from seleniumwire import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

def Create():
    options = webdriver.EdgeOptions()
    options.add_argument("--headless")
    driver = webdriver.Edge(options=options)
    return driver

def goto(driver: webdriver, url: str):
    driver.get(url)
    return driver

def getValue(driver: webdriver, by: By, path: str, defaultValue: any, errorFriendlyName: str):        
    try:
        return driver.find_element(by, path).text.strip()
    except: 
        return defaultValue

def getHTMLGroups(driver: webdriver, by: By, path: str, errorFriendlyName: str):
    try:
        return driver.find_elements(by, path)
    except: 
        print(errorFriendlyName)

def getHTML(driver: webdriver, by: By, path: str, errorFriendlyName: str):
    try:
        return driver.find_element(by, path)
    except: 
        print(errorFriendlyName)

def waitForPageLoad(driver):
    elementOnPage = EC.presence_of_element_located((By.TAG_NAME, 'p'))
    WebDriverWait(driver, timeout=3).until(elementOnPage)
    
def CreateSelect(driver,by,path,error):
    try:
        return Select(getHTML(driver=driver,by=by, path=path,errorFriendlyName=error))
    except:
        print(error)
             