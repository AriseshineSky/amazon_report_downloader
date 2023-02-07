# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import re
import pdb

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException)

from amazon_reports_downloader.utils import extract_balance_amount


class PaymentsManager(object):
    def __init__(self, driver, marketplace):
        self.driver = driver
        self.marketplace = marketplace.lower()

    def get_exchange_rate(self):
        while True:
            try:
                rate_elem = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//kat-popover-content[@id="katal-id-4"]/span[1]/div/p[1]/span')
                    )
                )
                rate_str = rate_elem.get_attribute('innerHTML').strip().split('=')[-1]
                rate_match = re.search(r'\d+.\d+', rate_str)
                rate = float(rate_match.group()) if rate_match else None
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                rate = None
                break
        return rate

    def get_instant_transfer_balance(self):
        balance = self.get_instant_transfer_balance_v1()
        if balance is not None:
            return balance

        balance = self.get_instant_transfer_balance_v2()

        return balance

    def get_instant_transfer_balance_v1(self):
        summary_xpath = '//div[@class="pPaymentSummary"]' + \
            '[descendant::strong[contains(text(), "Balance available for transfer now")]]'

        balance = None
        while True:
            try:
                summary_elem = WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, summary_xpath)))
                balance_elem = summary_elem.find_element_by_xpath(
                    './div[@class="pSummaryBlock"]/div[@class="pDetailLineValue"]')
                balance = extract_balance_amount(self.marketplace, balance_elem.text.strip())

                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException) as e:
                break

        return balance

    def get_instant_transfer_balance_v2(self):
        summary_xpath = '//kat-card[@class="linkable-multi-row-card"]' + \
            '[descendant::section[@class="available-balance-header"]]'
        balance_xpath = './div[@class="linkable-multi-row-card-rows-container"]/div[1]' + \
            '/div[@class="available-balance-row-with-children" or @class="available-balance-row"]' + \
            '/div[@class="available-currency-amount"]/span'

        balance = None
        while True:
            try:
                summary_elem = WebDriverWait(self.driver, 12).until(
                    EC.presence_of_element_located((By.XPATH, summary_xpath)))
                balance_elem = summary_elem.find_element_by_xpath(balance_xpath)
                balance_str = balance_elem.text.strip()
                balance = extract_balance_amount(self.marketplace, balance_str)

                if '-' in balance_str:
                    balance *= -1

                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException) as e:
                break

        return balance

    def get_closing_balance(self):
        return (self.get_total_balance(), self.get_unavailable_balance())

    def get_total_balance(self):
        total_balance = self.get_total_balance_v1()
        if total_balance is not None:
            return total_balance

        return self.get_total_balance_v2()

    def get_total_balance_v1(self):
        total_balance = None

        while True:
            try:
                total_closing_balance_elem = WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[@class="pDetailLine"][descendant::a[@id="Total balance"]]')))

                total_balance_elems = total_closing_balance_elem.find_elements_by_xpath(
                    './div[@class="pDetailLineValue"]/span')
                total_balance_str = ''.join(
                    [total_balance_elem.text.strip() for total_balance_elem in total_balance_elems])

                total_balance = extract_balance_amount(self.marketplace, total_balance_str)

                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                break

        return total_balance

    def get_total_balance_v2(self):
        total_closing_balance_wrapper_xpath = '//kat-card[@class="linkable-multi-row-card"]' + \
            '[descendant::div[@class="total-balance-header"]]'
        total_balance_xpath = './div[@class="linkable-multi-row-card-rows-container"]/div[1]' + \
            '/div[@class="currency-amount" or @class="underline-link"]'

        total_balance = None
        while True:
            try:
                total_closing_balance_elem = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, total_closing_balance_wrapper_xpath)))
                total_balance_elem = total_closing_balance_elem.find_element_by_xpath(total_balance_xpath)
                if total_balance_elem is None:
                    break

                total_balance_str = total_balance_elem.text.strip()
                total_balance = extract_balance_amount(self.marketplace, total_balance_str)
                if '-' in total_balance_str:
                    total_balance *= -1

                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                break

        return total_balance

    def get_unavailable_balance(self):
        unavailable_balance = self.get_unavailable_balance_v1()
        if unavailable_balance is not None:
            return unavailable_balance

        return self.get_unavailable_balance_v2()

    def get_unavailable_balance_v1(self):
        unavailable_balance = None

        while True:
            try:
                unavailable_closing_balance_elem = WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[@class="pDetailLine"][descendant::a[@id="Unavailable balance"]]')))

                unavailable_balance_elems = unavailable_closing_balance_elem.find_elements_by_xpath(
                    './div[@class="pDetailLineValue"]/span')
                unavailable_balance_str = ''.join(
                    [unavailable_balance_elem.text.strip() for unavailable_balance_elem in unavailable_balance_elems])
                unavailable_balance = extract_balance_amount(self.marketplace, unavailable_balance_str)

                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                break

        return unavailable_balance

    def get_unavailable_balance_v2(self):
        unavailable_closing_balance_xpath = '//div[@class="top-level-breakdown-details"]' + \
            '/h4[text()="Account Level Reserve"]/following-sibling::div[contains(@class, "breakdown-amount")]'

        unavailable_balance = None
        while True:
            try:
                unavailable_balance_elem = WebDriverWait(self.driver, 12).until(
                    EC.presence_of_element_located((By.XPATH, unavailable_closing_balance_xpath)))

                unavailable_balance_str = unavailable_balance_elem.text.strip()
                unavailable_balance = extract_balance_amount(self.marketplace, unavailable_balance_str)

                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                break

        return unavailable_balance

    def has_disburse_button(self):
        has_disburse_button = self.has_disburse_button_v1()
        if has_disburse_button is not None:
            return has_disburse_button

        return bool(self.has_disburse_button_v2())

    def has_disburse_button_v1(self):
        has_disburse_button = True

        try:
            WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="disburse_button_bottom_id"]')))
        except (NoSuchElementException, TimeoutException) as e:
            has_disburse_button = None

        return has_disburse_button

    def has_disburse_button_v2(self):
        has_disburse_button = True
        try:
            summary_elem = WebDriverWait(self.driver, 12).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     '//kat-card[@class="linkable-multi-row-card"][descendant::section[@class="available-balance-header"]]')))
            summary_elem.find_element_by_xpath(
                './div[@class="linkable-multi-row-card-rows-container"]/div[1]/div[@class="available-balance-row-with-children"]/div[@class="custom-child-available-balance"]/kat-button/button')
        except (NoSuchElementException, TimeoutException) as e:
            has_disburse_button = None

        return has_disburse_button

    def is_disburse_button_disabled(self, disburse_button):
        # return disburse_button.get_attribute('disabled') or \
        #     'Request Payment' not in disburse_button.text
        if disburse_button is None:
            return None

        return bool(disburse_button.get_attribute('disabled'))

    def get_disburse_button(self):
        disburse_button = self.get_disburse_button_v1()
        if disburse_button is not None:
            return disburse_button
        disburse_button = self.get_disburse_button_v2()
        if disburse_button is not None:
            return disburse_button
        return self.get_disburse_button_v3()

    def get_disburse_button_v1(self):
        disburse_button = None
        try:
            disburse_button = WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="disburse_button_bottom_id"]')))
        except (NoSuchElementException, TimeoutException) as e:
            pass

        return disburse_button

    def get_disburse_button_v2(self):
        disburse_button = None
        try:
            summary_elem = WebDriverWait(self.driver, 12).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     '//kat-card[@class="linkable-multi-row-card"][descendant::section[@class="available-balance-header"]]')))
            disburse_button = summary_elem.find_element_by_xpath(
                './div[@class="linkable-multi-row-card-rows-container"]/div[1]/div[@class="available-balance-row-with-children"]/div[@class="custom-child-available-balance"]/kat-button/button')
        except (NoSuchElementException, TimeoutException) as e:
            pass

        return disburse_button
    
    def get_disburse_button_v3(self):
        disburse_button = None
        try:
            summary_elem = WebDriverWait(self.driver, 12).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     '//kat-card[@class="linkable-multi-row-card"][descendant::section[@class="available-balance-header"]]')))
            kat_button = summary_elem.find_element_by_xpath(
                './div[@class="linkable-multi-row-card-rows-container"]/div[1]/div[@class="available-balance-row-with-children"]/div[@class="custom-child-available-balance"]/kat-button')
            disburse_button = self.query_shadow_dom(kat_button, "button")
        except (NoSuchElementException, TimeoutException) as e:
            pass

        return disburse_button

    def get_shadow_dom(self, shadow_host_elem):
        show_dom = self.driver.execute_script('return arguments[0].shadowRoot;', shadow_host_elem)
        return show_dom
    
    def query_shadow_dom(self, shadow_host_elem, css_selector):
        return self.driver.execute_script('return arguments[0].shadowRoot.querySelector("{}");'.format(css_selector), shadow_host_elem)

    def query_shadow_dom_all(self, shadow_host_elem, css_selector):
        return self.driver.execute_script('return arguments[0].shadowRoot.querySelectorAll("{}");'.format(css_selector), shadow_host_elem)

    def trigger_disburse(self):
        disburse_button = self.get_disburse_button()
        if disburse_button is None or self.is_disburse_button_disabled(disburse_button):
            return False

        disburse_button.click()

        return True
