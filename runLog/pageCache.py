from hashlib import sha256
import os
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from urllib.parse import urlparse

import time

class PageCache:
    # only load page from internet if a copy does not exist locally
    def __init__(self, timeSep):
        self._dir = 'HTML'
        os.makedirs(self._dir, exist_ok=True)
        self._timeSep = timeSep

    def getUrl(self, url, driver, timeout, expected_title):
        # need to get rid of username and password
        parsed = urlparse(url)
        replaced = parsed._replace(netloc="{}:{}@{}".format("???", "???", parsed.hostname))
        stripped_url = replaced.geturl()
        prefix = sha256(stripped_url.encode()).hexdigest()
        filename = prefix
        for i in range(1, 10000):
            if os.path.isfile(os.path.join(self._dir, filename + '.html')):
                with open(os.path.join(self._dir, filename + '.html'), encoding='utf-8') as f:
                    content = f.read()
                    urlFile, content = content.split('\n', 1)
                    if urlFile == '<!-- ' + stripped_url + '-->':
                        return content
                    else:
                        filename = prefix + '_%d' % i
            else:
                break
        else:
            raise RuntimeError('Really? 10000 hash collisions? Clear your HTML directory.')
                
        try: 
            driver.window_handles
        except EC.WebDriverException:
            raise RuntimeError('Cannot call window handles. Browser may have been closed manually. Abort')
            raise

        driver.get(url)
        WebDriverWait(driver, timeout).until(EC.any_of(EC.title_is(expected_title), 
                                             EC.title_contains('Error'), 
                                             EC.title_contains('error'), 
                                             EC.title_contains('Unauthorize')))
     
        if 'error' in driver.title.lower() or 'unauthorize' in driver.title.lower():
            raise RuntimeError('Cannot load shift log. Verify that your username and password are correct.')

        with open(os.path.join(self._dir, filename + '.html'), 'w', encoding='utf-8') as f:
            f.write('<!-- ' + stripped_url + '-->\n' + driver.page_source)
        time.sleep(self._timeSep)
        return driver.page_source


if __name__ == '__main__':
    import browser
    driver = browser.getDriver(False, 30, '', '')
    ps = PageCache()

    runID = str(20062045)
    year = int(runID[:2]) - 1
    url = 'https://online.star.bnl.gov/RunLogRun%d/index.php?r=%s' % (year, runID)

    p1 = ps.getUrl(url, driver, 30, 'STAR RunLog Browser')
    p2 = ps.getUrl(url, driver, 30, 'STAR RunLog Browser')
    print(p1 == p2)
