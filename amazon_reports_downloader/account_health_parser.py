import time
import random
import re
import os
import requests
import calendar
import json
import traceback
from datetime import datetime, timedelta, timezone
from json import dumps
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import pdb

from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException)

from selenium.webdriver.support.select import Select
from selenium import webdriver
from selenium.webdriver.common.alert import Alert

from amazon_reports_downloader import logger, REFACTOR, downloaded_report_dir, MARKETPLACE_MAPPING
from amazon_reports_downloader.utils import close_web_driver


class AccountHealthReporter(object):
    def __init__(self, driver):
        self.driver = driver
        self.selectors = {
            'compliance_table': '#ahd-product-policies-table',
            'compliance_rows': '.ahd-product-policy-table-row-wrapper',
            'compliance_reason': 'div[class^="kat-row"] > div:first-child a',
            'compliance_date': 'div[class^="kat-row"] > div:nth-child(2) span',
            'action_selector': 'div[class^="kat-row"] > div:nth-child(4) span',
            'impact_selector': 'div[class^="kat-row"] > div:nth-child(3) span:first-child',
            'page_number': '#ahd-pp-pagination-jump > kat-label:nth-child(3)',
            'page_input': '#katal-id-2',
            'page_input_2': '#ahd-pp-pagination-page-num-input',
            'go_button': '#ahd-pp-pagination-page-num-submit-button'
        }
        self.xpathes = {
            'asin_xpath': './/div/span[contains(text(), "ASIN:")]',
            'sku_xpath': './/div/span[contains(text(), "SKU:")]',
            'impact_xpath': './/div[@class="kat-row kat-no-gutters ahd-product-policy-table-row"]/div[@class="kat-col-xs-4"]/span[1]',
            'action_xpath': './/div[contains(@class, "kat-row")]//div[4]/span',
            'pages_shadow': '//*[@id="ahd-pp-pagination-katal-control"]',
        }

    def close_webdriver(self):
        if self.driver is None:
            return

        close_web_driver(self.driver)
        self.driver = None

    def download_health_report(self, seller_id, marketplace):
        result = {
            "sellerID": seller_id,
            "marketPlace": marketplace
        }
        data = []
        try:
            report_table = WebDriverWait(self.driver, 10, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["compliance_table"])))
            report_table_rows = report_table.find_elements_by_css_selector(self.selectors["compliance_rows"])
            for row in report_table_rows:
                try:
                    record = dict()
                    record.update(result)
                    compliance_reason = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["compliance_reason"]))).text
                    compliance_date = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["compliance_date"]))).text
                    impact = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["impact_selector"]))).text
                    try:
                        ASIN = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["asin_xpath"]))).text
                        record.update({
                            "asin": ASIN.strip().split()[-1]
                        })
                    except Exception as e:
                        try:
                            SKU = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["sku_xpath"]))).text
                            record.update({
                                "sku": SKU.strip().split()[-1]
                            })
                        except Exception as e:
                            print(e)
                    action = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["action_selector"]))).text

                    
                    record.update({
                        "action": action.strip(),
                        "reason": compliance_reason.strip(),
                        "date": compliance_date.strip(),
                        "impact": impact.strip()
                    })
                    data.append(record)
                    try:
                        self.add_record_to_file(record)
                    except Exception as e:
                        print(e)
                except (NoSuchElementException, TimeoutException):
                    logger.warning('No Product Policy Compliance found')
                    result = False
            res = requests.post('http://account.kbslogisticsllc.com/api/health_reports', data={'data': json.dumps(data)})
            logger.info(json.dumps(data))
            logger.info(res)
        except (NoSuchElementException, TimeoutException):
            logger.warning('No Product Policy Compliance table found.')
            result = False
        return result

    def get_shadow_dom(self, shadow_host_elem):
        show_dom = self.driver.execute_script('return arguments[0].shadowRoot;', shadow_host_elem)
        return show_dom

    def page_number_find(self):
        page_number = None
        page_label_shadow_root = WebDriverWait(self.driver, 10, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["page_number"])))
        try:
            page_number = page_label_shadow_root.get_attribute("text").strip().split()[-1]
        except Exception as e:
            try:
                page_label_shadow = self.get_shadow_dom(page_label_shadow_root)
                page_label_elem = page_label_shadow.find_element_by_css_selector("label > slot > span")
                page_number = page_label_elem.get_attribute("text").strip().split()[-1]
            except Exception as e:
                print(e)
        return page_number

    def page_input_find(self):
        page_input = None
        
        try:
            page_input = WebDriverWait(self.driver, 10, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["page_input"])))
        except Exception as e:
            try:
                page_input_shadow_root = WebDriverWait(self.driver, 10, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["page_input_2"])))
                page_input_shadow = self.get_shadow_dom(page_input_shadow_root)
                page_input = page_input_shadow.find_element_by_css_selector("#katal-id-2")
            except Exception as e:
                print(e)
        return page_input

    def go_button_find(self):
        go_button = None
        try:
            go_button = WebDriverWait(self.driver, 10, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["go_button"])))
        except Exception as e:
            print(e)
        try:
            go_button_shadow = self.get_shadow_dom(go_button)
            go_button = go_button_shadow.find_element_by_css_selector("button")
        except Exception as e:
            print(e)
        return go_button
    
    def go_button_find_v2(self):
        next_page = None
        for _ in range(10):
            try:
                pagination_root = WebDriverWait(self.driver, 10, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#ahd-pp-pagination-katal-control')))
                pagination = self.get_shadow_dom(pagination_root)
                next_page_root = WebDriverWait(pagination, 10, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'nav > span:last-child > kat-icon')))
                next_page_elem = self.get_shadow_dom(next_page_root)
                next_page = next_page_elem.find_element_by_css_selector("i")
            except (NoSuchElementException, TimeoutException, StaleElementReferenceException):
                pass
        return next_page

    def find_report_page(self, seller_id, marketplace):
        
        page_number = self.page_number_find()

        pages_elems_shadow = WebDriverWait(self.driver, 12).until(
                EC.presence_of_element_located((By.XPATH, self.xpathes['pages_shadow']))
        )

        pages_elems_shadow_root = self.get_shadow_dom(pages_elems_shadow)

        if page_number:
            for page in range(int(page_number)):
                # page_input = self.page_input_find()
                # page_input.clear()
                # page_input.send_keys(i+1)
                # go_button = self.go_button_find_v2()
                # self.driver.execute_script('arguments[0].click();', go_button)

                page_elem = WebDriverWait(pages_elems_shadow_root, 12).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'ul.pages li[data-page="{}"]'.format(page+1)))
                )
                self.driver.execute_script("arguments[0].click()", page_elem)
                time.sleep(3)
                self.download_health_report(seller_id, marketplace)
    def scroll_down(self,):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def add_record_to_file(self, record):
        with open('C:\\AmazonReportDownloader\\records.txt', 'a', encoding="utf-8") as writer:
            writer.write(str(record) + "\n")