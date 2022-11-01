# -*- coding: utf-8 -*-

# Copyright © 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import time
import datetime
import sys
import random
import os
import io
import json

from selenium import webdriver
from cmutils.config_loaders import YamlConfigLoader
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException)
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from amazon_reports_downloader.operation_recorder import OperationRecorder
from amazon_reports_downloader import (
    logger, get_shared_driver, MARKETPLACE_MAPPING, DEBUG,
    downloaded_report_dir
)
from amazon_reports_downloader.helpers import SellerLoginHelper
from amazon_reports_downloader.inventory_manager import Download
from amazon_reports_downloader.operation_recorder import OperationRecorder
from amazon_reports_downloader.utils import close_web_driver


class CampaignManager():

    def __init__(self, config):
        self.config = config
        self.campaign_url = {'US': 'https://advertising.amazon.com/cm/campaigns?ref_=AAC_gnav_CM',
                            'CA': 'https://advertising.amazon.ca/cm/campaigns?ref_=AAC_gnav_CM'}
        # self.campaign_url = 'file:///Users/sky/KBPL/amazon_report_downloader/tests/pages/advertising/campaign.html'
        self.operation_recorder = OperationRecorder()
        self.report_type = 'Campaign'
        self.normal_budget = 20
        self.low_budget = 0


    def run(self):
        
        for marketplace in self.config['account']['campaigns']:
            marketplace = marketplace.upper()
            marketplace_lower = marketplace.lower()
            email = self.config['account']['email']
            password = self.config['account']['password']
            seller_id = self.config['account']['seller_id']
            reset_time = self.config['account']['reset_time']
            recover_time = self.config['account']['recover_time']
            self.campaigns = self.config['account']['campaigns']
            report_type = 'Campaign'

            if (not self.is_to_reset(reset_time, marketplace, seller_id)) and (not self.is_to_recover(recover_time, marketplace, seller_id)):
                continue

            try:
                self.driver = get_shared_driver(marketplace)
                helper = SellerLoginHelper(self.driver, email, password, marketplace)

                seller_central_url = 'https://{}/home'.format(
                    MARKETPLACE_MAPPING[marketplace_lower]['sellercentral'])
                self.driver.get(seller_central_url)

                while helper.is_login_required():
                    logger.info('Login required! Trying to login...')

                    helper.login()

                    wait_time = 180
                    while wait_time > 0:
                        wait_time -= 1
                        logger.debug('Waiting for login...')
                        if helper.is_login_required():
                            time.sleep(1)
                        else:
                            break

                    if wait_time <= 0:
                        logger.error('Could not login to seller central, exit!')
                        sys.exit(1)

                    time.sleep(7)

                    self.driver.get(seller_central_url)

                if helper.is_login_required():
                    message = '[LoginSellerCentralFailed] SellerID: {}, Marketplace: {}'.format(
                        seller_id, marketplace)
                    raise Exception(message)

                # if not DEBUG:
                #     self.driver.set_window_position(1200, -900)

                logger.info('begin to pick marketplace')
                helper.pick_marketplace()
                logger.info('Picked marketplace!')

                self.trigger_reports_type('Advertising')
                self.driver.get(self.campaign_url[marketplace])
                if self.is_to_reset(reset_time):
                    for asin in self.campaigns[marketplace]:
                        if self.is_budget_record('reset_budget', seller_id, marketplace, asin):
                            continue

                        self.reset_budget(asin, seller_id, marketplace)

                if self.is_to_recover(recover_time) and (not self.is_to_reset(reset_time)):
                    for asin in self.campaigns[marketplace]:
                        if self.is_budget_record('recover_budget', seller_id, marketplace, asin):
                            continue

                        self.recover_budget(asin, seller_id, marketplace)
            except (SystemError, SystemExit, KeyboardInterrupt) as e:
                raise e
            except Exception as e:
                logger.exception(e)
            finally:
                self.cleanup()

    def cleanup(self):
        if self.driver is None:
            return

        close_web_driver(self.driver)
        self.driver = None

    def campaign_filter(self, asin):
        result = False

        search_box_xpath = '//*[@id="UCM-CM-APP:CAMPAIGNS:searchInput"]'
        for _ in range(3):
            try:
                search_box_elem = WebDriverWait(self.driver, 30, 0.5).until(
                    EC.element_to_be_clickable((By.XPATH, search_box_xpath)))
                search_box_elem.click()
                search_box_elem.clear()
                search_box_elem.send_keys(asin)
                search_box_elem.send_keys(Keys.RETURN)

                time.sleep(3)

                WebDriverWait(self.driver, 30).until(EC.inpresence_of_element_located((By.XPATH, '//div[@data-e2e-id="loading"]')))

                time.sleep(3)

                result = True
            except Exception as e:
                time.sleep(3)

            if result:
                break

        return result

    def reset_budget(self, asin, seller_id, marketplace):
        self.campaign_filter(asin)

        campaigns = self.get_campaigns()
        for campaign in campaigns:
            if campaigns[campaign]['state'] != 'Enabled':
                continue

            result = False
            logger.info(campaigns[campaign]['name'])

            for _ in range(10):
                try:
                    self.set_campaign_budget(campaigns[campaign]['name'], self.campaigns[marketplace][asin]['low_budget'])
                    # logger.info('campaign name: %s reset budget to %s.' % (campaigns[campaign]['name'], self.campaigns[asin]['low_budget']))

                    result = True
                except Exception as e:
                    logger.exception(e)

                if result:
                    record = {
                        'seller_id': seller_id,
                        'marketplace': marketplace,
                        'campaign': campaigns[campaign]['name']
                    }
                    self.operation_recorder.record('reset_budget', record)

                    break

                time.sleep(3)

    def trigger_reports_type(self, report_type):
        result = True
        report_xpath = {
            'Fulfillment': '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Fulfil")]',
            'Payments': '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Payments")]',
            'Advertising': '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Advertising")]'
        }

        if report_type not in report_xpath:
            return False

        report_link_xpath = report_xpath[report_type]
        while True:
            try:
                reports = WebDriverWait(self.driver, 5, 0.5).until(
                    EC.presence_of_element_located((By.ID, 'sc-navtab-reports')))
                time.sleep(random.randint(4, 7))
                webdriver.ActionChains(self.driver).move_to_element(reports).perform()
                logger.info('go to reports')
                js_change_display = 'document.querySelector("#sc-navtab-reports > ul").style.display = "block";'
                js_change_opacity = 'document.querySelector("#sc-navtab-reports > ul").style.opacity = 1;'
                self.driver.execute_script(js_change_display)
                self.driver.execute_script(js_change_opacity)
                WebDriverWait(self.driver, 3, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, report_link_xpath)))
                report_link = self.driver.find_element_by_xpath(report_link_xpath).get_attribute('href')
                self.driver.get(report_link)
                break
            except (StaleElementReferenceException):
                pass
            except (NoSuchElementException, TimeoutException):
                result = False
                break
        logger.info('trigger_reports_type: %s' % report_type)
        return result


    def recover_budget(self, asin, seller_id, marketplace):
        self.campaign_filter(asin)
        campaigns = self.get_campaigns()
        for campaign in campaigns:
            result = False
            if campaigns[campaign]['state'] != 'Enabled':
                continue

            for _ in range(10):
                try:
                    self.set_campaign_budget(campaigns[campaign]['name'], self.campaigns[marketplace][asin]['normal_budget'])
                    logger.info('campaign name: %s recover budget to %s.' % (campaigns[campaign]['name'], self.campaigns[marketplace][asin]['normal_budget']))
                    time.sleep(3)

                    if self.get_campaign_budget(campaigns[campaign]['name']) == self.campaigns[marketplace][asin]['normal_budget']:
                        result = True
                except Exception as e:
                    logger.info(e)

                if result:
                    record = {
                        'seller_id': seller_id,
                        'marketplace': marketplace,
                        'campaign': campaigns[campaign]['name']
                    }
                    self.operation_recorder.record('recover_budget', record)

                    break

                time.sleep(3)

    # def is_reset_recorded(self, seller_id, marketplace, record_type, record_time):
    #     last_record_time, last_record = self.operation_recorder.get_last_record(
    #         record_type,
    #         lambda record_time, record: self.filter_budget_records(record_time, record, seller_id, marketplace))

    #     return last_record_time and last_record

    def filter_budget_records(self, record_time, record, seller_id, marketplace, asin):
        marketplace = marketplace.upper()
        now = datetime.datetime.now()

        if record['seller_id'] != seller_id:
            return False

        if record['marketplace'] != marketplace:
            return False

        if record_time.date() != now.date():
            return False

        if record['campaign'].find(asin) == -1:
            return False

        return True

    def is_budget_record(self, budget_type, seller_id, marketplace, asin):
        last_record_time, last_record = self.operation_recorder.get_last_record(
            budget_type,
            lambda record_time, record: self.filter_budget_records(record_time, record, seller_id, marketplace, asin))

        return last_record_time and last_record

    def is_to_reset(self, reset_time, marketplace=None, seller_id=None):
        
        if reset_time:
            now = datetime.datetime.now()
            to_reset = now.hour >= reset_time
        else:
            to_reset = False

        if to_reset:
            logger.info('it is time to reset.')
        else:
            logger.info('it is not time to reset.')

        if not marketplace:
            return to_reset

        reset_done = True
        for asin in self.campaigns[marketplace]:
            if not self.is_budget_record('reset_budget', seller_id, marketplace, asin):
                reset_done = False
        if reset_done:
            logger.info('all campaigns reset done.')
        return to_reset and not reset_done

    def is_to_recover(self, recover_time, marketplace=None, seller_id=None):
        if recover_time:
            now = datetime.datetime.now()
            to_recover = now.hour >= recover_time
        else:
            to_recover = False

        if to_recover:
            logger.info('it is time to recover.')
        else:
            logger.info('it is not time to recover.')

        if not marketplace:
            return to_recover

        recover_done = True

        for asin in self.campaigns[marketplace]:
            if not self.is_budget_record('recover_budget', seller_id, marketplace, asin):
                recover_done = False

        if recover_done:
            logger.info('all campaigns recover done.')

        return to_recover and not recover_done

    def get_campaigns(self):
        result = True

        campaigns = dict()
        campaigns_table_xpath = '//div[@id="CAMPAIGNS" and @data-e2e-id="table"]'
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, campaigns_table_xpath)))
        except Exception as e:
            logger.exception(e)
            result = False
        else:
            state_elems = self.driver.find_elements_by_xpath(
                '//div[@data-udt-column-id="state-cell"]')
            for state_elem in state_elems:
                idx = state_elem.get_attribute('data-e2e-index').split('_')
                idx.pop()
                idx = '_'.join(idx)
                campaigns.setdefault(idx, dict())

                button_elem = WebDriverWait(state_elem, 7, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, './div/div/button')))
         
                state = button_elem.get_attribute('title')

                campaigns[idx]['state'] = state

        name_elems = self.driver.find_elements_by_xpath('//div[@data-udt-column-id="name-cell"]')
            
        for name_elem in name_elems:
            idx = name_elem.get_attribute('data-e2e-index').split('_')
            idx.pop()
            idx = '_'.join(idx)
            if idx not in campaigns:
                continue

            elem = WebDriverWait(name_elem, 7, 0.5).until(
                EC.presence_of_element_located((By.XPATH, './div/div/a')))
            
            name = elem.text.strip()
            campaigns[idx]['name'] = name

        status_elems = self.driver.find_elements_by_xpath(
            '//div[@data-udt-column-id="status-cell"]')
        for status_elem in status_elems:
            idx = status_elem.get_attribute('data-e2e-index').split('_')
            idx.pop()
            idx = '_'.join(idx)
            if idx not in campaigns:
                continue

            elem = WebDriverWait(status_elem, 7, 0.5).until(
                EC.presence_of_element_located((By.XPATH, './div/div[@data-e2e-id="statusText"]')))
            
            status = elem.get_attribute('title')
            campaigns[idx]['status'] = status

        budget_elems = self.driver.find_elements_by_xpath(
            '//div[@data-udt-column-id="budget-cell"]')
        for budget_elem in budget_elems:
            idx = budget_elem.get_attribute('data-e2e-index').split('_')
            idx.pop()
            idx = '_'.join(idx)
            if idx not in campaigns:
                continue
            elem = WebDriverWait(budget_elem, 7, 0.5).until(
                EC.presence_of_element_located((By.XPATH, './/input[@data-e2e-id="currencyInput"]')))
            budget_str = elem.get_attribute('value').replace(',', '')
            try:
                budget = round(float(budget_str), 2)
                campaigns[idx]['budget'] = budget
            except Exception as e:
                logger.exception(e)
                continue
        return campaigns

    def set_campaign_budget(self, name, budget):
        result = False

        budget_adjust_xpath = '//div[@id="portal"]//input[@data-e2e-id="editableCurrencyInput"]'
        for _ in range(10):
            try:
                elem = self.get_campaign_budget_elem(name)
                if not elem:
                    time.sleep(3)
                    continue

                webdriver.ActionChains(self.driver).move_to_element(elem).click(elem).perform()
            except Exception as e:
                logger.exception(e)

                time.sleep(3)

                continue

            try:
                WebDriverWait(self.driver, 45).until(
                    EC.presence_of_element_located((By.XPATH, budget_adjust_xpath)))
            except Exception as e:
                logger.exception(e)
                result = False
            else:
                input_elem = WebDriverWait(self.driver, 7, 0.5).until(
                    EC.element_to_be_clickable((By.XPATH, budget_adjust_xpath)))
                input_elem.clear()
                input_elem.send_keys(budget)
                save_elem = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '//div[@id="portal"]//button[@data-e2e-id="saveButton"]')))
            
                save_elem.click()

                cur_budget = self.get_campaign_budget(name)
                result = cur_budget == budget

            if result:
                break

        return result

    def get_campaign_budget(self, name):
        elem = self.get_campaign_budget_elem(name)
        if elem:
            budget_str = elem.get_attribute('value')
            budget = round(float(budget_str), 2)
        else:
            budget = 0

        return budget

    def get_campaign_budget_elem(self, name):
        try:
            xpath = '//div[@data-udt-column-id="name-cell" and .//a[contains(text(), "{}")]]'.format(
                name)
            campaign_elem = WebDriverWait(self.driver, 90, 0.5).until(
                EC.presence_of_element_located((By.XPATH, xpath)))
            idx = campaign_elem.get_attribute('data-e2e-index').split('_')
            idx.pop()
            idx = '_'.join(idx)
            xpath = '//div[@data-udt-column-id="budget-cell" and contains(@data-e2e-index, "{}")]'.format(idx)
            self.driver.maximize_window()
            budget_elem = WebDriverWait(self.driver, 7, 0.5).until(
                EC.presence_of_element_located((By.XPATH, xpath)))
            input_elem = WebDriverWait(budget_elem, 7, 0.5).until(
                EC.element_to_be_clickable((By.XPATH, './/input[@data-e2e-id="currencyInput"]')))
        except Exception as e:
            logger.exception(e)

            input_elem = None

        return input_elem

if __name__ == '__main__':
    if sys.platform.startswith('win'):
        work_dir = 'C:\\AmazonReportDownloader'
    else:
        work_dir = os.path.join(os.path.expanduser('~'), '.AmazonReportDownloader')


    if sys.platform.startswith('win'):
        config_path = os.path.join(work_dir, 'config.yml')
    else:
        config_path = os.path.join(work_dir, 'config.yml')

    if not os.path.isfile(config_path):
        logger.error('Could not find configuration file - %s', config_path)
        sys.exit(0)

    cl = YamlConfigLoader(config_path)
    config = cl.load()
    manager = CampaignManager(config)   
    manager.run()

    