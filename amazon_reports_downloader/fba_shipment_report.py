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


class FBAShipmentReport():
    def __init__(self, driver):
        self.driver = driver

    def get_selected_date_range(self):
        try:
            date_picker_dropdown_xpath = '//div[@id="daily-time-picker-style"]/kat-dropdown'
            date_picker_dropdown_elem = WebDriverWait(self.driver, 3, 0.5).until(
                EC.presence_of_element_located((By.XPATH, date_picker_dropdown_xpath)))
            date_picker_dropdown = self.get_shadow_dom(date_picker_dropdown_elem)

            selected_option_elem = date_picker_dropdown.find_element_by_css_selector(
                'div.kat-select-container div.select-options kat-option[selected]')
            days = int(selected_option_elem.get_attribute('value'))
        except (NoSuchElementException, TimeoutException) as e:
            logger.exception(e)

            days = None

        return days

    def select_date_range(self, days):
        result = False
        try:
            date_picker_dropdown_xpath = '//div[@id="daily-time-picker-style"]/kat-dropdown'
            date_picker_dropdown_elem = WebDriverWait(self.driver, 3, 0.5).until(
                EC.presence_of_element_located((By.XPATH, date_picker_dropdown_xpath)))
            date_picker_dropdown = self.get_shadow_dom(date_picker_dropdown_elem)

            indicator_elem = date_picker_dropdown.find_element_by_css_selector(
                'div.kat-select-container div.indicator kat-icon[name="chevron-down"]')
            indicator_elem.click()

            date_range_option = date_picker_dropdown.find_element_by_css_selector(
                'div.kat-select-container div.select-options kat-option[value="{}"]'.format(days))
            date_range_option.click()

            time.sleep(1)

            selected_days = self.get_selected_date_range()
            result = selected_days == days
        except (NoSuchElementException, TimeoutException) as e:
            logger.exception(e)

        return result

    def has_shadow_root(self):
        result = True
        try:
            WebDriverWait(self.driver, 3, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'kat-box#report-page-kat-box')))
        except (NoSuchElementException, TimeoutException) as e:
            result = False

        return result

    def get_shadow_dom(self, shadow_host_elem):
        show_dom = self.driver.execute_script('return arguments[0].shadowRoot;', shadow_host_elem)
        return show_dom

    def check_shipment_status(self, date):
        result = False

        report_date_selector = 'div#downloadArchive tr.downloadTableRow:first-child td:nth-child(3), #download-page-margin-style > kat-table > kat-table-body > kat-table-row:nth-child(1) > kat-table-cell:nth-child(3)'
        for _ in range(3):
            self.driver.refresh()
            try:
                date_requested = WebDriverWait(self.driver, 10, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, report_date_selector))).text
                date_v1 = datetime.strptime(date, '%Y-%m-%d').strftime("%B %d, %Y")
                date_v2 = datetime.strptime(date, '%Y-%m-%d').strftime("%b. %-d, %Y")
                if date_requested.strip() == date_v1 or date_requested.strip() == date_v2:
                    result = True
                break
            except Exception as e:
                print(e)

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