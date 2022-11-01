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

class PerformanceNotificationReporter(object):
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
            'go_button': '#ahd-pp-pagination-page-num-submit-button'
        }
        self.xpathes = {
            'notification_content': '//table[@id="bodyTable"] | //div[@id="app-root"]//pre',
            'notification_content_in_iframe': '/html/body',
            'notification_rows': './/kat-table-row[contains(@class, "starfleet-notification-row")]',
            'notification_table': '//*[@id="app-root"]//kat-table/kat-table-body',
            'page_number': '//*[@id="app-root"]/div[@class="starfleet-page-body"]/div[contains(@class, "border-bottom")]/div/div[contains(@class, "order-sm-first")]/div/kat-label[2]',
            'asin_xpath': './/div/span[contains(text(), "ASIN:")]',
            'impact_xpath': './/div[@class="kat-row kat-no-gutters ahd-product-policy-table-row"]/div[@class="kat-col-xs-4"]/span[1]',
            'action_xpath': './/div[contains(@class, "kat-row")]//div[4]/span',
            'pages_shadow': '//*[@id="ahd-pp-pagination-katal-control"]',
            'iframe': "//iframe[@class='starfleet-sanitized-iframe']"
        }
        self.record_path = 'C:\\AmazonReportDownloader\\performance_notification_records.txt'
        self.last_record_time, self.last_record = self.get_last_record()
        self.operation_recorder = OperationRecorder()
        

    def close_webdriver(self):
        if self.driver is None:
            return

        close_web_driver(self.driver)
        self.driver = None

    def check_exists_by_xpath(self, xpath):
        result = False
        for _ in range(5):
            try:
                WebDriverWait(self.driver, 2, 0.5).until(EC.presence_of_element_located((By.XPATH, xpath)))
                self.driver.find_element_by_xpath(xpath)
                result = True
                break
            except (StaleElementReferenceException):
                pass
            except (NoSuchElementException, TimeoutException):
                logger.warning('There is no iframe element')
        
        return result
    def date_range(self, date):
        today = datetime.today()
        days = (today - datetime.strptime(date, '%Y-%m-%d')).days
        return days

    def download_performance_notification(self, seller_id, marketplace):
        result = {
            "sellerID": seller_id,
            "marketPlace": marketplace
        }
        data = []
        status = 'pending'
        for _ in range(10):
            try:
                notification_table = WebDriverWait(self.driver, 10, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["notification_table"])))
                notification_table_rows = notification_table.find_elements_by_xpath(self.xpathes["notification_rows"])
                for row in notification_table_rows:
                    for _ in range(10):
                        try:
                            if 'starfleet-notification-row-mobile' in row.get_attribute('class'):
                                continue
                            notification_subject = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["notification_subject"]))).text
                            notification_date = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["notification_date"]))).text
                            record = dict()
                            record.update(result)
                            record.update({
                                "subject": notification_subject.strip(),
                            })
                            try:
                                record.update({
                                    "date": datetime.strptime(notification_date.strip(), '%B %d, %Y').strftime("%Y-%m-%d"),
                                })
                            except Exception as e:
                                try:
                                    record.update({
                                        "date": datetime.strptime(notification_date.strip(), '%d %B %Y').strftime("%Y-%m-%d"),
                                    })
                                except Exception as e:
                                    print(e)
                            try:
                                self.add_record_to_file(record)
                            except Exception as e:
                                print(e)
                            for _ in range(10):
                                try:
                                    notification_content = None
                                    notification_content_link = WebDriverWait(row, 5, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["notification_subject"]))).get_attribute("href")
                                    self.driver.execute_script("window.open('%s');" % notification_content_link)
                                    self.driver.switch_to.window(self.driver.window_handles[-1])
                                    if self.check_exists_by_xpath(self.xpathes["iframe"]):
                                        WebDriverWait(self.driver, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["iframe"])))
                                        iframe = self.driver.find_element_by_xpath(self.xpathes["iframe"])
                                        self.driver.switch_to.frame(iframe)
                                        notification_content = WebDriverWait(self.driver, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["notification_content_in_iframe"]))).get_attribute("innerHTML")
                                        self.driver.switch_to.default_content()
                                    else:
                                        notification_content = WebDriverWait(self.driver, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["notification_content"]))).get_attribute("innerHTML")
                                    record.update({
                                        "content": notification_content
                                    })
                                    self.driver.close()
                                    self.driver.switch_to.window(self.driver.window_handles[0])
                                    break
                                except (StaleElementReferenceException):
                                    pass
                                except (NoSuchElementException, TimeoutException):
                                    logger.warning('No Performance Notification Content found')
                            data.append(record)
                            if self.date_range(record.get('date')) > 3:
                                status = 'done'
                            break
                        except (StaleElementReferenceException):
                            pass
                        except (NoSuchElementException, TimeoutException):
                            logger.warning('No Performance Notification found')
                            result = False
                    if status == 'done':
                        break
                logger.info(data)
                res = requests.post('https://300gideon.com/api/v1/performance-notification', json={"data": data})
                # logger.info(json.dumps(data))
                logger.info(res)
                break
            except (StaleElementReferenceException):
                pass
            except (NoSuchElementException, TimeoutException):
                logger.warning('No Performance Notification table found.')
            
        return status

    def page_number_find(self):
        page_number = None
        page_label = WebDriverWait(self.driver, 10, 0.5).until(EC.presence_of_element_located((By.XPATH, self.xpathes["page_number"])))
        page_number = page_label.get_attribute("text").strip().split()[-1]
        return page_number

    def find_report_page(self, seller_id, marketplace):
        
        page_number = self.page_number_find()

        if page_number:
            for page in range(int(page_number)):

                page_elem = WebDriverWait(self.driver, 12).until(EC.presence_of_element_located((By.XPATH, '//*[@id="app-root"]/div[@class="starfleet-page-body"]/div[contains(@class, "border-bottom")]/div/div[contains(@class, "order-sm-last")]/kat-pagination/ul/li[contains(@class, \"page-%s\")]' % str(page+1))))
                self.driver.execute_script("arguments[0].click()", page_elem)
                time.sleep(3)
                if self.download_performance_notification(seller_id, marketplace) == 'done':
                    return

    def scroll_down(self,):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def add_record_to_file(self, record):
        with io.open(self.record_path, 'a', encoding='utf-8', errors='ignore') as fh:
            params = dict(record)
            record = json.dumps(params)
            record += '\n'
            fh.write(record)
    
    def is_notification_recorded(self, seller_id, marketplace, download_hours):
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
