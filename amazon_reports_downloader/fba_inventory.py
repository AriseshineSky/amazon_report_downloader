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

class FBAInventoryDownload(object):
    def __init__(self, driver):
        self.driver = driver

    def get_shadow_dom(self, shadow_host_elem):
        show_dom = self.driver.execute_script('return arguments[0].shadowRoot;', shadow_host_elem)
        return show_dom

    def has_shadow_root(self):
        result = True
        try:
            WebDriverWait(self.driver, 3, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'kat-box#report-page-kat-box')))
        except (NoSuchElementException, TimeoutException) as e:
            result = False

        return result

    def download_inventory_report(self):
        last_request_time = self.get_FBA_inventory_report_time_v1()
        for _ in range(100):
            try:
                time.sleep(5)
                new_request_time = self.get_FBA_inventory_report_time_v1()
                if new_request_time == last_request_time:
                    continue
                else:
                    download_btn = self.get_download_btn()
                    if download_btn.text.strip() == 'Download':
                        result = True
                        download_btn.click
                        break
                    else:
                        continue
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                break
    
    def click_request_download(self):
        result = False
        request_download_btn_xpath = '//*[@id="report-page-kat-box"]/kat-button[2]'
        request_download_btn_elem = WebDriverWait(self.driver, 3, 0.5).until(
            EC.presence_of_element_located((By.XPATH, request_download_btn_xpath))
        )
        
        while True:
            try:
                request_download_root = self.get_shadow_dom(request_download_btn_elem)
                request_download = WebDriverWait(request_download_root, 10, 0.5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.button div.content > slot > span')))
                request_download.click()
                result = True
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                break

        return result

        
    def get_download_btn(self):
        result = None
        try:
            download_btn_elem_xpath = '//*[@id="download-page-margin-style"]/kat-table/kat-table-body/kat-table-row[1]/kat-table-cell[5]/kat-button'
            download_btn_elem = WebDriverWait(self.driver, 3, 0.5).until(
                EC.presence_of_element_located((By.XPATH, download_btn_elem_xpath))
            )
            download_btn_elem = self.get_shadow_dom(download_btn_elem)
            download_btn = download_btn_elem.find_element_by_css_selector(
                'button.button div.content > slot > span')
            result = download_btn
        except Exception as e:
            pass
        return result
    
    def get_FBA_inventory_report_time_v1(self):
        report_request_time_xpath = '//*[@id="download-page-margin-style"]/kat-table/kat-table-body/kat-table-row[1]/kat-table-cell[2]'
        report_request_time = None
        try:
            report_request_time = WebDriverWait(self.driver, 7, 0.5).until(
                EC.presence_of_element_located((By.XPATH, report_request_time_xpath))).text.strip()
        except (NoSuchElementException, TimeoutException):
            report_request_time_xpath = '//*[@id="report-page-margin-style"]/kat-table/kat-table-body/kat-table-row[1]/kat-table-cell[2]'
            try:
                report_request_time = WebDriverWait(self.driver, 7, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, report_request_time_xpath))).text.strip()
            except (NoSuchElementException, TimeoutException):
                pass
        logger.info('inventory request time: %s' % report_request_time)
        return report_request_time

    

