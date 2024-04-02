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
from collections import namedtuple, defaultdict
from readFromROOT import getNamesAllTProfile, getVarNames, readFromROOT
import re
from tqdm import tqdm

import shiftLogByShift as sl
#import browser 
from pageCache import PageCache

RunInfo = namedtuple('RunInfo', 'message history summary runStart runEnd')

def login():
    username = input('Enter shift log username: ')
    password = getpass.getpass('Enter shift log password: ')
    return username, password

def getRunIdFromFile(filename, varName=None, mapping=None):
    if filename.endswith('.root'):
        print('The input is a ROOT file.')
        if varName is None:
            print('No TProfile is specified. Will load run ID from the x-axis of the first TProfile contained in the file.')
            varName = getNamesAllTProfile(filename)[0]
        else:
            varName = getVarNames(varName)[0]
        print('Loading run ID from TProfile: %s' % varName)
        if mapping is not None:
            print('Will use mapping file: %s' % mapping)
        runs, _, _, _ = readFromROOT(filename, [varName], mapping)
        runId = [str(id_) for id_ in runs]
        reasons = {str(id_): 'None provided' for id_ in runs}
    else:
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

def selectRun(results, runID, dp):
    if runID in dp:
        return dp[runID]

    for dt, content in results.items():
        matches = re.findall(r'Run (\d+)', content)
        if matches:
            capturedID = matches[0]
            dp[capturedID][dt] = content

    return dp[runID]

def getShiftLogDetailed(runs, pc, runYR, username=None, password=None, firefox=False, timeout=60, ignoreEmpty=False, minDuration=None, **kwargs):
    results = {}
    dp = {}
    NEvents = {}
    dpSelect = defaultdict(dict)
    junkReasons = {}
    try:
        #driver = browser.getDriver(firefox, timeout, username, password)
        if firefox:
            driver = webdriver.Firefox()
        else:
            import chromedriver_autoinstaller
            chromedriver_autoinstaller.install()
            driver = webdriver.Chrome()

        driver.set_page_load_timeout(timeout)
    
        for i, run in tqdm(enumerate(runs), desc='Loading run history', total=len(runs)):
            run = str(run)
            results[run] = ['', '']
            NEvents[run] = 0
    
            try:
                runStart, runEnd, NEvent = sl.findRunTime(run, runYR, driver, timeout, pc, username, password)
            except ValueError as e:
                results[run] = RunInfo({'Error': 'Run info cannot be fetched from online database. Detailed error: ' + str(e)}, None, None, None, None)
                junkReasons[run] = 'Run info cannot be fetched from online database. Detailed error: ' + str(e)
            else:
                result, summary = sl.getEntriesAndSummary(driver, runYR, runStart, runEnd, timedelta(hours=10),
                                                          timedelta(minutes=90), timedelta(minutes=90), 
                                                          timeout, dp, pc, username, password)
                selectedMessage = selectRun(result, run, dpSelect)
                if ignoreEmpty:
                    if not selectedMessage:
                        del results[run]
                        del NEvents[run]
                        continue
                if summary is None:
                    summary = (runStart, 'Summary not found')
                if minDuration is not None:
                    duration = runEnd - runStart
                    if duration < timedelta(seconds=minDuration):
                        junkReasons[run] = 'BAD RUN: the run lasted %d seconds < min threshold of %d seconds.' % (duration.seconds, minDuration)
                        selectedMessage = {runStart - timedelta(seconds=1): junkReasons[run], **selectedMessage}
                NEvents[run] = NEvent
                results[run] = RunInfo(selectedMessage, result, 
                                       summary[1], runStart, runEnd)
    finally:
        if driver is not None:
            driver.quit()

    return results, junkReasons, NEvents

def printBriefDict(result):
    x = PrettyTable()
    x.hrules=ALL
    x.field_names = ['RunID', 'Content']
    x._max_width = {'RunID' : 10, 'Content': 70}
    for runId, content in result.items():
        brief = ('\n' + '-' * 50 + '\n' + '-'*50 + '\n').join([entry for _, entry in content.message.items()])
        x.add_row([runId, brief])
    x.align['Content'] = 'l'
    return x.get_string()


def human_format(num):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{:.2f}{}'.format(num, ['', 'K', 'M', 'B', 'T', 'P'][magnitude])


def eventSummary(NEvents, badrunList):
    totEvents = 0
    badEvents = 0
    for id, events in NEvents.items():
        totEvents = totEvents + events
        if id in badrunList:
            badEvents = badEvents + events
    print(u'\u2500' * 100)
    print('Total number of runs = %d' % len(NEvents))
    print('Total Statistics = %d = %s' % (totEvents, human_format(totEvents)))
    print('Rejected Runs = %d (%.1f %%)' % (len(badrunList), float(len(badrunList))*100/len(NEvents)))
    print('Rejected events = %d = %s (%.1f%%)' % (badEvents, human_format(badEvents), float(badEvents)*100/totEvents))


def main(input, runYR, timeStep, allOutput, badrun, posOutput, negOutput, useAI, threshold, username, password, skipUI, ignoreEmpty, jsonAI, forceAI, debugAI, varNames, mapping, **kwargs):
    print('Reading bad run list from text file %s' % input)
    runId, reasons = getRunIdFromFile(input, varNames, mapping)
    if username is None or password is None:
        username, password = login()
    pc = PageCache(timeStep)
    # load data from shiftLog, return junks that are easy to identify e.g. shift leader marked as junk, duration doesn't meet min requirement. 
    result, junkReasons, NEvents = getShiftLogDetailed(runId, pc, runYR, username=username, password=password, ignoreEmpty=ignoreEmpty, **kwargs)

    if allOutput is not None:
        print('Saving human-readable shiftLog to %s' % allOutput)
        with open(allOutput, 'w') as f:
            f.write(printBriefDict(result))

    if useAI:
        AIReasons = sentiment(result, 'LLM', skip=set(junkReasons.keys()), settings_json=jsonAI, threshold=threshold, forceAI=forceAI, debug=debugAI)
        junkReasons = {**AIReasons, **junkReasons}
        intro = 'AI thinks that %d runLog entries out of a total of %d are bad runs.\nBackground color will turn for red for those runs that are considered bad.' % (len(AIReasons), len(result))
    else:
        intro = 'There are %d runs to go through.' % len(result)
    import UI
    pos, neg, memo = UI.main(result, 
                             reasons, 
                             set(junkReasons.keys()), 
                             intro=intro,
                             defaultNotes=junkReasons,
                             skipUI=skipUI)
    if skipUI:
        # without user intervention, all junk runs are rejected
        for run, reason in junkReasons.items():
            memo[run] = reason

    for runID, content in neg.items():
        neg[runID] = content

    # store run log of good runs in text file
    if posOutput is not None:
        with open(posOutput, 'w') as f:
            f.write(printBriefDict(pos))
    # store run log of bad runs in text file
    if negOutput is not None:
        with open(negOutput, 'w') as f:
            f.write(printBriefDict(neg))

    eventSummary(NEvents, set(neg.keys()))

    # store bad run list with notes on the memo. 
    with open(badrun, 'w', encoding='utf-8') as f:
        f.write('\n'.join(['%s $ %s' % (id_, memo[id_]) for id_ in neg.keys()]))


def printBanner():
    print(u'\u2500' * 100)
    print(pyfiglet.figlet_format('SHIFT LOG SCRAPER'))
    print(u'\u2500' * 100)
    print('Contact: <ctsang@bnl.gov>, <yuhu@bnl.gov>, <ptribedy@bnl.gov>, <asheikh2@kent.edu>')
    print(u'\u2500' * 100)


if __name__ == '__main__':
    printBanner()
    parser = argparse.ArgumentParser(description='Robot that fetch shiftLog online')
    parser.add_argument('-i', '--input', required=True, help='Text file with all the bad runs from QA script')
    parser.add_argument('-o', '--output', help='Deprecated. All output are saved automatically in runLog/HTML. Will ignore this option')
    parser.add_argument('-br', '--badrun', required=True, help='Name of the text file of all the bad runs')
    parser.add_argument('-t', '--timeStep', type=float, default=0.5, help='Refresh interval to fetch run-log. Cannot be too short to avoid DDoS.')
    parser.add_argument('-ao', '--allOutput', help='Name of the human readible file to which all run are stored.')
    parser.add_argument('-po', '--posOutput', help='Name of the human readible file to which positive runs are stored')
    parser.add_argument('-no', '--negOutput', help='Name of the human readible file to which negative runs are stored')
    parser.add_argument('--skipUI', action='store_true', help='Will skip the user verification step. Only return junk that are identified automatically either with AI or just duration requirement.')
    parser.add_argument('--useAI', action='store_true', help='Use AI to select bad runs from shiftLog.')
    parser.add_argument('--forceAI', action='store_true', help='Force AI to not use cache and rerun.')
    parser.add_argument('--jsonAI', default='jsons/LLM_settings_mid.json', help='Json file for the AI settings')
    parser.add_argument('-th', '--threshold', type=float, default=0.99, help='Threshold of score higher than which a shift log entry will be consider bad by AI. Only used when TRANS model is used. (default: %(default)s)')

    parser.add_argument('-un', '--username', help='Username of the shift log. (Experimental. Unstable. Use at your own risk)')
    parser.add_argument('-pw', '--password', help='Password of the shift log. (Experimental. Unstable. Use at your own risk)')
    parser.add_argument('--useFirefox', action='store_true', help='Switch to Firefox if desired. MAY NOT WORK WITH MANUAL CREDENTIALS.')
    parser.add_argument('-to', '--timeout', default=60, type=float, help='Longest time to wait before connection timeout (default: %(default)s)')
    parser.add_argument('-YR', '--runYR', type=int, help='Run year. e.g. 20 for Run 20, 19 for Run 19', required=True)
    parser.add_argument('-ie', '--ignoreEmpty', action='store_true', help='If enable, runs where shift log entries are empty will be ignored and not appear in GUI or the bad run list.')
    parser.add_argument('-md', '--minDuration', default=None, type=float, help='Unit is seconds. If duration of a run is less than minDuration, the run is automatically considered bad.')

    parser.add_argument('--test', action='store_true', help='Automatically compare AI\'s results to manual inspection and official bad runs.')
    parser.add_argument('--debugAI', action='store_true', help='Print the prompt and response from AI.')

    parser.add_argument('-v', '--varNames', help='(Optional, only used if input is a ROOT file) Txt files with all the variable names for QA. If it is not set, it will read ALL TProfiles in the ROOT file.')
    parser.add_argument('-m', '--mapping', help ='(Optional, only used if input is a ROOT file) If x-axis of TProfile does not corresponds to STAR run ID, you can supply a file that translate bin low edge to STAR ID')


    args = parser.parse_args()
    if args.output is not None:
        raise DeprecationWarning('The flag -o is not used anymore because all loaded pages are cached automatically now. Run again with no -o option.')
    if args.test:
        # use test run list
        print('Self-test mode.')
        print('Will load bad run list for testing.')
        args.input = 'selfTest/badrun.list'
        args.runYR = 20
    main(args.input, args.runYR, args.timeStep, args.allOutput,
         args.badrun, args.posOutput, args.negOutput, args.useAI, 
         threshold=args.threshold, username=args.username, password=args.password, 
         firefox=args.useFirefox, timeout=args.timeout, skipUI=args.skipUI, 
         ignoreEmpty=args.ignoreEmpty, minDuration=args.minDuration,
         jsonAI=args.jsonAI, forceAI=args.forceAI, debugAI=args.debugAI,
         varNames=args.varNames, mapping=args.mapping)
    print('*' * 100)

    if args.test:
        import selfTest.compareManual as cm
        cm.main(args.badrun, 'selfTest/manualResult.txt', 'report.csv')
        print('Self test results are saved to report.csv.')
