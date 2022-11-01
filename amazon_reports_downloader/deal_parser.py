import time
import random
import re
import os
import io
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
from amazon_reports_downloader.operation_recorder import OperationRecorder

class DealReporter(object):
    def __init__(self, driver):
        self.driver = driver
        self._time_format = '%Y-%m-%d'
        self.selectors = {
            'compliance_reason': 'div[class^="kat-row"] > div:first-child a',
            'compliance_date': 'div[class^="kat-row"] > div:nth-child(2) span',
            'action_selector': 'div[class^="kat-row"] > div:nth-child(4) span',
            'impact_selector': 'div[class^="kat-row"] > div:nth-child(3) span:first-child',
            'notification_subject': '.pl-sm-c>a',
            'notification_date': '.starfleet-notification-date',
            'page_input': '#katal-id-2',
            'page_input_2': '#ahd-pp-pagination-page-num-input',
            'status_select': '#search-and-filters > span:nth-child(2) div[class*="smui-dropdown-header"]',
            'go_button': '#ahd-pp-pagination-page-num-submit-button',
            'ended_selector_host': '#search-and-filters > span:nth-child(2) > div > ul > li kat-checkbox[label="Ended"]',
            'canceled_selector_host': '#search-and-filters > span:nth-child(2) > div > ul > li kat-checkbox[label="Canceled"]',
            'ended_selector': 'div slot kat-label[text="Ended"]',
            'canceled_selector': 'div slot kat-label[text="Canceled"]',
            'ended_checked_host': 'div.checkbox',
            'ended_checked': 'div svg',
            'canceled_checked': 'div svg',
            'apply': '#search-and-filters > span:nth-child(2) > div > ul > kat-button[label="Apply"]'
        }
        self.xpathes = {
            'notification_content': '//table[@id="bodyTable"] | //div[@id="app-root"]//pre',
            'notification_content_in_iframe': '/html/body',
            'deal_title': './/kat-table-cell[1]//a//div[contains(@class, "hero-description")]',
            'deal_asin': './/kat-table-cell[1]/div/div/div[2]/div[2]',
            'deal_sku': './/kat-table-cell[1]/div/div/div[2]/div[3]',
            'deal_rows': '//*[@id="manage-table-container"]//kat-table/kat-table-body/kat-table-row',
            'product_rows': '//*[@id="smui-root"]//kat-table[contains(@class, "smui-table__products--review")]/kat-table-body/kat-table-row',
            'deal_fee': './/kat-table-cell[3]',
            'deal_type': './/kat-table-cell[1]//a//div[contains(text(), "7-day Deal")] | .//kat-table-cell[1]//a//div[contains(text(), "Lightning Deal")]',
            'deal_date_range': './/kat-table-cell[2]/div/div[2]',
            'deal_status_shadow_host': './/kat-table-cell[2]/div/div[4]/kat-badge',
            'deal_link': './/kat-table-cell[1]/div/a',
            'page_number': '//*[@id="smui-root"]//form[@name="pageNumber"]/span',
            'asin_xpath': './/div/span[contains(text(), "ASIN:")]',
            'impact_xpath': './/div[@class="kat-row kat-no-gutters ahd-product-policy-table-row"]/div[@class="kat-col-xs-4"]/span[1]',
            'action_xpath': './/div[contains(@class, "kat-row")]//div[4]/span',
            'pages_shadow': '//*[@id="ahd-pp-pagination-katal-control"]',
            'iframe': "//iframe[@class='starfleet-sanitized-iframe']",
            
        }
        self.record_path = 'C:\\AmazonReportDownloader\\deal_records.txt'
        self.operation_recorder = OperationRecorder()
        

    def close_webdriver(self):
        if self.driver is None:
            return

        close_web_driver(self.driver)
        self.driver = None

    def check_exists_by_xpath(self, xpath):
        result = False
        while True:
            try:
                WebDriverWait(self.driver, 2, 0.5).until(EC.presence_of_element_located((By.XPATH, xpath)))
                self.driver.find_element_by_xpath(xpath)
                result = True
                break
            except (StaleElementReferenceException):
                pass
            except (NoSuchElementException, TimeoutException):
                logger.warning('There is no iframe element')
                break
        
        return result
    def date_range(self, date):
        today = datetime.today()
        days = (today - datetime.strptime(date, '%Y-%m-%d')).days
        return days

    def get_products_from_deal(self, url):
        self.driver.execute_script("window.open('%s');" % url)
        self.driver.switch_to.window(self.driver.window_handles[-1])
        product_rows = None
        while True:
            try:
                product_rows = WebDriverWait(self.driver, 5, 0.5).until(EC.presence_of_all_elements_located((By.XPATH, self.xpathes["product_rows"])))
                break
            except (StaleElementReferenceException):
                pass
            except (NoSuchElementException, TimeoutException):
                logger.warning('No product found')
                break
        if product_rows == None:
            return False
        deal_skus = []
        deal_asins = []
        for row in product_rows:
            while True:
                try:
                    deal_sku = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["deal_sku"]))).text
                    deal_asin = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["deal_asin"]))).text
                    deal_skus.append(deal_sku)
                    deal_asins.append(deal_asin)
                    time.sleep(3)
                    break
                except (StaleElementReferenceException):
                    pass
                except (NoSuchElementException, TimeoutException):
                    logger.warning('product found')
                    break
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])           
        return deal_skus, deal_asins

    def download_deals(self, seller_id, marketplace):
        result = {
            "sellerId": seller_id,
            "marketPlace": marketplace
        }
        data = []
        status = 'pending'
        for _ in range(20):
            try:
                deal_rows = WebDriverWait(self.driver, 5, 0.5).until(EC.presence_of_all_elements_located((By.XPATH, self.xpathes["deal_rows"])))
                deal_rows_length = len(deal_rows)
                for i in range(deal_rows_length):
                    while True:
                        try:
                            row = WebDriverWait(self.driver, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["deal_rows"] + '[%s]' % str(i+1))))
                            deal_title = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["deal_title"]))).text
                            deal_type = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["deal_type"]))).text
                            if "Lightning Deal" in deal_type:
                                deal_type = "Lightning Deal"
                            deal_link = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["deal_link"]))).get_attribute("href")
                            deal_date_range = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["deal_date_range"]))).text
                            deal_fee = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["deal_fee"]))).text
                            deal_status_shadow_host = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["deal_status_shadow_host"])))
                            deal_status = deal_status_shadow_host.get_attribute('label')
                            record = dict()
                            record.update(result)
                            record.update({
                                "title": deal_title.strip(),
                                "date_range": deal_date_range.strip(),
                                "fee": deal_fee.replace('$', '').strip(),
                                "status": deal_status.strip(),
                                "type": deal_type,
                            })
                            try:
                                self.add_record_to_file(record)
                            except Exception as e:
                                print(e)
                            for _ in range(5):
                                try:
                                    deal_skus, deal_asins = self.get_products_from_deal(deal_link)
                                    record.update({
                                        "skus": deal_skus,
                                        "asins": deal_asins,
                                    })
                                    break
                                except (StaleElementReferenceException):
                                    pass
                                except (NoSuchElementException, TimeoutException):
                                    logger.warning('No deal Content found')
                                    break
                            data.append(record)
                            break
                        except (StaleElementReferenceException):
                            pass
                        except (NoSuchElementException, TimeoutException):
                            logger.warning('No deal found')
                            result = False
                            break
                logger.info(data)
                res = requests.post('https://300gideon.com/api/v1/deals', json={"data": json.dumps(data)})
                logger.info(json.dumps(data))
                logger.info(res)
                break
            except (StaleElementReferenceException):
                pass
            except (NoSuchElementException, TimeoutException):
                logger.warning('No Performance Notification table found.')
                break
            
        return status

    def page_number_find(self):
        page_number = None
        while True:
            try:
                page_label = WebDriverWait(self.driver, 10, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, self.xpathes["page_number"])))
                page_number = page_label.text.strip().split()[-1]
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                break
        
        return page_number

    def find_report_page(self, seller_id, marketplace):
        
        page_number = self.page_number_find()

        if page_number:
            for page in range(int(page_number)):
                while True:
                    try:
                        page_host_elem = WebDriverWait(self.driver, 12).until(EC.presence_of_element_located((By.XPATH, '//*[@id="smui-root"]//kat-pagination[@data-name="pageNumber"]')))
                        page_root_elem = self.get_shadow_dom(page_host_elem)
                        page_elem = page_root_elem.find_element_by_css_selector('nav ul li[data-page="%s"]' % (str(page+1)))
                        self.driver.execute_script("arguments[0].click()", page_elem)
                        time.sleep(3)
                        self.check_ended_deals()
                        self.download_deals(seller_id, marketplace)
                        break
                    except StaleElementReferenceException:
                        pass
                    except (NoSuchElementException, TimeoutException):
                        break

    def check_ended_deals(self,):
        while True:
            try:
                status_select = WebDriverWait(self.driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['status_select'])))
                status_select.click()
                ended_selector_host = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['ended_selector_host'])))
                ended_selector_root = self.get_shadow_dom(ended_selector_host)
                ended_selector = WebDriverWait(ended_selector_root, 10, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['ended_selector'])))
                ended = False
                for _ in range(20):
                    try:
                        WebDriverWait(ended_selector_root, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['ended_checked'])))
                        ended = True
                        break
                    except StaleElementReferenceException:
                        pass
                    except (NoSuchElementException, TimeoutException):
                        ended_selector.click()

                canceled_selector_host = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['canceled_selector_host'])))
                canceled_selector_root = self.get_shadow_dom(canceled_selector_host)
                canceled_selector = WebDriverWait(canceled_selector_root, 10, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['canceled_selector'])))
                canceled = False
                for _ in range(20):
                    try:
                        WebDriverWait(canceled_selector_root, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['canceled_checked'])))
                        canceled = True
                        break
                    except StaleElementReferenceException:
                        pass
                    except (NoSuchElementException, TimeoutException):
                        canceled_selector.click()
                if ended and canceled:
                    for _ in range(20):
                        try:
                            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['apply']))).click()
                            time.sleep(3)
                            return True
                        except StaleElementReferenceException:
                            pass
                        except (NoSuchElementException, TimeoutException):
                            break

            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                break
    def scroll_down(self,):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def add_record_to_file(self, record):
        with io.open(self.record_path, 'a', encoding='utf-8', errors='ignore') as fh:
            params = dict(record)
            record = json.dumps(params)
            record += '\n'
            fh.write(record)
    
    def is_deals_recorded(self, seller_id, marketplace, download_hours):
        last_record_date, last_record = self.operation_recorder.get_last_record(
            lambda record_time, record: self.filter_report_records(record_time, record, seller_id, marketplace, download_hours))

        return last_record_date and last_record

    def filter_report_records(self, record_time, record, seller_id, marketplace, download_hours):
        marketplace = marketplace.upper()
        now = datetime.datetime.now()

        if record['seller_id'] != seller_id:
            return False

        if record['marketplace'] != marketplace:
            return False

        if record_time.date() != now.date():
            return False

        found = False
        cnt = len(download_hours)
        for i, hour in enumerate(download_hours):
            if i == 0 and now.hour < hour:
                continue

            if i == (cnt - 1):
                next_hour = 24
            else:
                next_hour = download_hours[i + 1]

            if now.hour >= next_hour:
                continue

            hours = range(hour, next_hour)
            if record_time.hour in hours:
                found = True
                break

        return found

    def get_last_record(self, callback=None):
        result = (None, None)

        if not os.path.isfile(self.record_path):
            return result

        with io.open(self.record_path, encoding='utf-8', errors='ignore') as fh:
            lines = fh.readlines()
            lines.reverse()
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except Exception as e:
                    logger.exception(e)
                    record = None

                if record is None:
                    continue

                record_time = self.deformat_time(record.pop('date'))
                if callback and callable(callback):
                    try:
                        res = callback(record_time, record)
                    except:
                        res = False
                    if res:
                        result = (record_time, record)
                        break
                else:
                    result = (record_time, record)
                    break

        return result

    def get_all_record(self, callback=None):
        result = (None, None)

        if not os.path.isfile(self.record_path):
            return result

        with io.open(self.record_path, encoding='utf-8', errors='ignore') as fh:
            lines = fh.readlines()
            lines.reverse()
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except Exception as e:
                    logger.exception(e)
                    record = None

                if record is None:
                    continue

                record_time = self.deformat_time(record.pop('date'))
                if callback and callable(callback):
                    try:
                        res = callback(record_time, record)
                    except:
                        res = False
                    if res:
                        result = (record_time, record)
                        break
                else:
                    result = (record_time, record)
                    break

        return result

    def deformat_time(self, t_str):
        return datetime.strptime(t_str, self._time_format)

    def get_shadow_dom(self, shadow_host_elem):
        show_dom = self.driver.execute_script(
            'return arguments[0].shadowRoot;', shadow_host_elem)
        return show_dom