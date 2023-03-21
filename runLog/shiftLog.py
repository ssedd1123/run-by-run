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
import pyfiglet
import os

import sentiment as sen

def getShiftLog(runs, timeSep=0.5):
    result = {}
    driver = webdriver.Chrome()
    driver.set_page_load_timeout(10)
    for i, runId in enumerate(runs):
        result[runId] = None
        year = int(str(runId)[:2]) - 1
        url = "https://online.star.bnl.gov/apps/shiftLog20%d/logForFullTextSearch.jsp?text=%d" % (year, runId)
        print('Loading data for run %d (%d/%d)' % (runId, i + 1, len(runs)))
        
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(EC.any_of(EC.title_is('ShiftLog'), EC.title_contains('Error'), EC.title_contains('error')))
        except:
            print('Connection time out for run %d' % runId)
            result[runId] = 'Connection to shift log time out'
            continue
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        if 'error' in soup.title.get_text().lower():
            print('Cannot load shift log for run %d' % runId)
            result[runId] = 'Cannot load shift log'
            continue
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

def main(input, output, timeStep, allOutput):
    _, ext = os.path.splitext(input)
    if ext == '.json':
        print('Reading json file %s' % input)
        with open(args.input) as f:
            result = json.load(f)
    else:
        print('Reading bad run list from text file %s' % input)
        runId = getRunIdFromFile(input)
        result = getShiftLog(runId, timeStep)
    print('Saving shiftLog to %s' % output)
    with open(output, 'w') as f:
        json.dump(result, f)
    if allOutput is not None:
        print('Saving human-readable shiftLog to %s' % allOutput)
        with open(allOutput, 'w') as f:
            f.write(printDict(result))

def printBanner():
    print(u'\u2500' * 100)
    print(pyfiglet.figlet_format('SHIFT LOG SCRAPER'))
    print(u'\u2500' * 100)
    print('Contact: <ctsang@bnl.gov>, <yuhu@bnl.gov>, <ptribedy@bnl.gov>')
    print(u'\u2500' * 100)


if __name__ == '__main__':
    printBanner()
    parser = argparse.ArgumentParser(description='Robot that fetch shiftLog online')
    parser.add_argument('-i', '--input', required=True, help='Text file with all the bad runs from QA script OR json file of shiftLog. If json file is provided, It will not load shiftLog online.')
    parser.add_argument('-o', '--output', required=True, help='Name of the json file to which ALL runlog are stored.')
    parser.add_argument('-br', '--badrun', required=True, help='Name of the text file of all the bad runs')
    parser.add_argument('-t', '--timeStep', type=float, default=0.5, help='Refresh interval to fetch run-log. Cannot be too short to avoid DDoS.')
    parser.add_argument('-ao', '--allOutput', help='Name of the human readible file to which all run are stored.')
    parser.add_argument('-po', '--posOutput', help='Name of the human readible file to which positive runs are stored')
    parser.add_argument('-no', '--negOutput', help='Name of the human readible file to which negative runs are stored')
    parser.add_argument('--useAI', action='store_true', help='Use AI to help select bad runs from shiftLog.')
    parser.add_argument('--justAI', action='store_true', help='Just Use AI to select bad runs from shiftLog. No user prompt. Will override --useAI option.')
    args = parser.parse_args()

    main(args.input, args.output, args.timeStep, args.allOutput)
    print('*' * 100)
    sen.main(args.output, args.badrun, args.posOutput, args.negOutput, args.useAI, args.justAI)
    print('*' * 100)
