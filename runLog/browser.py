from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import os

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
    # url = 'https://online.star.bnl.gov/apps/shiftLog2019/logForFullTextSearch.jsp?text=20000000'
    url = 'https://online.star.bnl.gov/apps/shiftLog2021/logForFullTextSearch.jsp?text=22031042'

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

def getDriver(firefox, timeout, username=None, password=None):
    if firefox:
        driver = webdriver.Firefox()
    else:
        driver = webdriver.Chrome(service_log_path=os.devnull)
    driver.set_page_load_timeout(timeout)
    if username is not None and password is not None: 
        # supposedly you only need to enter credientials once at the beginning
        autoLogin(driver, username, password, timeout)
    return driver

