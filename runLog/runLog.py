import base64
from selenium import webdriver
import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import re
import json
from sentiment import sentiment, printDict
import argparse

def getRunLog(runs, timeSep=0.5):
    result = {}
    driver = webdriver.Chrome()
    driver.set_page_load_timeout(10)
    for i, runId in enumerate(runs):
        #20057007
        result[runId] = None
        year = int(str(runId)[:2]) - 1
        url = "https://online.star.bnl.gov/apps/shiftLog20%d/logForFullTextSearch.jsp?text=%d" % (year, runId)
        print('Loading data for run %d (%d/%d)' % (runId, i + 1, len(runs)))
        
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(EC.title_is('ShiftLog'))
        except:
            continue
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tables = soup.findAll('table')
        try:
            for table  in tables:
                rows = table.find_all('tr')
                for row in rows:
                    # Find all cells in the row
                    #print(row.find_all('td'))
                    cells = row.find_all("td")#[-1]
                    for i, cell in enumerate(cells):
                        # Print the cell text
                        word = cell.get_text(strip=True, separator="\n")
                        word = re.sub(r"\s*\n\s*", "\n", word)
                        if i == 0 and 'General' not in word:
                            break
                        if i == 1:
                            if result[runId] is None:
                                result[runId] = word
                            else:
                                result[runId] = result[runId] + '\n' + word

        except Exception:
            pass
        time.sleep(timeSep)
    return result

def getRunIdFromFile(filename):
    with open(filename) as f:
        runId = []
        lines = f.readlines()
        try:
            for l in lines:
                runId.append(int(l.split(' ')[0]))
        except Exception:
            pass
    return runId

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Robot that fetch runLog online')
    parser.add_argument('-i', '--input', required=True, help='Text file with all the bad runs. Competible with output from QA script.')
    parser.add_argument('-o', '--output', required=True, help='Name of the json file to which runlog are stored.')
    parser.add_argument('-ho', '--humanOutput', help='Name of the human readible text file to which runlog are stored.')
    parser.add_argument('-t', '--timeStep', type=float, default=0.5, help='Refresh interval to fetch run-log. Cannot be too short to avoid DDoS.')
    args = parser.parse_args()
    runId = getRunIdFromFile(args.input)
    result = getRunLog(runId, args.timeStep)
    with open(args.output, 'w') as f:
        json.dump(result, f)
    if args.humanOutput is not None:
        with open(args.humanOutput, 'w') as f:
            f.write(printDict(result))
     
