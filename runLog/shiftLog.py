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

def autoLogin(driver, username, password, timeout):
    print('*' * 100)
    print('Using pre-entered credentials')
    print('WARNING: Auto Login is Extremely unstable!')
    print('Prepare for failure and try again')
    try:
        import keyboard
    except ModuleNotFoundError as e:
        print('*' * 100)
        print('Keyboard module not found. Please install with \'pip install keyboard\'')
        print('Abort. Please enter credentials manually.')
        print('*' * 100)
        return
    # login with shiftLog2019 home page
    # once you have the login session, you are all set
    # if this url fails, replace with any other shift log page
    url = 'https://online.star.bnl.gov/apps/shiftLog2019/logForFullTextSearch.jsp?text=20000000'

    driver.get(url)
    keyboard.write(username)
    keyboard.press_and_release('tab')
    keyboard.write(password)
    keyboard.press_and_release("tab")
    keyboard.press_and_release("enter")
    print('*' * 100)
    WebDriverWait(driver, timeout).until(EC.any_of(EC.title_is('ShiftLog'), EC.title_contains('Error'), EC.title_contains('error'), EC.title_contains('Unauthorize')))
    if 'Unauthorize' in driver.title.lower():
        raise RuntimeError('Incorrect password or username')


def getShiftLog(runs, timeSep=0.5, username=None, password=None, firefox=False, timeout=60):
    result = {}
    if firefox:
        driver = webdriver.Firefox()
    else:
        driver = webdriver.Chrome()
    driver.set_page_load_timeout(timeout)
    if username is not None and password is not None: 
        # supposedly you only need to enter credientials once at the beginning
        autoLogin(driver, username, password, timeout)

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
    driver.quit()
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

def main(input, output, timeStep, allOutput, **kwargs):
    _, ext = os.path.splitext(input)
    if ext == '.json':
        print('Reading json file %s' % input)
        with open(args.input) as f:
            result = json.load(f)
    else:
        print('Reading bad run list from text file %s' % input)
        runId = getRunIdFromFile(input)
        result = getShiftLog(runId, timeStep, **kwargs)
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
    parser.add_argument('-un', '--username', help='Username of the shift log. (Experimental. Unstable. Use at your own risk)')
    parser.add_argument('-pw', '--password', help='Password of the shift log. (Experimental. Unstable. Use at your own risk)')
    parser.add_argument('--useFirefox', action='store_true', help='Switch to Firefox if desired. MAY NOT WORK WITH MANUAL CREDENTIALS.')
    parser.add_argument('-to', '--timeout', default=60, type=float, help='Longest time to wait before connection timeout (default: %(default)s)')


    args = parser.parse_args()
    main(args.input, args.output, args.timeStep, args.allOutput, 
            username=args.username, password=args.password, 
            firefox=args.useFirefox, timeout=args.timeout)
    print('*' * 100)
    sen.main(args.output, args.badrun, args.posOutput, args.negOutput, args.useAI, args.justAI)
    print('*' * 100)
