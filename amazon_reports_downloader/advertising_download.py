import time
import pdb
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException)

from selenium.webdriver.support.select import Select
from selenium import webdriver
from selenium.webdriver.common.alert import Alert

from amazon_reports_downloader import logger
from amazon_reports_downloader.utils import close_web_driver

class AdvertisingReport(Object):
    def __init__(self, driver):
        self.driver = driver

    def choose_advertised_product(self):
        while True:
            try:
                logger.info("choose advertised product")
                report_type_btn = WebDriverWait(self.driver, 3, 0.5).until(EC.element_to_be_clickable((By.XPATH, '//div[contains(text(), "Search")]')))
                report_type_btn.click()
                advertised_elem = WebDriverWait(self.driver, 3, 0.5).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="portal"]/div/div/button[3]')))
                advertised_elem.click()
                return True
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                return False
    