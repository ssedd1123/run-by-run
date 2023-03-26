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
import shiftLogByShift as sl
import browser 

def getShiftLog(runs, timeSep=0.5, username=None, password=None, firefox=False, timeout=60):
    result = {}
    driver = browser.getDriver(firefox, timeout, username, password)

    for i, runId in enumerate(runs):
        result[runId] = None
        year = int(str(runId)[:2]) - 1
        url = "https://online.star.bnl.gov/apps/shiftLog20%d/logForFullTextSearch.jsp?text=%d" % (year, runId)
        print('Loading data for run %d (%d/%d)' % (runId, i + 1, len(runs)))

        try: 
            driver.window_handles
        except:
            raise RuntimeError('Cannot call window handles. Browser may have been closed manually. Abort')
            raise
        
        try:
            driver.get(url)
            WebDriverWait(driver, timeout).until(EC.any_of(EC.title_is('ShiftLog'), EC.title_contains('Error'), EC.title_contains('error'), EC.title_contains('Unauthorize')))
        except:
            print('Connection time out for run %d' % runId)
            result[runId] = 'Connection to shift log time out'
            continue
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        if 'error' in soup.title.get_text().lower() or 'unauthorize' in soup.title.get_text().lower():
            print('Cannot load shift log for run %d' % runId)
            result[runId] = 'Cannot load shift log'
            continue
        tables = soup.findAll('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                # Find all cells in the row
                #print(row.find_all('td'))
                cells = row.find_all("td")#[-1]
                #for i, cell in enumerate(cells):
                    # Print the cell text
                if len(cells) == 2:
                    if 'QA' not in cells[0].get_text():
                        word = cells[1].get_text(strip=True, separator="\n").replace('\t', ' ')
                        word = re.sub(r"\s*\n\s*", "\n", word)
                        if result[runId] is None:
                            result[runId] = word
                        else:
                            result[runId] = result[runId] + '\n' + word
        time.sleep(timeSep)
    # driver.quit()
    return result, driver

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

def main(input, output, timeStep, allOutput, **kwargs):
    _, ext = os.path.splitext(input)
    driver = None
    if ext == '.json':
        print('Reading json file %s' % input)
        with open(args.input) as f:
            result = json.load(f)
    else:
        print('Reading bad run list from text file %s' % input)
        runId = getRunIdFromFile(input)
        result, driver = getShiftLog(runId, timeStep, **kwargs)
    print('Saving shiftLog to %s' % output)
    with open(output, 'w') as f:
        json.dump(result, f)
    if allOutput is not None:
        print('Saving human-readable shiftLog to %s' % allOutput)
        with open(allOutput, 'w') as f:
            f.write(printDict(result))
    return driver

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
    parser.add_argument('--useAI', choices=['NLTK', 'TRANS'], help='Use AI to help select bad runs from shiftLog.')
    parser.add_argument('--justAI', choices=['NLTK', 'TRANS'], help='Just Use AI to select bad runs from shiftLog. No user prompt. Will override --useAI option.')
    parser.add_argument('-th', '--threshold', type=float, default=0.99, help='Threshold of score higher than which a shift log entry will be consider bad by AI. Only used when TRANS model is used. (default: %(default)s)')

    parser.add_argument('-un', '--username', help='Username of the shift log. (Experimental. Unstable. Use at your own risk)')
    parser.add_argument('-pw', '--password', help='Password of the shift log. (Experimental. Unstable. Use at your own risk)')
    parser.add_argument('--useFirefox', action='store_true', help='Switch to Firefox if desired. MAY NOT WORK WITH MANUAL CREDENTIALS.')
    parser.add_argument('-to', '--timeout', default=60, type=float, help='Longest time to wait before connection timeout (default: %(default)s)')
    parser.add_argument('-tr', '--traceHistory', help='Name of the human readible file to which 7 hours of shift log before the end of each selected run. The selected runs are good run from first pass to make sure the good runs are really good.')


    args = parser.parse_args()
    driver = main(args.input, args.output, args.timeStep, args.allOutput, 
                  username=args.username, password=args.password, 
                  firefox=args.useFirefox, timeout=args.timeout)
    print('*' * 100)
    pos, neg = sen.main(args.output, args.badrun, args.posOutput, args.negOutput, args.useAI, args.justAI, threshold=args.threshold)
    print('*' * 100)
    if args.traceHistory is not None:
        print('Searching histories of the good runs.')
        pos, neg = sl.main(list(pos.keys()), args.badrun, driver, timeSep=args.timeStep, 
                           firefox=args.useFirefox, username=args.username, password=args.password)
        with open(args.traceHistory, 'w') as f:
            f.write(sen.printDict(neg))
    driver.quit()
