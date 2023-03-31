import base64
from selenium import webdriver
import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import re
import json
from sentiment import sentiment
import argparse
import pyfiglet
import os
from datetime import datetime, timedelta
from prettytable import PrettyTable, ALL
import getpass

import shiftLogByShift as sl
import browser 

def login():
    username = input('Enter shift log username: ')
    password = getpass.getpass('Enter shift log password: ')
    return username, password

def getRunIdFromFile(filename):
    with open(filename) as f:
        runId = []
        reasons = {}
        lines = f.readlines()
        
        for l in lines:
            lsplit = l.split(' ', 1)
            id_ = lsplit[0].strip()
            runId.append(id_)
            if len(lsplit) == 2:
                reasons[id_] = lsplit[1]
            else:
                reasons[id_] = 'None provided'
    return runId, reasons

def selectRun(results, runID):
    relevant = {}
    for dt, content in results.items():
        if content.startswith('Run ' + runID):
            relevant[dt] = content
    return relevant

def getShiftLogDetailed(runs, timeStep, username=None, password=None, firefox=False, timeout=60, **kwargs):
    results = {}
    dp = {}
    junkID = []
    driver = browser.getDriver(firefox, timeout, username, password)

    for i, run in enumerate(runs):
        run = str(run)
        print('Loading history for run %s (%d/%d)' % (run, i+1, len(runs)))
        results[run] = ['', '']
        try: 
            driver.window_handles
        except:
            raise RuntimeError('Cannot call window handles. Browser may have been closed manually. Abort')
            raise
 
        try:
            runStart, runEnd = sl.findRunTime(run, driver, timeout)
        except Exception as e:
            results[run] = [str(e)]*3
            junkID.append(run)
        else:
            result, summary = sl.getEntriesAndSummary(driver, runStart, runEnd, timedelta(hours=10),
                                                      timedelta(minutes=30), timedelta(minutes=30), 
                                                      timeout, timeStep, dp)
            messageDetail = sl.printDict(result, runStart, runEnd, run)
            selectedMessage = selectRun(result, run)
            messageBrief = ('\n' + '-' * 50 + '\n' + '-'*50 + '\n').join([content for _, content in selectedMessage.items()])
            if summary is None:
                summary = 'Summary not found'
            results[run] = [messageBrief, messageDetail, summary[1]]
    return results, driver, junkID

def printBriefDict(result):
    x = PrettyTable()
    x.hrules=ALL
    x.field_names = ['RunID', 'Content']
    x._max_width = {'RunID' : 10, 'Content': 70}
    for runId, content in result.items():
        x.add_row([runId, content[0]])
    x.align['Content'] = 'l'
    return x.get_string()



def main(input, output, timeStep, allOutput, badrun, posOutput, negOutput, useAI, threshold, username, password, jsonInput=None, **kwargs):
    print('Reading bad run list from text file %s' % input)
    runId, reasons = getRunIdFromFile(input)

    if jsonInput is not None:
        print('Reading json file %s' % input)
        print('Will not write any json output')
        with open(jsonInput) as f:
            result = json.load(f)
        junkID = []
        for id, (contentB, contentD, _) in result.items():
            if contentB and contentB == contentD:
                junkID.append(id)
        assert runId == list(result.keys()), "Run ID from input and json file do not agree. Make sure you have the right file. Otherwise download everything from shift log from scratch."
    else:
        if username is None or password is None:
            username, password = login()
        result, driver, junkID = getShiftLogDetailed(runId, timeStep, username=username, password=password, **kwargs)
        driver.quit()
        print('Saving shiftLog to %s' % output)
    with open(output, 'w') as f:
        json.dump(result, f)
    if allOutput is not None:
        print('Saving human-readable shiftLog to %s' % allOutput)
        with open(allOutput, 'w') as f:
            f.write(printBriefDict(result))
    badRuns = None
    badHistory = None
    badSummary = None
    if useAI:
        AIbadRuns, AIbadHistory, AIbadSummary= sentiment(result, useAI, threshold=threshold)
        badRuns = junkID + AIbadRuns
        badHistory = junkID + AIbadHistory
        badSummary = junkID + AIbadSummary
        intro = 'AI thinks that %d runLog entries out of a total of %d are bad runs.\nBackground color will turn for red for those runs that are considered bad.' % (len(AIbadRuns), len(result))
    else:
        intro = 'There are %d runs to go through' % len(result)
    import UI
    pos, neg = UI.main(result, reasons, badRuns, badHistory, badSummary, intro=intro)
    for runID, content in neg.items():
        neg[runID] = content
    if posOutput is not None:
        with open(posOutput, 'w') as f:
            f.write(printBriefDict(pos))
    if negOutput is not None:
        with open(negOutput, 'w') as f:
            f.write(printBriefDict(neg))
    with open(badrun, 'w') as f:
        f.write('\n'.join(neg.keys()))


def printBanner():
    print(u'\u2500' * 100)
    print(pyfiglet.figlet_format('SHIFT LOG SCRAPER'))
    print(u'\u2500' * 100)
    print('Contact: <ctsang@bnl.gov>, <yuhu@bnl.gov>, <ptribedy@bnl.gov>')
    print(u'\u2500' * 100)


if __name__ == '__main__':
    printBanner()
    parser = argparse.ArgumentParser(description='Robot that fetch shiftLog online')
    parser.add_argument('-i', '--input', required=True, help='Text file with all the bad runs from QA script')
    parser.add_argument('-ji', '--jsonInput', help='Json file of shiftLog. If json file is provided, It will not load shiftLog online.')
    parser.add_argument('-o', '--output', required=True, help='Name of the json file to which ALL runlog are stored. Will be disabled if -ji is provided.')
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


    args = parser.parse_args()
    main(args.input, args.output, args.timeStep, args.allOutput, 
         args.badrun, args.posOutput, args.negOutput, args.useAI, 
         threshold=args.threshold, username=args.username, password=args.password, 
         firefox=args.useFirefox, timeout=args.timeout, jsonInput=args.jsonInput)
    print('*' * 100)
