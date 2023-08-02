from seleniumwire import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from logger.logger import getMyLogger

logger = getMyLogger(__name__)


def Create():
    options = webdriver.EdgeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-crash-reporter")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-in-process-stack-traces")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_argument("--output=/dev/null")
    driver = webdriver.Chrome(options=options)
    return driver


def goto(driver: webdriver, url: str):
    driver.get(url)
    return driver


def get_element_text_from_path(
    driver: webdriver, by: By, path: str, default_value: any, log_term: str
):
    try:
        return driver.find_element(by, path).text.strip()
    except:
        logger.log(0, log_term)
        return default_value


def get_elements_from_path(driver: webdriver, by: By, path: str, log_term: str):
    try:
        return driver.find_elements(by, path)
    except:
        logger.log(0, log_term)


def get_element(driver: webdriver, by: By, path: str, log_term: str):
    try:
        return driver.find_element(by, path)
    except:
        logger.log(0, log_term)


def page_load(driver):
    element_on_page = EC.presence_of_element_located((By.TAG_NAME, "p"))
    WebDriverWait(driver, timeout=3).until(element_on_page)


def create_select(driver, by, path, log_term):
    try:
        return Select(get_element(driver=driver, by=by, path=path, log_term=log_term))
    except:
        logger.log(0, log_term)
