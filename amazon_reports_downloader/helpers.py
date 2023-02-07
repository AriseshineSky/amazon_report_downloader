# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (TimeoutException, NoSuchElementException)
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys

from amazon_reports_downloader import MARKETPLACE_MAPPING, MARKETPLACE_MAPPING_V2
from amazon_reports_downloader import logger


class SellerLoginHelper(object):
    
    def __init__(self, driver, email, password, marketplace):
        self.driver = driver
        self.email = email
        self.password = password
        self.marketplace = marketplace.lower()
        

    def is_login_required(self):
        url = self.driver.current_url
        return url.find('/ap/signin') != -1 or url.find('/ap/mfa') != -1

    def login(self):
        rect = self.driver.get_window_rect()
        current_x = rect['x']
        current_y = rect['y']
        if rect['x'] < 0 or rect['y'] < 0:
            self.driver.set_window_position(0, 0)

        try:
            claimed_email_elem = self.driver.find_element_by_id('ap-claim')
            claimed_email = claimed_email_elem.get_attribute('value')

            if claimed_email.lower() != self.email.lower():
                add_account_elem = self.driver.find_element_by_id('cvf-account-switcher-add-accounts-link')
                self.br.get(add_account_elem.get_attribute('href'))
        except NoSuchElementException:
            pass

        try:
            email_elem = self.driver.find_element_by_id('ap_email')
            email_elem.clear()

            email_elem.send_keys(self.email)

            try:
                continue_elem = self.driver.find_element_by_id('continue')
                continue_elem.click()
            except NoSuchElementException:
                pass
        except NoSuchElementException:
            pass

        time.sleep(7)

        while True:
            try:
                try:
                    remember_elem = self.driver.find_element_by_name('rememberMe')
                    if not remember_elem.is_selected():
                        remember_elem.click()
                except NoSuchElementException:
                    pass

                password_elem = self.driver.find_element_by_id('ap_password')
                password_elem.clear()
                time.sleep(1)
                password_elem.send_keys(self.password)
                time.sleep(3)
                password_elem.send_keys(Keys.RETURN)
                time.sleep(1)
                break
            except NoSuchElementException:
                break

    def pick_marketplace(self):
        button_xpath = '//div[@id="partner-switcher"]/button'
        try:
            WebDriverWait(self.driver, 7, 0.5).until(EC.presence_of_element_located((By.XPATH, button_xpath)))
            print("marketplace version is v2")
            return self.pick_marketplace_v2()
        except Exception as e:
            print(e)
            print("marketplace version is v1")
        result = True

        marketplace_domain = MARKETPLACE_MAPPING.get(self.marketplace)['domain']
        picker_xpath = '//select[@id="sc-mkt-picker-switcher-select"]'
        target_xpath = picker_xpath + '//option[contains(text(), "{}")]'.format(marketplace_domain)
        try:
            picker_elem = WebDriverWait(self.driver, 12).until(
                EC.visibility_of_element_located((By.XPATH, picker_xpath)))
            picker_elem = Select(picker_elem)
            cur_marketplace = picker_elem.first_selected_option.text.strip()

            # get store name

            store_ele = self.driver.find_element_by_xpath('//*[@id="sc-mkt-picker-switcher-select"]/optgroup')
            store_name = store_ele.get_attribute('label')

            if cur_marketplace != marketplace_domain: #当前卖场和文件的卖场不同如何处理
                try:
                    print('switch market place')
                    if marketplace_domain == 'www.amazon.com':
                        # picker_elem.select_by_visible_text(marketplace_domain + ' ' + '-' + ' ' + store_name)
                        picker_elem.select_by_visible_text(marketplace_domain)
                    else:
                        picker_elem.select_by_visible_text(marketplace_domain)
                except Exception as e:
                    print(e)

            WebDriverWait(self.driver, 3).until(
                EC.element_located_to_be_selected((By.XPATH, target_xpath)))
        except (NoSuchElementException, TimeoutException) as e:
            result = False

        return result

    def pick_marketplace_v2(self):
        result = False
        current_marketplace_xpath = '//*[@id="partner-switcher"]/button'
        marketplace_elem = WebDriverWait(self.driver, 4).until(
                    EC.visibility_of_element_located((By.XPATH, current_marketplace_xpath)))
        marketplace = marketplace_elem.text
        logger.info(marketplace)

        marketplace_county = MARKETPLACE_MAPPING_V2.get(self.marketplace)['country']
        
        button_xpath = '//div[@id="partner-switcher"]/button'
        marketplace_elem_xpath = '//a[contains(text(),"{}")]'.format(marketplace_county)
        current_marketplace_xpath = '//*[@id="partner-switcher"]/button'

        for _ in range(10):
            try:
                button_elem = WebDriverWait(self.driver, 10, 0.5).until(EC.presence_of_element_located((By.XPATH, button_xpath)))
                button_elem.click()
                marketplace_elem = WebDriverWait(self.driver, 4).until(
                    EC.visibility_of_element_located((By.XPATH, marketplace_elem_xpath)))
                marketplace_elem.click()
                marketplace_elem = WebDriverWait(self.driver, 4).until(
                    EC.visibility_of_element_located((By.XPATH, current_marketplace_xpath)))
                marketplace = marketplace_elem.text
                logger.info(marketplace)
                if marketplace_county in marketplace:
                    result = True
                break
            except (NoSuchElementException, TimeoutException) as e:
                pass
        
        
        return result

        
