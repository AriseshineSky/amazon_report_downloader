# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException)

from amazon_reports_downloader.utils import extract_balance_amount


class TransferManager(object):
    def __init__(self, driver):
        self.driver = driver
        self.selectors = {
            'xpathes': {
                'transfer_amount': '//*[@id="currentBalanceValue" or @id="availableBalanceValue"]/span',
                'request_transfer_button': '//*[@id="request_transfer_button" or @id="disburseToBankAccountButton"]',
                'return_to_summary_button': '//*[@id="go_back_button" or @id="goBackButton"]'
            }
        };

    def get_transfer_amount(self, marketplace):
        while True:
            try:
                current_balance_elem = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, self.selectors['xpathes']['transfer_amount'])))
                current_balance_str = current_balance_elem.text.strip()
                current_balance = extract_balance_amount(marketplace, current_balance_str)

                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                raise

        return current_balance

    def is_transfer_available(self):
        transfer_available = True
        try:
            WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located(
                    (By.XPATH, self.selectors['xpathes']['request_transfer_button'])))
        except (NoSuchElementException, TimeoutException) as e:
            transfer_available = False

        return transfer_available

    def is_transfer_success(self):
        transfer_success = True
        try:
            WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[contains(text(), "Successfully initiated amount transfer")]')))
        except (NoSuchElementException, TimeoutException) as e:
            transfer_success = False

        return transfer_success

    def has_transfer_alert(self):
        try:
            WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@id="DisburseNowDetails"]/div[contains(@class, "infoMessages")]')))
            transfer_alert = not self.is_transfer_success()
        except (NoSuchElementException, TimeoutException) as e:
            transfer_alert = False

        return transfer_alert

    def get_transfer_alert(self):
        while True:
            try:
                alert_elem = WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[@id="DisburseNowDetails"]/div[contains(@class, "infoMessages")]//ul')))
                alert_message = alert_elem.text.strip()
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException) as e:
                alert_message = ''
                break

        return alert_message

    def trigger_transfer(self):
        result = True

        while True:
            try:
                request_transfer_button_elem = WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located(
                        (By.XPATH, self.selectors['xpathes']['request_transfer_button'])))
                request_transfer_button_elem.click()

                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException) as e:
                result = False
                break

        return result

    def return_to_summary(self):
        result = True

        while True:
            try:
                return_to_summary_elem = WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located(
                        (By.XPATH, self.selectors['xpathes']['return_to_summary_button'])))
                return_to_summary_elem.click()

                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException) as e:
                result = False
                break

        return result
