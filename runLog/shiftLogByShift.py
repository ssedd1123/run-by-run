from selenium import webdriver
import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import re
from dateutil import parser
import traceback
import pytz
from datetime import datetime, timedelta
from prettytable import PrettyTable, ALL
import os

import sentiment as sen
import UI
import browser
#from shiftLog import autoLogin

def findRunTime(runID, driver, timeout):
    year = int(runID[:2]) - 1
    url = 'https://online.star.bnl.gov/RunLogRun%d/index.php?r=%s' % (year, runID)
    try:
        driver.get(url)
        WebDriverWait(driver, timeout).until(EC.any_of(EC.title_is('STAR RunLog Browser'), EC.title_contains('Error'), EC.title_contains('error'), EC.title_contains('Unauthorize')))
    except:
        print('Connection time out for run %d' % runId)
        return None, None, True
 
    soup = BeautifulSoup(driver.page_source, "html.parser")
    if 'error' in soup.title.get_text().lower() or 'unauthorize' in soup.title.get_text().lower():
        print('Cannot load shift log for run %s' % runId)
        return None, None, True
    try:
        # see if it's mark as junk by shift Leader
        # should NOT have been produced in the first place
        # but it does happen
        spans = soup.find_all('span', 'cr')
        junk = False
        if len(spans) > 0 and 'Marked as Junk' in spans[0].text:
            junk = True
        spans = soup.find_all('span', 'cg')
        startTime = spans[0].text # first span should be RTS Start Time
        startDateTime = parser.parse(startTime.lstrip('[').rstrip(']'))
        endTime = spans[1].text # Second span should be RTS Stop Time
        endDateTime = parser.parse(endTime.lstrip('[').rstrip(']'))

        # convert GMT to Eastern Time (daylight saving IS considered)
        eastern = pytz.timezone('US/Eastern')
        return startDateTime.astimezone(eastern), endDateTime.astimezone(eastern), junk
    except Exception as e:
        traceback.print_exc()
        print('Cannot get time of run %s' % runID)
        return None, None, True

def getAllEntriesOnDate(driver, date, timeout):
    url = "https://online.star.bnl.gov/apps/shiftLog%d/logForPeriod.jsp?startDate=%d/%d/%d&endDate=%d/%d/%d&B1=Submit" % (date.year, date.month, date.day, date.year, date.month, date.day, date.year)
    try:
        driver.get(url)
        WebDriverWait(driver, timeout).until(EC.any_of(EC.title_is('ShiftLog'), EC.title_contains('Error'), EC.title_contains('error'), EC.title_contains('Unauthorize')))
    except:
        print('Connection time out for %s' % date.strftime('%Y-%m-%d %H:%M:%S %Z'))
        return {}
    soup = BeautifulSoup(driver.page_source, "html.parser")
    if 'error' in soup.title.get_text().lower() or 'unauthorize' in soup.title.get_text().lower():
        print('Cannot load shift log for %s' % date.strftime('%Y-%m-%d %H:%M:%S %Z'))
        return {}
    tables = soup.findAll('table')
    entries = {}
    try:
        for table  in tables:
            timestamp = date
            rows = table.find_all('tr')
            for row in rows:
                # Find all cells in the row
                cells = row.find_all("td")#[-1]

                for i, cell in enumerate(cells):
                    # Print the cell text
                    word = cell.get_text(strip=True, separator="\n").replace('\t', ' ')
                    word = re.sub(r"\s*\n\s*", "\n", word)
                    if i == 0:
                        timeString = word[:5]
                        minHr = datetime.strptime(timeString, '%H:%M')
                        timestamp = timestamp.replace(hour=minHr.hour, minute=minHr.minute)
                    if i == 1:
                        entries[timestamp] = word

    except Exception:
        traceback.print_exc()
        return {}

    return entries
 
def getEntriesInRange(driver, start, end, timeout, timeSep, dp):
    beginTime = start
    currTime = beginTime.replace(hour=0, minute=0, second=0)
    oneDay = timedelta(days=1)
    results = {}
    while currTime <= end:
        # reduce wepage loading by dynamic programing
        if currTime in dp:
            res = dp[currTime]
        else:
            res = getAllEntriesOnDate(driver, currTime, timeout)
            dp[currTime] = res
        for dt, content in res.items():
            if start <= dt and dt <= end:
                results[dt] = content
        currTime += oneDay
        time.sleep(timeSep)
    return results

def printDict(result, runStart=None, runEnd=None, runID='0'):
    x = PrettyTable()
    x.hrules=ALL
    x.field_names = ['Time', 'Content']
    x._max_width = {'Time' : 10, 'Content' : 70}
    # reverse chronological order
    insertedStart = False
    insertedEnd = False
    for time, content in sorted(list(result.items()), key=lambda x:x[0], reverse=True):
        if runEnd is not None and not insertedEnd and time < runEnd:
            insertedEnd = True
            x.add_row(['8'*10, 'RUN' + runID + 'END' + '8'*(70 - 6 - len(runID) if 70 - 6 - len(runID) > 0 else 1)])
        if runStart is not None and not insertedStart and time < runStart:
            insertedStart = True
            x.add_row(['8'*10, 'RUN' + runID + 'START' + '8'*(70 - 8 - len(runID) if 70 - 8 - len(runID) > 0 else 1)])
        if runID in content:
            content = content.replace(runID, '>'*10 + runID + '<'*10)
        x.add_row([time.strftime('%B %d, %Y\n%H:%M:%S'), content])
    x.align['Content'] = 'l'
    return x.get_string()
