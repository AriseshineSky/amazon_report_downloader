import time
import random
import os
from datetime import datetime, timedelta, timezone
import traceback

import requests
from selenium.webdriver.support.select import Select
from amazon_reports_downloader import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException)

import gideon
from gideon.rest import ApiException


class GideonUploader:
    def __init__(self, driver, domain, email, password):
        self.driver = driver
        self.domain = domain
        self.email = email
        self.password = password

        self.gideon_api = gideon.ImportsApi()
        self.gideon_api.api_client.configuration.host = domain

        self.report_types = {
            'advertising_report': {
                'upload_path': '/import_ads',
                'action': 'upload_ads_report'
            },
            'FBA_inventory_report': {
                'upload_path': '/import_inventory',
                'action': 'upload_fba_inventory_report'
            },
            'finance_report': {
                'upload_path': '/import_finances',
                'action': 'upload_finance_report'
            },
            'listings_report': {
                'upload_path': '/import_listings',
                'action': 'upload_listings_report'
            },
            'order_report': {
                'upload_path': '/import_orders',
                'action': 'upload_order_report'
            },
            'FBA_shipment_report': {
                'upload_path': '/import_orders',
                'action': 'upload_fba_shipment_report'
            },
            'FBA_shipment_tax_report': {
                'upload_path': '/import_orders',
                'action': 'upload_fba_shipment_tax_report'
            }
        }

        self.selectors = {
            'email': '#email',
            'password': '#password',
            'login': 'body > div.container-fluid > div > div > div > div > div > div > div.panel-body > form > div:nth-child(5) > div > button',
            'seller_selector': '#page-content-wrapper > div:nth-child(3) > div > div:nth-child(1) > div > div > div.panel-body > form > div:nth-child(4) > div > select',
            'order_seller_selector': '#page-content-wrapper > div:nth-child(3) > div > div:nth-child(1) > div > div > div.panel-body > form > div:nth-child(4) > div > select',
            'finance_seller_selector': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(4) > div > select',
            'FBA_shipments_seller_selector': '#page-content-wrapper > div:nth-child(3) > div > div:nth-child(2) > div > div > div.panel-body > form > div:nth-child(4) > div > select',
            'ads_seller_selector': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(4) > div > select',
            'campaigns_seller_selector': '#page-content-wrapper > div:nth-child(3) > div > div > div > div:nth-child(1) > div.panel-body > form > div:nth-child(4) > div > select',
            'searchterms_seller_selector': '#page-content-wrapper > div:nth-child(3) > div > div > div > div:nth-child(2) > div.panel-body > form > div:nth-child(4) > div > select',
            'orders_import': '#page-content-wrapper > div:nth-child(3) > div > div:nth-child(1) > div > div > div.panel-body > form > div:nth-child(6) > div > button',
            'finance_import': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(7) > div > button',
            'FBA_shipments_import': '#page-content-wrapper > div:nth-child(3) > div > div:nth-child(2) > div > div > div.panel-body > form > div:nth-child(6) > div > button',
            'shipments_tax_import': '#main-content > div > div:nth-child(3) > div > div > div.panel-body > form > div:nth-child(6) > div > button',
            'listings_seller_selector': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(4) > div > select',
            'FBA_inventory_seller_selector': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(4) > div > select',
            'shipments_tax_seller_selector': '#main-content > div > div:nth-child(3) > div > div > div.panel-body > form > div:nth-child(4) > div > select',
            'business_seller_selector': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(4) > div > select',
            'order_shipments_import': '#page-content-wrapper > div:nth-child(3) > div > div:nth-child(2) > div > div > div.panel-body > form > div:nth-child(6) > div > button',
            'campaigns_import': '#page-content-wrapper > div:nth-child(3) > div > div > div > div:nth-child(1) > div.panel-body > form > div:nth-child(8) > div > button',
            'ads_import': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(7) > div > button',
            'searchterms_import': '#page-content-wrapper > div:nth-child(3) > div > div > div > div:nth-child(2) > div.panel-body > form > div:nth-child(7) > div > button',
            'ads_country': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(5) > div > select',
            'finance_country': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(5) > div > select',
            'campaigns_country': '#page-content-wrapper > div:nth-child(3) > div > div > div > div:nth-child(1) > div.panel-body > form > div:nth-child(5) > div > select',
            'searchterms_country': '#page-content-wrapper > div:nth-child(3) > div > div > div > div:nth-child(2) > div.panel-body > form > div:nth-child(5) > div > select',
            'listings_country': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(5) > div > select',
            'FBA_inventory_country': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(5) > div > select',
            'business_country': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(6) > div > select',
            'campaigns_date': '#page-content-wrapper > div:nth-child(3) > div > div > div > div:nth-child(1) > div.panel-body > form > div:nth-child(6) > div > input[type=date]',
            'business_date': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(5) > div > input[type=date]',
            'listings_import': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(7) > div > button',
            'FBA_inventory_import': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(7) > div > button',
            'business_import': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(8) > div > button',
            'order_report': '#sc-navtab-reports'
        }

    def upload_report(self, report_type, report_path, seller_id, country=None):
        url = self.get_upload_url(report_type)
        if url is None:
            return False

        result = False
        for _ in range(0, 5):
            is_logged_in = self.login()
            if not is_logged_in:
                continue

            self.driver.get(url)
            try:
                action = getattr(self, self.report_types[report_type]['action'])
                result = action(report_path, seller_id, country)

                if result:
                    break
            except Exception as e:
                logger.exception(e)

        return result

    def login(self):
        url = self.get_login_url()
        window_openned = True
        try:
            handles = self.driver.window_handles
            js = 'window.open("{url}");'.format(url=url)
            self.driver.execute_script(js)

            WebDriverWait(self.driver, 7).until(EC.new_window_is_opened(handles))
            self.driver.switch_to.window(self.driver.window_handles[-1])
        except Exception as e:
            window_openned = False

            print(e)

        if not window_openned:
            return False

        if not self.is_login_required():
            return True

        result = True
        try:
            email_input_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['email'])))
            email_input_elem.clear()
            email_input_elem.send_keys(self.email)
            
            logger.info("put password")
            password_input_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['password'])))
            password_input_elem.clear()
            password_input_elem.send_keys(self.password)

            login_elem = WebDriverWait(self.driver, 7).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors['login'])))
            login_elem.click()
        except Exception as e:
            result = False

            logger.exception(e)

        return result
    
    def get_upload_url(self, report_type):
        if report_type in self.report_types:
            url = '{}{}'.format(self.domain, self.report_types[report_type]['upload_path'])
        else:
            url = None

        return url
    
    def get_login_url(self):
        return '{}/login'.format(self.domain)
    
    def is_login_required(self):
        required = True
        try:
            WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors['login'])))
        except (TimeoutException, NoSuchElementException):
            required = False
        
        return required
    
    def upload_order_report(self, report_path, seller_id, country=None):
        result = True

        file_type = 'orders_file'
        try:
            seller_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['order_seller_selector'])))
            Select(seller_elem).select_by_value(seller_id)
            file_upload = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, file_type))
            )

            logger.info("file_upload")
            file_upload.send_keys(report_path)
            time.sleep(random.randint(1, 3))

            logger.info("file import")
            WebDriverWait(self.driver, 30, 0.5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors['orders_import']))).click()
        except Exception as e:
            result = False

            logger.exception(e)

        return result

    def upload_ads_report(self, report_path, seller_id, country=None):
        result = True

        file_type = 'ads_file'
        try:
            seller_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['ads_seller_selector'])))
            Select(seller_elem).select_by_value(seller_id)

            logger.info("select country")
            country_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['ads_country'])))
            Select(country_elem).select_by_value(country)

            logger.info("file_upload")
            file_upload = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, file_type))
            )
            file_upload.send_keys(report_path)
            time.sleep(random.randint(1, 5))

            logger.info("file import")
            WebDriverWait(self.driver, 40, 0.5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors['ads_import']))).click()
        except Exception as e:
            result = False

            logger.exception(e)

        return result

    def upload_fba_inventory_report(self, report_path, seller_id, country=None):
        result = True

        file_type = 'inventory_file'
        try:
            seller_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['FBA_inventory_seller_selector'])))
            Select(seller_elem).select_by_value(seller_id)

            logger.info("select country")
            country_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['FBA_inventory_country'])))
            Select(country_elem).select_by_value(country)

            logger.info("file_upload")
            file_upload = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, file_type))
            )
            file_upload.send_keys(report_path)
            time.sleep(random.randint(1, 5))

            logger.info("file import")
            WebDriverWait(self.driver, 40, 0.5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors['FBA_inventory_import']))).click()
        except Exception as e:
            result = False

            logger.exception(e)

        return result

    def upload_finance_report(self, report_path, seller_id, country=None):
        result = True

        file_type = 'finances_file'
        try:
            seller_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['finance_seller_selector'])))
            Select(seller_elem).select_by_value(seller_id)

            logger.info("select country")
            country_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['finance_country'])))
            Select(country_elem).select_by_value(country)

            logger.info("file_upload")
            file_upload = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, file_type))
            )
            file_upload.send_keys(report_path)
            time.sleep(random.randint(1, 5))

            logger.info("file import")
            WebDriverWait(self.driver, 40, 0.5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors['finance_import']))).click()
        except Exception as e:
            result = False

            logger.exception(e)

        return result

    def upload_listings_report(self, report_path, seller_id, country=None):
        result = True

        file_type = 'listings_file'
        try:
            seller_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['listings_seller_selector'])))
            Select(seller_elem).select_by_value(seller_id)

            logger.info("select country")
            country_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['listings_country'])))
            Select(country_elem).select_by_value(country)

            logger.info("file_upload")
            file_upload = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, file_type))
            )
            file_upload.send_keys(report_path)
            time.sleep(random.randint(1, 5))

            logger.info("file import")
            WebDriverWait(self.driver, 40, 0.5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors['listings_import']))).click()
        except Exception as e:
            result = False

            logger.exception(e)

        return result

    def upload_fba_shipment_report(self, report_path, seller_id, country=None):
        result = True

        file_type = 'order_shipments_file'
        try:
            seller_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['FBA_shipments_seller_selector'])))
            Select(seller_elem).select_by_value(seller_id)

            logger.info("file_upload")
            file_upload = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, file_type))
            )
            file_upload.send_keys(report_path)

            import_btn = WebDriverWait(self.driver, 40, 0.5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors['FBA_shipments_import'])))
            self.driver.execute_script("arguments[0].scrollIntoView()", import_btn)
            time.sleep(random.randint(1, 5))

            logger.info("file import")
            self.driver.execute_script("arguments[0].click()", import_btn)
        except Exception as e:
            result = False

            logger.exception(e)

        return result

    def upload_fba_shipment_tax_report(self, report_path, seller_id, country=None):
        result = True

        file_type = 'tax_invoicing_file'
        try:
            seller_elem = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['shipments_tax_seller_selector'])))
            Select(seller_elem).select_by_value(seller_id)

            logger.info("file_upload")
            file_upload = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, file_type))
            )
            file_upload.send_keys(report_path)

            self.scroll_down()
            time.sleep(random.randint(1, 5))

            logger.info("file import")
            WebDriverWait(self.driver, 40, 0.5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors['shipments_tax_import']))).click()
        except Exception as e:
            result = False

            logger.exception(e)

        return result

    def scroll_down(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def is_report_uploaded(self, report_type, seller_id, country=None, date=None):
        if date is None:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        if country is None:
            country = ''

        imported_reports = []
        try:
            imported_reports = self.gideon_api.imports_get(
                seller_id=seller_id, marketplace=country,
                report_type=report_type, _date=date)
        except ApiException as e:
            logger.exception(e)

        return len(imported_reports) > 0
