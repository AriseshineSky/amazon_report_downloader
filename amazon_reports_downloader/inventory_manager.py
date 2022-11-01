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


class InventoryManager(object):
    def __init__(self, driver):
        self.driver = driver
        self.selectors = {
            'total_products_selector': '#mt-header-count-value',
            'total_product_pages_selector': 'span.mt-totalpagecount',
            'page_input_selector': 'input#myitable-gotopage',
            'go_to_page_selector': '#myitable-gotopage-button > span > input',
            'select_all_selector': '#mt-select-all',
            'bulk_action_select_selector': 'div.mt-header-bulk-action select',
            'option_delete_selector': 'option#myitable-delete',
            'continue_selector': '#interstitialPageContinue-announce'
        }

    def get_total_products_cnt(self):
        total_products_cnt = 0
        total_products_str = ''
        for _ in range(30):
            try:
                total_products_elem = WebDriverWait(self.driver, 12).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['total_products_selector'])))
                total_products_str = total_products_elem.get_attribute('innerText')
                total_products_cnt = int(total_products_str.replace(',', ''))
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                raise RuntimeError(
                    'Could not find total products element - %s' % self.selectors['total_products_selector'])
            except ValueError:
                raise RuntimeError('Could not parse total products text - %s' % total_products_str)

        return total_products_cnt

    def get_total_product_pages_cnt(self):
        total_product_pages_cnt = 0
        total_product_pages_str = ''
        for _ in range(30):
            try:
                total_product_pages_elem = WebDriverWait(self.driver, 12).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['total_product_pages_selector'])))
                total_product_pages_str = total_product_pages_elem.text
                total_product_pages_cnt = int(total_product_pages_str.split(' ').pop())
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                total_product_pages_cnt = 0
                break
            except ValueError:
                raise RuntimeError('Could not parse total product pages text - %s' % total_product_pages_str)
            except:
                raise RuntimeError(
                    'Could not find total product pages element - %s' % self.selectors['total_product_pages_selector'])

        return total_product_pages_cnt

    def go_to_page(self, page):
        for _ in range(30):
            try:
                page_input_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['page_input_selector'])))
                page_input_elem.clear()
                page_input_elem.send_keys(page)

                go_to_page_elem = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['go_to_page_selector'])))
                go_to_page_elem.click()

                break
            except StaleElementReferenceException:
                pass
            except:
                break

    def select_all(self):
        for _ in range(30):
            try:
                select_all_elem = WebDriverWait(self.driver, 7).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors['select_all_selector'])))
                script = 'document.querySelector("{}").click()'.format(
                    self.selectors['select_all_selector'])
                self.driver.execute_script(script)
                break
            except StaleElementReferenceException as e:
                logger.exception(e)
            except WebDriverException as e:
                if e.msg.find('is not clickable') != -1:
                    logger.exception(e)
                    continue

                raise e
            except:
                raise RuntimeError(
                    'Could not find select all element - %s' % self.selectors['select_all_selector'])

    def scroll_down(self,):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def delete_selected(self):
        result = True

        for _ in range(30):
            try:
                bulk_action_select_elem = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors['bulk_action_select_selector'])))
                bulk_action_select = Select(bulk_action_select_elem)
                bulk_action_select.select_by_value('myitable-delete')
                break
            except StaleElementReferenceException:
                pass

        time.sleep(3)
        Alert(self.driver).accept()
       
        time.sleep(3)

        if '/inventory/confirmAction' in self.driver.current_url:
            for _ in range(30):
                try:
                    continue_elem = WebDriverWait(self.driver, 12).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['continue_selector'])))
                    script = 'document.querySelector("{}").click()'.format(
                        self.selectors['continue_selector'])
                    self.driver.execute_script(script)
                    # continue_elem.click()
                    break
                except StaleElementReferenceException:
                    pass
                except WebDriverException as e:
                    if e.msg.find('is not clickable') != -1:
                        logger.exception(e)
                        continue

                    raise e
                except  (NoSuchElementException, TimeoutException):
                    raise RuntimeError(
                        'Could not find continue element - %s' % self.selectors['continue_selector'])

            try:
                WebDriverWait(self.driver, 12).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Thanks for suggesting changes to the catalog')]")))
                logger.info('Selected products are deleted!')
            except (NoSuchElementException, TimeoutException):
                logger.warning('Delete result could not determined!')
                result = False

        return result

class Download(object):
    def __init__(self, driver):
        self.driver = driver
        self.selectors = {
            'total_products_selector': '#mt-header-count-value',
            'total_product_pages_selector': 'span.mt-totalpagecount',
            'page_input_selector': 'input#myitable-gotopage',
            'go_to_page_selector': '#myitable-gotopage-button > span > input',
            'select_all_selector': '#mt-select-all',
            'bulk_action_select_selector': 'div.mt-header-bulk-action select',
            'option_delete_selector': 'option#myitable-delete',
            'continue_selector': '#interstitialPageContinue-announce',
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
            'listings_seller_selector': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(4) > div > select',
            'FBA_inventory_seller_selector': '#page-content-wrapper > div:nth-child(3) > div > div > div > div > div.panel-body > form > div:nth-child(4) > div > select',
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

    def add_inventory(self, marketplace, seller_id, sku, units, package_l, package_w, package_h, package_weight, shipment_name, shipment_number, shipment_id, start):
        time.sleep(random.randint(4, 7))
        logger.info("shipment_id: " + shipment_id)
        logger.info("start: " + str(start))
        logger.info("shipment_number: " + str(shipment_number))
        logger.info("shipment_name: " + shipment_name)
        first_window = self.driver.current_window_handle
        for index in range(start, shipment_number):
            logger.info("index: " + str(index))
            if index > 0:
                self.driver.execute_script("window.open();")
                # Switch to the new window
                self.driver.switch_to.window(self.driver.window_handles[index])
                self.driver.get("https://sellercentral.amazon.{marketplace}/gp/homepage.html/ref=xx_home_logo_xx".format(
                    marketplace=marketplace))
                logger.info("https://sellercentral.amazon.{marketplace}/gp/homepage.html/ref=xx_home_logo_xx".format(
                    marketplace=marketplace))
                time.sleep(random.randint(4, 7))

            try:
                # 移动鼠标到inventory
                for i in range(0, 3):
                    click = 'false'
                    try:
                        inventory = WebDriverWait(self.driver, 40, 0.5).until(
                            EC.presence_of_element_located((By.ID, 'sc-navtab-inventory')))
                        time.sleep(random.randint(4, 7))
                        webdriver.ActionChains(self.driver).move_to_element(inventory).perform()
                        logger.info('go to inventory')

                        # click inventory reports

                        length = len(self.driver.find_elements_by_xpath('//*[@id="sc-navtab-inventory"]/ul/li'))
                        logger.info(length)
                        for i in range(1, length):
                            report_name = self.driver.find_element_by_xpath(
                                '//*[@id="sc-navtab-inventory"]/ul/li[{}]'.format(i)).text.strip()
                            if report_name.startswith('Manage Inventory'):
                                time.sleep(random.randint(7, 9))
                                js_click_inventory_reports = "document.querySelector('#sc-navtab-inventory > ul > li:nth-child({}) > a').click();".format(
                                    i)
                                self.driver.execute_script(js_click_inventory_reports)
                                logger.info('click Manage Inventory')
                                time.sleep(random.randint(1, 5))
                                click = 'true'
                                break
                        if click == 'true':
                            break
                    except Exception as e:
                        print(e)
                sku_search_input = self.driver.find_element_by_id('myitable-search')
                sku_search_input.send_keys(sku)
                time.sleep(random.randint(1, 3))
                js_click_search = "document.querySelector('#myitable-search-button > span > input').click();"
                self.driver.execute_script(js_click_search)
                logger.info('try to find this item ' + sku)
                time.sleep(random.randint(4, 7))
                try:
                    dropdown = WebDriverWait(self.driver, 40, 0.5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '#myitable table tr:last-child td:last-child .a-button-splitdropdown button')))
                    webdriver.ActionChains(self.driver).move_to_element(dropdown).perform()
                    time.sleep(random.randint(1, 4))
                    logger.info('go to dropdown')

                    try:
                        js_click_dropdown = "document.querySelector('#myitable table tr:last-child td:last-child .a-button-splitdropdown button').click();"
                        self.driver.execute_script(js_click_dropdown)

                    except Exception as e:
                        print(e)

                    time.sleep(random.randint(2, 4))
                except Exception as e:
                    print(e)
                    logger.info('can not find this item ' + sku)

                try:
                    length = len(self.driver.find_elements_by_xpath('//*[@id="a-popover-1"]/div/div/ul/li'))
                    logger.info('The length of the list is ' + str(length))
                except Exception as e:
                    print(e)
                    try:
                        self.driver.find_element_by_css_selector(
                            '#myitable > div.mt-content.clearfix > div > table > tbody > tr.mt-row > td:nth-child(17) > div.mt-save-button-dropdown-normal > span > span > span.a-button.a-button-group-last.a-button-splitdropdown > span > button').click()
                        time.sleep(random.randint(2, 4))
                        length = len(self.driver.find_elements_by_xpath('//*[@id="a-popover-1"]/div/div/ul/li'))
                    except Exception as e:
                        print(e)
                js_click_flag = False
                for i in range(1, length):
                    dropdown_name = self.driver.find_element_by_xpath(
                        '//*[@id="a-popover-1"]/div/div/ul/li[{}]'.format(i)).text.strip()
                    logger.info(dropdown_name + ' ' + str(i))
                    if dropdown_name.startswith('Send'):
                        logger.info(dropdown_name + ' ' + str(i))
                        time.sleep(random.randint(1, 5))
                        try:
                            js_click_send = "document.querySelector('#a-popover-1 > div > div > ul > li:nth-child({}) > a').click();".format(i)
                            self.driver.execute_script(js_click_send)
                            js_click_flag = True
                        except Exception as e:
                            print(e)

                        logger.info('click Send/Replenish Inventory')
                        time.sleep(random.randint(3, 7))
                        break
                if not js_click_flag:
                    try:
                        js_click_send = "document.querySelector('#dropdown1_5').click();".format(i)
                        self.driver.execute_script(js_click_send)
                    except Exception as e:
                        print(e)
                time.sleep(random.randint(5, 7))
                try:
                    WebDriverWait(self.driver, 40, 0.5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR,
                                                        '#save-manifest')))
                    continue_ele = self.driver.find_element_by_css_selector("#save-manifest")
                    if continue_ele.is_enabled():
                        js_click_send = "document.querySelector('#save-manifest').click();"
                        self.driver.execute_script(js_click_send)
                        time.sleep(random.randint(3, 7))
                except Exception as e:
                    print(e)
                    try:
                        self.driver.find_element_by_css_selector(
                            '#fba-core-page > div.fba-core-page-meta-landing-page.fba-core-page-meta-container > div.action > span:nth-child(2) > button').click()
                    except Exception as e:
                        print(e)
                logger.info('config Send')
                try:
                    limit = self.driver.find_element_by_css_selector('#plan-items > tr:nth-child(2) > td.item-errors.info > p.fba-core-alert-label.fba-core-alert-label-error').text.strip()
                    if limit == "Limited restock":
                        logger.info('Limited restock')
                        break
                except Exception as e:
                    print(e)

                try:

                    logger.info('length')
                    length_ele = self.driver.find_element_by_css_selector(
                        '#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(3) > form > input:nth-child(1)')
                    length_ele.clear()
                    length_ele.send_keys(package_l)
                    logger.info('w')
                    wide_ele = self.driver.find_element_by_css_selector(
                        '#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(3) > form > input:nth-child(2)')

                    wide_ele.clear()
                    wide_ele.send_keys(package_w)
                    logger.info('h')
                    height_ele = self.driver.find_element_by_css_selector(
                        '#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(3) > form > input:nth-child(3)')

                    height_ele.clear()
                    height_ele.send_keys(package_h)

                    logger.info('weight')
                    weight_ele = self.driver.find_element_by_css_selector('#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(6) > form > input')

                    js_click_weight = "document.querySelector('#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(6) > form > select').value = 'G';"
                    self.driver.execute_script(js_click_weight)
                    weight_ele.send_keys(package_weight)

                    WebDriverWait(self.driver, 40, 0.5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR,
                                                        '#save-item-catalog-attributes')))

                    logger.info('begin to save')
                    js_click_save = "document.querySelector('#save-item-catalog-attributes').click();"
                    self.driver.execute_script(js_click_save)
                    logger.info('save done')
                    time.sleep(random.randint(4, 7))

                except Exception as e:
                    print(e)
                    print("do not need to add dimension")
                self.driver.find_element_by_css_selector(
                    '#batch-update-number-cases').send_keys(
                    units)
                WebDriverWait(self.driver, 40, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                                                    '#continue-plan')))
                js_click_continue = "document.querySelector('#continue-plan').click();".format(i)
                self.driver.execute_script(js_click_continue)

                time.sleep(random.randint(4, 7))
                try:
                    logger.info('click choose category')
                    WebDriverWait(self.driver, 40, 0.5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR,
                                                        '#prep-items > tr:nth-child(2) > td.prep-category > a')))
                    js_click_choose_category = "document.querySelector('#prep-items > tr:nth-child(2) > td.prep-category > a').click();"
                    self.driver.execute_script(js_click_choose_category)

                    logger.info('choose last one')

                    js_click_choose_no = "document.querySelector('#prep-categories').value = 'NONE';"
                    self.driver.execute_script(js_click_choose_no)
                    time.sleep(random.randint(1, 4))

                    logger.info('click choose')
                    js_click_choose = "document.querySelector('#choose-category-button').click();"
                    self.driver.execute_script(js_click_choose)
                    time.sleep(random.randint(4, 7))
                except Exception as e:
                    print(e)

                try:
                    logger.info('click continue')
                    js_click_continue = "document.querySelector('#continue-plan').click();"

                    self.driver.execute_script(js_click_continue)
                    time.sleep(random.randint(4, 7))
                except Exception as e:
                    print(e)

                for i in range(5):
                    try:
                        element = self.driver.find_element_by_css_selector("#continue-plan")
                        logger.info(element.is_enabled())
                        if element.is_enabled():
                            logger.info('click continue agin')
                            js_click_continue = "document.querySelector('#continue-plan').click();"
                            self.driver.execute_script(js_click_continue)
                            time.sleep(random.randint(2, 5))

                        if not element.is_enabled() and i < 2:
                            logger.info('continue is disabled')
                            js_click_all_products = "document.querySelector('#fba-core-tabs > li:nth-child(2) > a').click();"
                            self.driver.execute_script(js_click_all_products)
                            time.sleep(random.randint(2, 5))
                            logger.info('click products needs info')
                            try:

                                logger.info('length')
                                length_ele = self.driver.find_element_by_css_selector(
                                    '#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(3) > form > input:nth-child(1)')
                                length_ele.clear()
                                length_ele.send_keys(package_l)
                                logger.info('w')
                                wide_ele = self.driver.find_element_by_css_selector(
                                    '#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(3) > form > input:nth-child(2)')

                                wide_ele.clear()
                                wide_ele.send_keys(package_w)
                                logger.info('h')
                                height_ele = self.driver.find_element_by_css_selector(
                                    '#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(3) > form > input:nth-child(3)')

                                height_ele.clear()
                                height_ele.send_keys(package_h)

                                logger.info('weight')
                                weight_ele = self.driver.find_element_by_css_selector(
                                    '#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(6) > form > input')

                                js_click_weight = "document.querySelector('#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(6) > form > select').value = 'G';"
                                self.driver.execute_script(js_click_weight)
                                weight_ele.send_keys(package_weight)

                                time.sleep(random.randint(1, 4))

                                logger.info('begin to save')
                                js_click_save = "document.querySelector('#save-item-catalog-attributes').click();"
                                self.driver.execute_script(js_click_save)
                                logger.info('save done')
                                time.sleep(random.randint(4, 7))

                            except Exception as e:
                                print(e)
                                print("do not need to add dimension")
                            tot_ele = self.driver.find_element_by_css_selector(
                                '#batch-update-number-cases')
                            tot_ele.clear()
                            tot_ele.send_keys(
                                units)

                            num_ele = self.driver.find_element_by_css_selector(
                                "#plan-items > tr:nth-child(2) > td.number.indi-pack > input")
                            num_ele.clear()
                            num_ele.send_keys(
                                units)
                            logger.info('send value')
                            time.sleep(random.randint(4, 7))
                            logger.info('click continue agin')
                            js_click_continue = "document.querySelector('#continue-plan').click();"
                            self.driver.execute_script(js_click_continue)
                            time.sleep(random.randint(4, 7))
                        try:
                            element = self.driver.find_element_by_css_selector("#continue-plan")
                            logger.info(element.is_enabled())
                            if not element.is_enabled() and i > 1:
                                logger.info('continue is disabled')
                                js_click_all_products = "document.querySelector('#fba-core-tabs > li:nth-child(1) > a').click();"
                                self.driver.execute_script(js_click_all_products)
                                time.sleep(random.randint(4, 7))
                                logger.info('click all products')
                                try:
                                    js_click_length = "document.querySelector('#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(3) > form > select').value = 'CM';"
                                    self.driver.execute_script(js_click_length)

                                    logger.info('length')
                                    length_ele = self.driver.find_element_by_css_selector(
                                        '#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(3) > form > input:nth-child(1)')
                                    length_ele.clear()
                                    length_ele.send_keys(package_l)
                                    logger.info('w')
                                    wide_ele = self.driver.find_element_by_css_selector(
                                        '#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(3) > form > input:nth-child(2)')

                                    wide_ele.clear()
                                    wide_ele.send_keys(package_w)
                                    logger.info('h')
                                    height_ele = self.driver.find_element_by_css_selector(
                                        '#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(3) > form > input:nth-child(3)')

                                    height_ele.clear()
                                    height_ele.send_keys(package_h)

                                    logger.info('weight')
                                    weight_ele = self.driver.find_element_by_css_selector(
                                        '#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(6) > form > input')

                                    js_click_weight = "document.querySelector('#plan-items > tr:nth-child(2) > td.item-errors.info > div:nth-child(6) > form > select').value = 'G';"
                                    self.driver.execute_script(js_click_weight)
                                    weight_ele.send_keys(package_weight)

                                    time.sleep(random.randint(4, 7))

                                    logger.info('begin to save')
                                    js_click_save = "document.querySelector('#save-item-catalog-attributes').click();"
                                    self.driver.execute_script(js_click_save)
                                    logger.info('save done')
                                    time.sleep(random.randint(4, 7))

                                except Exception as e:
                                    print(e)
                                    print("do not need to add dimension")
                                tot_ele = self.driver.find_element_by_css_selector(
                                    '#batch-update-number-cases')
                                tot_ele.clear()
                                tot_ele.send_keys(
                                    units)

                                num_ele = self.driver.find_element_by_css_selector(
                                    "#plan-items > tr:nth-child(2) > td.number.indi-pack > input")
                                num_ele.clear()
                                num_ele.send_keys(
                                    units)
                                logger.info('send value')
                                time.sleep(random.randint(4, 7))
                                logger.info('click continue agin')
                                js_click_continue = "document.querySelector('#continue-plan').click();"
                                self.driver.execute_script(js_click_continue)
                                time.sleep(random.randint(4, 7))
                        except Exception as e:
                            print(e)
                    except Exception as e:
                        print(e)
                logger.info(index)
                logger.info(shipment_id)
                if index == 0:
                    logger.info(shipment_name)
                    elem = self.driver.find_element_by_css_selector('#fba-core-workflow-shipment-summary-shipment > tr:nth-child(1) > td:nth-child(1) > ul > li:nth-child(1) > input.fba-core-input.fba-core-input-large.new-shipment-name.fba-core-input-text')
                    elem.clear()
                    elem.send_keys(shipment_name)
                    time.sleep(random.randint(1, 5))

                else:
                    pass

            except Exception as e:
                print(e)
        self.driver.switch_to.window(first_window)
        js_click_continue = "document.querySelector('#fba-inbound-manifest-workflow-preview-edit-create-shipments').click();"
        self.driver.execute_script(js_click_continue)
        logger.info('confirm')
        time.sleep(random.randint(3, 5))
        WebDriverWait(self.driver, 40, 0.5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                                            '#fba-core-workflow-shipment-summary-shipment > tr:nth-child(1) > td:nth-child(2)')))

        try:
            shipment_id = self.driver.find_element_by_css_selector("#fba-core-workflow-shipment-summary-shipment > tr:nth-child(1) > td:nth-child(2)").text.strip()

            logger.info("css" + shipment_id)
        except Exception as e:
            print(e)

        try:
            shipment_id = self.driver.find_element_by_xpath(
                "//*[@id='fba-core-workflow-shipment-summary-shipment']/tr[1]/td[2]").text.strip()

            logger.info("xpath" + shipment_id)
        except Exception as e:
            print(e)

        try:
            shipment_id = self.driver.find_element_by_xpath(
                "/html/body/div[2]/div[2]/div[2]/div/div[1]/div/div[1]/div/div/div[2]/div/div/table/tbody/tr[1]/td[2]").text.strip()

            logger.info("full" + shipment_id)
        except Exception as e:
            print(e)
        for index in range(shipment_number - 1, start - 1, -1):
            try:

                if index > 0:
                    self.driver.switch_to.window(self.driver.window_handles[index])
                    # Switch to the new window

                    self.driver.refresh()
                    time.sleep(random.randint(1, 3))
                    WebDriverWait(self.driver, 40, 0.5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '#fba-core-workflow-shipment-summary-shipment > tr:nth-child(1) > td:nth-child(1) > ul > li:nth-child(2) > input')))

                    js_click_continue = "document.querySelector('#fba-core-workflow-shipment-summary-shipment > tr:nth-child(1) > td:nth-child(1) > ul > li:nth-child(2) > input').click();"
                    self.driver.execute_script(js_click_continue)
                    time.sleep(random.randint(1, 5))
                    logger.info(shipment_id)
                    try:
                        js_click_continue = "document.querySelector('#fba-core-workflow-shipment-summary-shipment > tr:nth-child(1) > td:nth-child(1) > ul > li:nth-child(2) > select').value = " + dumps(
                            shipment_id)
                        logger.info(js_click_continue)
                        logger.info("dumps")

                        self.driver.execute_script(js_click_continue)
                    except Exception as e:
                        print(e)
                    time.sleep(random.randint(1, 5))

                    js_click_continue = "document.querySelector('#fba-inbound-manifest-workflow-preview-edit-create-shipments').className = 'amznBtn btn-lg-pri-arrowr';"
                    self.driver.execute_script(js_click_continue)

                    js_click_continue = "document.querySelector('#fba-inbound-manifest-workflow-preview-edit-create-shipments').disabled = false;"
                    self.driver.execute_script(js_click_continue)

                    js_click_continue = "document.querySelector('#fba-inbound-manifest-workflow-preview-edit-create-shipments').click();"
                    self.driver.execute_script(js_click_continue)
                    time.sleep(random.randint(2, 4))
                    self.driver.close()
                else:
                    self.driver.switch_to.window(first_window)
                    WebDriverWait(self.driver, 40, 0.5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR,
                                                        '#fba-core-workflow-shipment-summary-shipment > tr:nth-child(1) > td:nth-child(6) > button')))

                    js_click_continue = "document.querySelector('#fba-core-workflow-shipment-summary-shipment > tr:nth-child(1) > td:nth-child(6) > button').click();"
                    self.driver.execute_script(js_click_continue)
                    time.sleep(random.randint(1, 3))
                    self.driver.close()
            except Exception as e:
                print(e)

    def scroll_down(self,):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def go_to_listings_download_page(self):
        
        try:
            result = self.trigger_reports_type('All Listings')
            if not result:
                # 移动鼠标到inventory
                for i in range(0, 3):
                    click = 'false'
                    try:
                        inventory = WebDriverWait(self.driver, 40, 0.5).until(
                            EC.presence_of_element_located((By.ID, 'sc-navtab-inventory')))
                        time.sleep(random.randint(4, 7))
                        webdriver.ActionChains(self.driver).move_to_element(inventory).perform()

                        logger.info('go to inventory')
                        js_change_display = 'document.querySelector("#sc-navtab-inventory > ul").style.display = "block";'
                        js_change_opacity = 'document.querySelector("#sc-navtab-inventory > ul").style.opacity = 1;'
                        self.driver.execute_script(js_change_display)
                        self.driver.execute_script(js_change_opacity)
                        # click Inventory
                        try:
                            logger.info('click Inventory')
                            inventory_link = self.driver.find_element_by_xpath(
                                '//*[@id="sc-navtab-inventory"]/ul/li/a[contains(text(), "Inventory Reports")]').get_attribute(
                                'href')
                            self.driver.get(inventory_link)
                            break
                        except Exception as e:
                            print(e)

                    except Exception as e:
                        print(e)

            # click Report Type drop down
            time.sleep(random.randint(3, 5))

            if REFACTOR:
                status = dict()

                result = self.trigger_choose_report_type()
                if not result:
                    status['message'] = 'Failed to trigger choose report type!'
                    status['status'] = False
                    return status

                result = self.choose_report_type('All Listings Report')
                if not result:
                    status['message'] = 'Failed to choose "All Listings Report"!'
                    status['status'] = False
                    return status

                time.sleep(random.randint(1, 3))

                result = self.request_report()
                if not result:
                    status['message'] = 'Request report failed!'
                    status['status'] = False
                    return status

                time.sleep(random.randint(1, 3))
                self.driver.refresh()

                report_name = self.extract_report_name(self.driver.current_url)
                if report_name is None:
                    status['message'] = 'Failed to extract report name - {}!'.format(
                        self.driver.current_url)
                    status['status'] = False
                    return status

                # TODO
                # Detect whether listing report already exists, if it exists,
                # delete it and download a new one
                report_file_name = 'All+Listings+Report+{}.txt'.format(
                    datetime.utcnow().date().strftime("%m-%d-%Y"))
                self.remove_old_downloaded_reports(report_file_name)

                result = self.download_report(report_name)
                if not result:
                    status['message'] = 'Failed to download report!'
                    status['status'] = False
                    return status

                status['status'] = True
                status['message'] = '"All Listing Report" has been downloaded!'
                status['report_name'] = 'All+Listings+Report+{}.txt'.format(
                    datetime.utcnow().date().strftime("%m-%d-%Y"))

                return status
            else:
                drop_down_js = 'document.querySelector("#a-autoid-0-announce").click();'
                self.driver.execute_script(drop_down_js)
                logger.info('click Report Type drop down')
                time.sleep(random.randint(4, 7))

                # click all listing report

                WebDriverWait(self.driver, 5, 0.5).until(
                    EC.presence_of_element_located((By.ID, 'dropdown1_7')))
                all_listings_js = 'document.querySelector("#dropdown1_7").click();'
                self.driver.execute_script(all_listings_js)

                logger.info('click all listing report')
                time.sleep(random.randint(4, 7))

                # click request report button

                request_report_js = 'document.querySelector("#a-autoid-5 input").click();'
                self.driver.execute_script(request_report_js)

                logger.info('click request report button')
                time.sleep(random.randint(4, 7))

                self.driver.refresh()

                # download
                current_url = self.driver.current_url

                # 匹配“report_reference_id=”后面的数字
                pattern = re.compile(r'(?<=report_reference_id=)\d+\.?\d*')
                id = pattern.findall(current_url)[0]
                time.sleep(random.randint(1, 6))
                self.driver.refresh()
                for i in range(0, 3):
                    try:
                        logger.info('%s-report_download' % id)
                        download_button = WebDriverWait(self.driver, 900, 0.5).until(EC.presence_of_element_located((By.ID, '%s-report_download' % id)))
                        download_report_js = '''document.querySelector("td[data-row='%s'] a").click();''' % id
                        self.driver.execute_script(download_report_js)
                        logger.info(download_button)
                        break
                    except Exception as e:
                        print(e)
                logger.info('All+Listings+Report+' + datetime.utcnow().date().strftime("%m-%d-%Y") + ".txt")
                time.sleep(random.randint(20, 50))
                return 'All+Listings+Report+' + datetime.utcnow().date().strftime("%m-%d-%Y") + ".txt"
        except Exception as e:
            self.save_page(traceback.format_exc())
            print(e)

    def trigger_choose_report_type(self):
        result = True
        try:
            report_type_choose_btn = WebDriverWait(self.driver, 10, 0.5).until(
                EC.element_to_be_clickable((By.ID, 'a-autoid-0-announce')))
            report_type_choose_btn.click()
        except (NoSuchElementException, TimeoutException):
            # Locate report type choose button failed, could not continue
            result = False

        return result

    def choose_report_type(self, report_type):
        # All Listings Report
        result = True
        for _ in range(30):
            try:
                report_type_option = WebDriverWait(self.driver, 10, 0.5).until(
                    EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "{}")]'.format(report_type))))
                report_type_option.click()

                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                result = False
                break

        return result

    def request_report(self):
        result = True

        while result:
            try:
                request_report_btn = WebDriverWait(self.driver, 7, 0.5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '#a-autoid-5 input, input[name="report-request-button"]')))
                request_report_btn.click()

                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                result = False

        return result

    def extract_report_name(self, url):
        report_name_pattern = re.compile(r'(?<=report_reference_id=)\d+\.?\d*')
        matched_data = report_name_pattern.findall(url)
        if matched_data:
            report_name = matched_data[0]
        else:
            report_name = None

        return report_name

    def download_report(self, report_name):
        result = False
        for i in range(0, 3):
            try:
                WebDriverWait(self.driver, 900, 0.5).until(
                    EC.visibility_of_element_located((By.ID, '{}-report_download'.format(report_name))))

                download_btn = WebDriverWait(self.driver, 7, 0.5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'td[data-row="{}"] a'.format(report_name))))
                download_btn.click()

                result = True

                break
            except (StaleElementReferenceException, NoSuchElementException, TimeoutException):
                pass

        return result

    def close_tooltips(self):
        # close tooltips
        try:
            self.driver.find_element_by_xpath('//*[@id="step-0"]/div[2]/button').click()
        except:
            pass


    def multi_download(self):
        # close tooltips
        try:
            self.driver.find_element_by_xpath('//*[@id="step-0"]/div[2]/button').click()
        except (StaleElementReferenceException, NoSuchElementException, TimeoutException):
            pass

    def choose_last_updated_date_v2(self):
        result = True
        for _ in range(30):
            try:
                report_type_elem = WebDriverWait(self.driver, 5, 0.5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="radio"][aria-label="Last Updated Date"]')))
                self.driver.execute_script('arguments[0].click();', report_type_elem)
                logger.info('choose last updated date')
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                logger.warning('Could not find last updated date element!')
                result = False
                break

        return result

    def choose_event_date_v2(self):
        result = True
        for _ in range(30):
            try:
                event_date_drop_down_elem = WebDriverWait(self.driver, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="daily-time-picker-style"]/kat-dropdown')))
                event_date_root_elem = self.driver.execute_script('return arguments[0].shadowRoot;', event_date_drop_down_elem)
                WebDriverWait(event_date_root_elem, 5, 0.5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.select-header'))).click()
                event_date_elem = WebDriverWait(event_date_root_elem, 5, 0.5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.kat-select-container kat-option[value="3"]')))
                self.driver.execute_script('arguments[0].click();', event_date_elem)
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                logger.warning('V2 Could not find event date element!')
                result = False
                break

        return result

    def request_download_click_v2(self):
        result = True
        for _ in range(30):
            try:
                request_download_shadow =  WebDriverWait(self.driver, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, '//kat-button[@label="Request Download"]')))
                request_download_root_elem = self.driver.execute_script('return arguments[0].shadowRoot;', request_download_shadow)
                request_download_elem = WebDriverWait(request_download_root_elem, 5, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[class="button"]')))
                self.driver.execute_script('arguments[0].click();', request_download_elem)
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                logger.warning('Could not find request download!')
                result = False
                break
        return result
        
    def choose_order_download(self):
        result = True

        # click order date drop down
        for _ in range(30):
            try:
                event_date_elem = WebDriverWait(self.driver, 5, 0.5).until(EC.element_to_be_clickable((By.XPATH, '//select[@name="eventDateTypeFilterOption"]')))
                event_date_select = Select(event_date_elem)
                event_date_select.select_by_value('lastUpdatedDate')
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                logger.warning('Could not find event date element!')
                result = False
                break
        if not result:
            if not self.choose_last_updated_date_v2():
                return False
            else:
                result = True

        time.sleep(random.randint(1, 3))

        # choose order date range
        for _ in range(30):
            try:
                order_date_elem = WebDriverWait(self.driver, 5, 0.5).until(EC.element_to_be_clickable((By.ID, 'downloadDateDropdown')))
                order_date_elem = Select(order_date_elem)
                order_date_elem.select_by_value('3')
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                logger.warning('Could not find order date element!')
                result = False
                break

        if not result:
            if not self.choose_event_date_v2():
                return False
            else:
                result = True

        time.sleep(random.randint(1, 3))
        if not self.request_download_click_v2():
            try:
                request_download_btn = 'javascript:FBAReporting.requestDownloadSubmit();'
                self.driver.execute_script(request_download_btn)
            except Exception as e:
                result = False

        return result

    def download_order_report_v2(self, country='us'):
        
        result = False
        
        for _ in range(5):
            try:
                self.driver.refresh()
                try:
                    download_btn_shadow = WebDriverWait(self.driver, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="download-page-margin-style"]//kat-table-body/kat-table-row[1]/kat-table-cell[4]/kat-button')))
                except (NoSuchElementException, TimeoutException):
                    download_btn_shadow = WebDriverWait(self.driver, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="report-page-margin-style"]//kat-table-body/kat-table-row[1]/kat-table-cell[4]/kat-button')))
                download_btn_root = self.driver.execute_script('return arguments[0].shadowRoot;', download_btn_shadow)
                download_btn = WebDriverWait(download_btn_root, 5, 0.5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[class="button"]')))
                self.driver.execute_script('arguments[0].click();', download_btn)
                result = self.check_report_filename('order', country) + '.txt'
                break

            except StaleElementReferenceException:
                time.sleep(30)
                pass
            except (NoSuchElementException, TimeoutException):
                logger.info('try to find download button')
                time.sleep(30)
        return result
    def download_order_report(self, country='us'):
        result = self.download_order_report_v2(country)
        if result:
            return result
        else:
            order_report_xpath = '//*[@id="downloadArchive"]/table/tbody/tr[1]/td[contains(text(), "No ") or child::a]'
            for _ in range(10):
                try:
                    order_report_elem = WebDriverWait(self.driver, 5, 0.5).until(
                        EC.presence_of_element_located((By.XPATH, order_report_xpath)))
                    if order_report_elem.text.find('No')!= -1:
                        logger.warning('No order data available')
                        result = False
                        break
                    download_button = order_report_elem.find_element_by_xpath('./a')
                    #download_button = self.driver.find_element_by_css_selector('#downloadArchive table tbody tr:first-child a')
                    download_link = download_button.get_attribute("href")
                    self.driver.get(download_link)
                    logger.info('downloading')
                    orders_name = re.findall(r"GET_FLAT_FILE_ALL_ORDERS_DATA_BY_LAST_UPDATE__(\d*)\.txt", download_link)[0]
                    logger.info(orders_name)
                    result = orders_name + '.txt'
                    break
                except StaleElementReferenceException:
                    pass
                except (NoSuchElementException, TimeoutException):
                    logger.warning('Click order report not successfully')
                    result = False

            return result

    def click_fufillment(self):
        logger.info('click fulfillments')
        WebDriverWait(self.driver, 3, 0.5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#downloadArchive table tbody tr:first-child a')))
        fulfillment_link = self.driver.find_element_by_xpath(
            '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Fulfil")]').get_attribute('href')
        self.driver.get(fulfillment_link)
        return True

    def click_all_orders(self):
        result = True

        all_orders_xpath = '//*[@id="sc-sidepanel"]//ul/li[descendant::a[text()="All Orders"] or @id="FlatFileAllOrdersReport"]//a'
        for _ in range(30):
            try:
                all_orders_elem = WebDriverWait(self.driver, 20, 0.5).until(
                    EC.element_to_be_clickable((By.XPATH, all_orders_xpath)))
                all_orders_elem.click()
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                result = False
                break

        return result

    def select_report_by_type_v1(self, report_type):
        result = True

        report_xpathes = {
            'order': '//*[@id="sc-sidepanel"]//ul/li[descendant::a[text()="All Orders"] or @id="FlatFileAllOrdersReport"]//a',
            'fba_inventory': '//*[@id="sc-sidepanel"]//ul/li[descendant::a[contains(text(), "Manage FBA Inventory")] or @id="FBA_MYI_UNSUPPRESSED_INVENTORY"]//a',
            'fba_shipment': '//*[@id="sc-sidepanel"]//ul/li[descendant::a[contains(text(), "Amazon Fulfilled Shipments")] or @id="AFNShipmentReport"]//a'
        }
        if report_type not in report_xpathes:
            return False

        report_link_xpath = report_xpathes[report_type]
        for _ in range(30):
            try:
                report_link_elem = WebDriverWait(self.driver, 20, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, report_link_xpath)))
                logger.info('find report link element.')
                if not report_link_elem.is_displayed():
                    # Click show more to make report link element clickable
                    logger.info('report link is not displayed.')
                    result = self.trigger_show_more(report_link_elem)
                    if not result:
                        return False
                logger.info('wait element to be clickable.')
                if report_type == 'fba_inventory':
                    try:
                        url_before = self.driver.current_url
                        logger.info('url_before: %s' % url_before)
                        js_click_inventory = 'document.querySelector("#FBA_MYI_UNSUPPRESSED_INVENTORY > a").click();'
                        self.driver.execute_script(js_click_inventory)
                        time.sleep(3)
                        url_after = self.driver.current_url
                        logger.info('url_after: %s' % url_after)
                        if url_before == url_after:
                            result = False
                            break
                    except Exception as e:
                        logger.info(e)

                try:
                    report_link_elem = WebDriverWait(self.driver, 20, 0.5).until(
                        EC.element_to_be_clickable((By.XPATH, report_link_xpath)))

                    report_link_elem.click()
                except Exception as e:
                    logger.info(e)
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                result = False
                break

        logger.info('select_report_by_type_v1: %s: %s' % (report_type, result))
        return result
    
    def trigger_all_show_more(self):

        show_more_xpath = '//*[@id="report-central-nav"]//label[contains(text(), "Show more")]'
        show_more_elems = self.driver.find_elements_by_xpath(show_more_xpath)
        for show_more_ele in show_more_elems:
            show_more_ele.click()

    def select_report_by_type_v2(self, report_type):
        result = True

        report_xpathes = {
            'order': '//*[@id="report-central-nav"]//kat-popover//a[descendant::span[text()="All Orders"]]',
            'fba_inventory': '//*[@id="report-central-nav"]//kat-popover//a[descendant::span[text()="Manage FBA Inventory"]]',
            'fba_shipment': '//*[@id="report-central-nav"]//kat-popover//a[descendant::span[text()="Amazon Fulfilled Shipments"]]'
        }
        if report_type not in report_xpathes:
            return False
        logger.info('find %s xpath' % report_type)
        report_link_xpath = report_xpathes[report_type]
        for _ in range(30):
            try:
                self.trigger_all_show_more()
                report_link_elem = WebDriverWait(self.driver, 20, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, report_link_xpath)))
                
                logger.info('find report link element.')
                if not report_link_elem.is_displayed():
                    # Click show more to make report link element clickable
                    logger.info('report link is not displayed.')
                    result = self.trigger_show_more(report_link_elem)
                    if not result:
                        return False
                logger.info('wait element to be clickable.')
                if report_type == 'fba_inventory':
                    try:
                        url_before = self.driver.current_url
                        logger.info('url_before: %s' % url_before)
                        js_click_inventory = 'document.querySelector("#FBA_MYI_UNSUPPRESSED_INVENTORY > a").click();'
                        self.driver.execute_script(js_click_inventory)
                        time.sleep(3)
                        url_after = self.driver.current_url
                        logger.info('url_after: %s' % url_after)
                        if url_before == url_after:
                            result = False
                            break
                    except Exception as e:
                        logger.info(e)

                try:
                    report_link_elem = WebDriverWait(self.driver, 20, 0.5).until(
                        EC.element_to_be_clickable((By.XPATH, report_link_xpath)))
                    logger.info('click report %s' % report_type)
                    report_link_elem.click()
                except Exception as e:
                    logger.info(e)
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                result = False
                break

        logger.info('select_report_by_type_v2: %s: %s' % (report_type, result))
        return result

    def trigger_show_more(self, elem):
        result = True

        show_more_xpath = './parent::li/following-sibling::li[contains(@class, "show-more")]/a[contains(text(), "Show more")]'
        for _ in range(30):
            try:
                logger.info('try to click show more')
                show_more_elem = elem.find_element_by_xpath(show_more_xpath)
                show_more_elem = WebDriverWait(elem, 5, 0.5).until(
                    EC.element_to_be_clickable((By.XPATH, show_more_xpath)))
                logger.info(show_more_elem.text)
                show_more_elem.click()

                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                message = 'Could not find Show-More report types element! XPATH: {}'.format(
                    show_more_xpath)
                logger.warning(message)

                result = False
                break
        logger.info('trigger show more done')
        return result

    def trigger_reports_type(self, report_type):
        result = True

        try:
            report_xpath = {
                'Fulfillment': '//a[span[contains(text(), "Fulfil") and not(contains(text(), "FBA")) and not(contains(text(), "Programs"))]]',
                'Payments': '//a[span[contains(text(), "Payments")]]',
                'Advertising': '//a[span[contains(text(), "Advertising")]]',
                'All Listings': '//a[span[contains(text(), "Inventory Reports")]]',
            }

            if report_type not in report_xpath:
                return False

            report_link_xpath = report_xpath[report_type]
            for _ in range(3):
                try:
                    WebDriverWait(self.driver, 3, 0.5).until(
                        EC.presence_of_element_located((By.XPATH, report_link_xpath)))
                    report_link = self.driver.find_element_by_xpath(report_link_xpath).get_attribute('href')
                    self.driver.get(report_link)
                    break
                except (StaleElementReferenceException):
                    pass
                except (NoSuchElementException, TimeoutException):
                    result = False
                    continue
            logger.info('trigger_reports_type: %s' % report_type)
            if result:
                return result
            if report_type == 'All Listings':
                return result
        except Exception as e:
            print(e)
        report_xpath = {
            'Fulfillment': '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Fulfil")]',
            'Payments': '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Payments")]',
            'Advertising': '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Advertising")]'
        }

        if report_type not in report_xpath:
            return False

        report_link_xpath = report_xpath[report_type]
        for _ in range(20):
            try:
                reports = WebDriverWait(self.driver, 25, 0.5).until(
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
                result = True
                break
            except (StaleElementReferenceException):
                pass
            except (NoSuchElementException, TimeoutException):
                result = False
                break
        logger.info('trigger_reports_type: %s' % report_type)
        return result

    def report_type_version_check(self):
        try:
            WebDriverWait(self.driver, 5, 0.5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="report-central-nav"]//kat-popover')))
            version = 'v2'
        except Exception as e:
            version = 'v1'
        return version

    def check_order_report_status(self, download_hours):
        result = False
        index = len(download_hours)
        logger.info(download_hours)
        for i in range(len(download_hours)):
            if (datetime.now().hour < download_hours[i]) and (datetime.now().hour > 0):
                index = i
                break
        logger.info(index)
        try:
            try:
                date_requested = WebDriverWait(self.driver, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="download-page-margin-style"]//kat-table-body/kat-table-row[%s]/kat-table-cell[3]' % (index)))).text.strip()
            except (NoSuchElementException, TimeoutException):
                date_requested = WebDriverWait(self.driver, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="report-page-margin-style"]//kat-table-body/kat-table-row[%s]/kat-table-cell[3]' % (index)))).text.strip()
            logger.info(date_requested)
            today_v1 = datetime.now().date().strftime("%B %d, %Y")
            today = datetime.now().date().timetuple()
            today_v2 = "%s. %s, %s" % (datetime.now().date().strftime("%b"), today.tm_mday, today.tm_year)
            today_v5 = "%s %s %s" % (today.tm_mday, datetime.now().date().strftime("%b"), today.tm_year)
            today_v4 = "%s %s, %s" % (datetime.now().date().strftime("%b"), today.tm_mday, today.tm_year)
            today_v3 = "%s %s, %s" % (datetime.now().date().strftime("%B"), today.tm_mday, today.tm_year)
            logger.info('today_v1: ' + today_v1)
            logger.info('today_v2: ' + today_v2)
            logger.info('today_v3: ' + today_v3)
            logger.info('today_v4: ' + today_v4)
            if (date_requested.strip() == today_v1 or date_requested.strip() == today_v2 or date_requested.strip() == today_v3 or date_requested.strip() == today_v4 or date_requested.strip() == today_v5):
                result = True
                logger.info("%s order report is already requested." % index)
        
        except Exception as e:
            logger.info(e)
        return result

    def go_to_orders_download_page(self, download_hours, country='us'):
        try:
            if REFACTOR:
                status = dict()

                result = self.trigger_reports_type('Fulfillment')
                if not result:
                    status['message'] = 'Failed to select Fulfillment!'
                    status['status'] = False
                    return status

                time.sleep(random.randint(1, 3))

                version = self.report_type_version_check()
                select_report_by_type = getattr(self, 'select_report_by_type_%s' % version)
                result = select_report_by_type('order')
                if not result:
                    status['message'] = 'Failed to select all orders!'
                    status['status'] = False
                    return status

                time.sleep(random.randint(1, 3))
                if not self.check_order_report_status(download_hours):
                    result = self.choose_order_download()
                    if not result:
                        status['message'] = 'Failed to choose order!'
                        status['status'] = False
                        return status
                else:


                    result = self.download_order_report(country)

                    if not result:
                        status['message'] = 'Failed to download order!'
                        status['status'] = False
                    else:
                        status['report_name'] = result
                        status['message'] = 'download order report successfully!'
                        status['status'] = True

                    return status

            else:

                # 移动鼠标到reports
                for i in range(0, 3):
                    click = 'false'
                    try:
                        reports = WebDriverWait(self.driver, 20, 0.5).until(
                            EC.presence_of_element_located((By.ID, 'sc-navtab-reports')))
                        time.sleep(random.randint(4, 7))
                        webdriver.ActionChains(self.driver).move_to_element(reports).perform()
                        logger.info('go to reports')
                        js_change_display = 'document.querySelector("#sc-navtab-reports > ul").style.display = "block";'
                        js_change_opacity = 'document.querySelector("#sc-navtab-reports > ul").style.opacity = 1;'
                        self.driver.execute_script(js_change_display)
                        self.driver.execute_script(js_change_opacity)
                        # click fulfillments
                        try:
                            if self.click_fufillment():
                                break
                        except Exception as e:
                            print(e)

                    except Exception as e:
                        print(e)

            
                js_click_all_orders = "document.querySelector('#FlatFileAllOrdersReport > a').click();"
                self.driver.execute_script(js_click_all_orders)

                logger.info('click all orders')
                time.sleep(random.randint(1, 7))

                # click order date drop down

                WebDriverWait(self.driver, 20, 0.5).until(EC.presence_of_element_located((By.ID, 'eventDateType'))).click()

                time.sleep(random.randint(1, 7))

                # select Last Updated Date

                WebDriverWait(self.driver, 20, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="eventDateType"]/select/option[2]'))).click()

                logger.info('choose Last Updated Date')
                time.sleep(random.randint(1, 7))

                # click last date drop down

                WebDriverWait(self.driver, 20, 0.5).until(
                    EC.presence_of_element_located((By.ID, 'downloadDateDropdown'))).click()

                time.sleep(random.randint(1, 7))

                # select Exact Date

                WebDriverWait(self.driver, 20, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="downloadDateDropdown"]/option[6]'))).click()

                time.sleep(random.randint(1, 7))

                # From today to today

                from_elem = WebDriverWait(self.driver, 40, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '#fromDateDownload')))
                # today = datetime.datetime.today().strftime("%m/%d/%Y")
                today = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-7))).strftime("%m/%d/%Y")
                time.sleep(random.randint(1, 7))
                for i in range(0, 30):
                    from_elem.send_keys('\b')
                from_elem.send_keys(today)
                logger.info(from_elem.get_attribute('value'))
                time.sleep(random.randint(3, 7))
                to_elem = WebDriverWait(self.driver, 40, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '#toDateDownload')))
                for i in range(0, 30):
                    to_elem.send_keys('\b')
                time.sleep(random.randint(1, 7))
                to_elem.send_keys(today)

                logger.info('select today')
                time.sleep(random.randint(4, 7))

                # click download

                WebDriverWait(self.driver, 120, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '#requestDownload button')))
                download_button = "document.querySelector('#requestDownload button').click();"
                self.driver.execute_script(download_button)

                logger.info('download request')

                time.sleep(random.randint(10, 20))

                WebDriverWait(self.driver, 120, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '#downloadArchive table tbody tr:first-child a')))
                download_button = self.driver.find_element_by_css_selector('#downloadArchive table tbody tr:first-child a')
                # download_button = WebDriverWait(self.driver, 40, 0.5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="downloadArchive"]/table/tbody/tr[1]/td[4]/a')))
                logger.info("download_button")

                download_link = download_button.get_attribute("href")

                logger.info(download_link)
                self.driver.get(download_link)
                logger.info('downloading')
                orders_name = re.findall(r"GET_FLAT_FILE_ALL_ORDERS_DATA_BY_LAST_UPDATE__(\d*)\.txt", download_link)[0]
                logger.info(orders_name)
                return orders_name + '.txt'

        except Exception as e:
            self.save_page(traceback.format_exc())
            print(e)

    def choose_fufillment_download(self): 
        AFN_btn = WebDriverWait(self.driver, 140, 0.5).until(EC.element_to_be_clickable((By.ID, 'downloadDateDropdown')))
        AFN_btn.click()
        pt = '#downloadDateDropdown > option:nth-child({})'.format(random.randint(1, 3))
        WebDriverWait(self.driver, 5, 0.5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, pt))).click()

        logger.info('date range')
        time.sleep(random.randint(1, 7))

    def download_fufillment(self):
        download_button = WebDriverWait(self.driver, 900, 0.5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#downloadArchive table tbody tr:first-child a')) or EC.presence_of_element_located((By.CSS_SELECTOR, '#downloadArchive table tbody tr:first-child a')))

        logger.info('downloading')
        time.sleep(random.randint(20, 50))

        download_link = download_button.get_attribute("href")
        logger.info(download_link)
        self.driver.get(download_link)
        FBA_shippment_name = re.findall(r"GET_AMAZON_FULFILLED_SHIPMENTS_DATA__(\d*)\.txt", download_link)[0]
        logger.info(FBA_shippment_name)
        return FBA_shippment_name + '.txt'

    def click_amazon_fulfillment_shipments(self):
        WebDriverWait(self.driver, 7, 0.5).until(EC.element_to_be_clickable((By.ID, 'AFNShipmentReport')))
        afs_button_click = "document.querySelector('#AFNShipmentReport').click();"
        self.driver.execute_script(afs_button_click)
        logger.info('click Amazon Fulfilled Shipments')
        return True

    def get_fulfilled_shipments_version(self):
        version_identifiers = {
            'v1': 'form#downloadReportForm select#downloadDateDropdown',
            'v2': 'form#downloadReportForm div.kat-select-container',
            'v3': 'div#daily-time-picker-style kat-dropdown'
        }

        try:
            css_selector = ', '.join(version_identifiers.values())
            WebDriverWait(self.driver, 3, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
        except (NoSuchElementException, TimeoutException):
            result = False
        else:
            result = False
            for k, v in version_identifiers.items():
                try:
                    self.driver.find_element_by_css_selector(v)
                    result = k
                    break
                except (NoSuchElementException, TimeoutException):
                    pass

        return result

    def choose_event_date_range_v1(self):
        result = False

        for _ in range(20):
            try:
                event_date_drop_down = WebDriverWait(self.driver, 7, 0.5).until(EC.element_to_be_clickable((By.ID, 'downloadDateDropdown')))
                Select(event_date_drop_down).select_by_value('7')
                result = True
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                break

        request_tsv_selector = 'tbody#requestCsvTsvDownload button[name="Request .txt Download"]'
        request_tsv_btn = self.driver.find_element_by_css_selector(request_tsv_selector)
        self.driver.execute_script(request_tsv_btn.get_attribute('onclick'))

        return result

    def choose_event_date_range_v2(self):
        result = False

        flag_element_xpath = '//div[@class="kat-select-container"]'
        try:
            WebDriverWait(self.driver, 3, 0.5).until(
                EC.presence_of_element_located((By.XPATH, flag_element_xpath)))
        except (NoSuchElementException, TimeoutException):
            pass
        else:
            select_dropdown_indicator_xpath = '//kat-icon[@name="chevron-down"]'
            indicator_elem = self.driver.find_element_by_xpath(select_dropdown_indicator_xpath)
            indicator_elem.click()

            last_7_days_option_xpath = '//div[@class="select-options"]//kat-option[@value="7"]'
            last_7_days_option = self.driver.find_element_by_xpath(last_7_days_option_xpath)
            last_7_days_option.click()

            option_text_elem = last_7_days_option.find_element_by_xpath(
                './div[@class="standard-option-content"]/div[@class="standard-option-name"]')
            option_text = option_text_elem.text.strip()
            option_selected_xpath = '//div[@class="kat-select-container"]//div[contains(@class, "header-row-text") and contains(text(), "{}")]'.format(option_text)
            WebDriverWait(self.driver, 3, 0.5).until(
                EC.presence_of_element_located((By.XPATH, option_selected_xpath)))

            result = True

        return result

    def choose_event_date_range_v3(self):
        result = False
        try:
            date_picker_dropdown_xpath = '//div[@id="daily-time-picker-style"]/kat-dropdown'
            date_picker_dropdown_elem = WebDriverWait(self.driver, 3, 0.5).until(
                EC.presence_of_element_located((By.XPATH, date_picker_dropdown_xpath)))
            date_picker_dropdown = self.get_shadow_dom(date_picker_dropdown_elem)

            indicator_elem = date_picker_dropdown.find_element_by_css_selector(
                'div.kat-select-container div.indicator kat-icon[name="chevron-down"]')
            self.driver.execute_script("arguments[0].click();", indicator_elem)
            # indicator_elem.click()

            date_range_option = date_picker_dropdown.find_element_by_css_selector(
                'div.kat-select-container div.select-options kat-option[value="{}"]'.format(7))
            date_range_option.click()

            time.sleep(1)

            logger.info('selected_days: 7')
            result = True
        except (NoSuchElementException, TimeoutException) as e:
            logger.exception(e)

        return result

    def choose_event_date_range(self):
        result = False

        flag_element_xpath = '//div[@class="kat-select-container"]'
        try:
            WebDriverWait(self.driver, 3, 0.5).until(
                EC.presence_of_element_located((By.XPATH, flag_element_xpath)))
        except (NoSuchElementException, TimeoutException):
            pass
        else:
            select_dropdown_indicator_xpath = '//kat-icon[@name="chevron-down"]'
            indicator_elem = self.driver.find_element_by_xpath(select_dropdown_indicator_xpath)
            indicator_elem.click()

            last_7_days_option_xpath = '//div[@class="select-options"]//kat-option[@value="7"]'
            last_7_days_option = self.driver.find_element_by_xpath(last_7_days_option_xpath)
            last_7_days_option.click()

            option_text_elem = last_7_days_option.find_element_by_xpath(
                './div[@class="standard-option-content"]/div[@class="standard-option-name"]')
            option_text = option_text_elem.text.strip()
            option_selected_xpath = '//div[@class="kat-select-container"]//div[contains(@class, "header-row-text") and contains(text(), "{}")]'.format(option_text)
            WebDriverWait(self.driver, 3, 0.5).until(
                EC.presence_of_element_located((By.XPATH, option_selected_xpath)))

            result = True

        return result

    def is_FBA_shipment_report_ready_v1(self):
        result = False
        report_ready_selector = 'div#downloadArchive tr.downloadTableRow:first-child td:last-child a[name="Download"]'
        try:
            download_report_btn = WebDriverWait(self.driver, 120, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, report_ready_selector)))

            result = True
        except (NoSuchElementException, TimeoutException):
            pass

        return result

    def check_report_filename(self, report_type, country='us'):
        report = None
        print(MARKETPLACE_MAPPING[country])
        report_name_url = {
                # 'shipment': 'https://%s/reportcentral/api/v1/getDownloadHistoryRecords?reportId=2500&isCountrySpecific=false' % (MARKETPLACE_MAPPING[country]['sellercentral']),
                'shipment': 'https://%s/reportcentral/api/v1/getDownloadHistoryRecords?reportId=2511&isCountrySpecific=false' % (MARKETPLACE_MAPPING[country]['sellercentral']),
                'order': 'https://%s/reportcentral/api/v1/getDownloadHistoryRecords?reportId=2400&reportId=2402&isCountrySpecific=false' % (MARKETPLACE_MAPPING[country]['sellercentral']),
                'tax': ('https://%s/reportcentral/api/v1/getDownloadHistoryRecords?reportId=2512&isCountrySpecific=false' % (MARKETPLACE_MAPPING[country]['sellercentral']) if country == 'us' else 'https://sellercentral.amazon.co.uk/reportcentral/api/v1/getDownloadHistoryRecords?reportId=2513&isCountrySpecific=false')
                }
        try:
            windows_before  = self.driver.current_window_handle
            
            self.driver.execute_script('''window.open("%s","_blank");''' % report_name_url[report_type])
            time.sleep(2)
            windows_after = self.driver.window_handles
            new_window = [x for x in windows_after if x != windows_before][-1]
            self.driver.switch_to_window(new_window)
            reports = WebDriverWait(self.driver, 120, 0.5).until(
                        EC.presence_of_element_located((By.XPATH, '//pre'))).text
            self.driver.close()
            self.driver.switch_to_window(windows_before)
            reports = json.loads(reports)
            report =reports[0]["reportReferenceId"]
        except Exception as e:
            print(e)
        return report

    def download_FBA_shipment_report_v1(self, country='us'):
        result = False

        time.sleep(random.randint(2, 5))
        report_name = None
        report_ready_selector = 'div#downloadArchive tr.downloadTableRow:first-child'
        for _ in range(10):
            self.driver.refresh()

            try:
                download_report_tr = WebDriverWait(self.driver, 60, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, report_ready_selector)))
                
                download_report_td = WebDriverWait(download_report_tr, 120, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, './td[contains(text(), "No ") or child::a]')))

                logger.info('Shipment is already.')
                if download_report_td.text.find('No') != -1:
                    print("No data")
                    return None

                download_report_btn = download_report_td.find_element_by_xpath('./a')
                download_link = download_report_btn.get_attribute('href')
                logger.info(download_link)
                self.driver.get(download_report_btn.get_attribute('href'))

                report_name = '{}.txt'.format(
                    re.findall(r"GET_AMAZON_FULFILLED_SHIPMENTS_DATA__(\d*)\.txt", download_link)[0])

                break
            except (NoSuchElementException, TimeoutException):
                pass

        if report_name:
            result = report_name

        return result

    def download_FBA_shipment_report_v2(self, country='us'):
        result = False

        request_tsv_xpath = '//kat-box[@id="report-page-kat-box"]/kat-button[value="TSV"]/button'
        request_tsv_btn = self.driver.find_element_by_xpath(request_tsv_xpath)
        request_tsv_btn.click()

        report_ready_xpath = '//kat-table/kat-table-body/kat-table-row[1]/kat-table-cell[last()]/kat-button[@label="Download"]'
        try:
            download_report_btn = WebDriverWait(self.driver, 120, 0.5).until(
                EC.presence_of_element_located((By.XPATH, report_ready_xpath)))
            download_report_btn.click()

            try:
                js_path = os.path.join(os.path.dirname(__file__), 'get_fba_shipment_reports.js')
                with open(js_path) as js_fh:
                    js_code = js_fh.read()
                    reports_history = self.driver.execute_script(js_code)
            except:
                reports_history = []
            
            logger.info('[DownloadReportsHistory] %s', reports_history)

            result = True
        except (NoSuchElementException, TimeoutException):
            pass

        return result

    def download_FBA_shipment_report_v3(self, country='us'):
        result = False
        for _ in range(100):
            try:
                time.sleep(5)
                download_btn = self.get_download_btn()
                if download_btn.text.strip() == 'Download':
                    result = self.check_report_filename('shipment', country) + '.txt'
                    logger.info('find download button.')
                    download_btn.click()
                    break
                else:
                    continue
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                break
        return result

    def download_FBA_shipment_tax_report_v3(self, country='us'):
        result = False
        for _ in range(100):
            try:
                time.sleep(5)
                download_btn = self.get_download_btn()
                if download_btn.text.strip() == 'Download':
                    result = self.check_report_filename('tax', country) + '.txt'
                    logger.info('find download button.')
                    download_btn.click()
                    break
                else:
                    continue
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                break
        return result
        
    def download_FBA_shipment_report(self):
        if True:
            result = False

            request_tsv_xpath = '//kat-box[@id="report-page-kat-box"]/kat-button[value="TSV"]/button'
            request_tsv_btn = self.driver.find_element_by_xpath(request_tsv_xpath)
            request_tsv_btn.click()

            report_ready_xpath = '//kat-table/kat-table-body/kat-table-row[1]/kat-table-cell[last()]/kat-button[@label="Download"]'
            try:
                download_report_btn = WebDriverWait(self.driver, 120, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, report_ready_xpath)))
                download_report_btn.click()

                try:
                    js_path = os.path.join(os.path.dirname(__file__), 'get_fba_shipment_reports.js')
                    with open(js_path) as js_fh:
                        js_code = js_fh.read()
                        reports_history = self.driver.execute_script(js_code)
                except:
                    reports_history = []
                
                logger.info('[DownloadReportsHistory] %s', reports_history)

                result = True
            except (NoSuchElementException, TimeoutException):
                pass

            return result
        else:
            FBA_shipment_report_xpath = '//*[@id="downloadArchive"]/table/tbody/tr[1]/td[contains(text(), "No ") or child::a]'

            for _ in range(30):
                try:
                    # click  Request .txt Download
                    try:
                        download_request_click = "javascript:FBAReporting.requestDownloadSubmitWithReportFileFormat('TSV');"
                        self.driver.execute_script(download_request_click)
                    except Exception as e:
                        print(e)

                    try:
                        request_txt_download_btn = WebDriverWait(self.driver, 7, 0.5).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="report-page-kat-box"]/kat-button[2]//button')))
                        request_txt_download_btn.click()
                    except StaleElementReferenceException:
                        pass
                    except (NoSuchElementException, TimeoutException):
                        break
                    
                    try:
                        download_btn = WebDriverWait(self.driver, 7, 0.5).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="download-page-margin-style"]/kat-table/kat-table-body/kat-table-row[1]/kat-table-cell[5]/kat-button//button')))
                        request_txt_download_btn.click()
                    except StaleElementReferenceException:
                        pass
                    except (NoSuchElementException, TimeoutException):
                        break
                    time.sleep(random.randint(4, 7))
                    logger.info('click  Request .txt Download')
                    download_button = WebDriverWait(self.driver, 900, 0.5).until(
                        EC.presence_of_element_located((By.XPATH, FBA_shipment_report_xpath)))

                    if download_button.text.find('No') != -1:
                        return None

                    logger.info('downloading')

                    # download_link = download_button.get_attribute("href")
                    download_link = download_button.find_element_by_xpath('./a').get_attribute("href")
                    self.driver.get(download_link)
                    time.sleep(random.randint(4, 7))
                    FBA_shippment_name = re.findall(r"GET_AMAZON_FULFILLED_SHIPMENTS_DATA__(\d*)\.txt", download_link)[0]
                    logger.info(FBA_shippment_name)
                    return FBA_shippment_name + '.txt'
                except StaleElementReferenceException:
                    pass
                except (NoSuchElementException, TimeoutException):
                    return False

    def is_FBA_inventory_report_ready_v1(self):
        result = False
        report_ready_selector = 'div#downloadArchive tr.downloadTableRow:first-child td:last-child a[name="Download"]'
        try:
            download_report_btn = WebDriverWait(self.driver, 120, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, report_ready_selector)))

            result = True
        except (NoSuchElementException, TimeoutException):
            pass

        return result

    def get_FBA_inventory_report_name_v1(self):
        report_ready_selector = 'div#downloadArchive tr.downloadTableRow:first-child td:last-child a[name="Download"]'
        try:
            download_report_btn = WebDriverWait(self.driver, 120, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, report_ready_selector)))
            download_link = download_report_btn.get_attribute('href')

            FBA_inventory_name = '{}.txt'.format(
                re.findall(r"GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA__(\d*)\.txt", download_link)[0])

            result = FBA_inventory_name
        except (NoSuchElementException, TimeoutException):
            result = None

        return result


    def trigger_FBA_inventory_report_download_v1(self):
        request_tsv_selector = 'tbody#requestCsvTsvDownload button[name="Request .txt Download"]'
        request_tsv_btn = self.driver.find_element_by_css_selector(request_tsv_selector)
        self.driver.execute_script(request_tsv_btn.get_attribute('onclick'))
        # request_tsv_btn.click()

    def check_shipment_status(self):
        result = False

        report_date_selector = 'div#downloadArchive tr.downloadTableRow:first-child td:nth-child(3), #download-page-margin-style > kat-table > kat-table-body > kat-table-row:nth-child(1) > kat-table-cell:nth-child(3), #report-page-margin-style > kat-table > kat-table-body > kat-table-row:nth-child(1) > kat-table-cell:nth-child(3)'
        report_type_selector = 'div#downloadArchive tr.downloadTableRow:first-child td:nth-child(4), #download-page-margin-style > kat-table > kat-table-body > kat-table-row:nth-child(1) > kat-table-cell:nth-child(4), #report-page-margin-style > kat-table > kat-table-body > kat-table-row:nth-child(1) > kat-table-cell:nth-child(4)'
        report_date_range_selector = 'div#downloadArchive tr.downloadTableRow:first-child td:nth-child(2), #download-page-margin-style > kat-table > kat-table-body > kat-table-row:nth-child(1) > kat-table-cell:nth-child(2), #report-page-margin-style > kat-table > kat-table-body > kat-table-row:nth-child(1) > kat-table-cell:nth-child(2)'
        for _ in range(3):
            self.driver.refresh()
            try:
                date_requested = WebDriverWait(self.driver, 10, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, report_date_selector))).text
                
                report_type = WebDriverWait(self.driver, 10, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, report_type_selector))).text.strip()
                logger.info('date_requested: ' + date_requested)
                today_v1 = datetime.now().date().strftime("%B %d, %Y")
                today = datetime.now().date().timetuple()
                today_v2 = "%s. %s, %s"%(datetime.now().date().strftime("%b"), today.tm_mday, today.tm_year)
                today_v5 = "%s %s %s"%(today.tm_mday, datetime.now().date().strftime("%b"), today.tm_year)
                today_v4 = "%s %s, %s"%(datetime.now().date().strftime("%b"), today.tm_mday, today.tm_year)
                today_v3 = "%s %s, %s"%(datetime.now().date().strftime("%B"), today.tm_mday, today.tm_year)
                logger.info('today_v1: ' + today_v1)
                logger.info('today_v2: ' + today_v2)
                logger.info('today_v3: ' + today_v3)
                logger.info('today_v4: ' + today_v4)
                date_range_covered = WebDriverWait(self.driver, 10, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, report_date_range_selector))).text.strip()
                end_date = date_range_covered

                yesterday = (datetime.now().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-7))) - timedelta(days=1)).strftime("%m/%d/%Y")
                
                if (date_requested.strip() == today_v1 or date_requested.strip() == today_v2 or date_requested.strip() == today_v3 or date_requested.strip() == today_v4 or date_requested.strip() == today_v5) and report_type.endswith('.txt'):
                    result = True
                    logger.info("Today's shipment report is already requested.")
                break
            except Exception as e:
                print(e)

        return result


    def download_FBA_inventory_report_v1(self):
        result = False

        report_ready_selector = 'div#downloadArchive tr.downloadTableRow:first-child td:last-child a[name="Download"]'
        for _ in range(10):
            self.driver.refresh()

            try:
                download_report_btn = WebDriverWait(self.driver, 60, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, report_ready_selector)))
                download_link = download_report_btn.get_attribute('href')
                self.driver.get(download_link)

                result = '{}.txt'.format(
                    re.findall(r"GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA__(\d*)\.txt", download_link)[0])

                break
            except (NoSuchElementException, TimeoutException):
                pass

        return result

    def click_request_download_v3(self):
        result = False
        request_download_btn_xpath = '//*[@id="report-page-kat-box"]/kat-button[2]'

        for _ in range(30):
            try:
                request_download_btn_elem = WebDriverWait(self.driver, 3, 0.5).until(
                EC.presence_of_element_located((By.XPATH, request_download_btn_xpath)))
                logger.info('find click request element')
                request_download_root = self.get_shadow_dom(request_download_btn_elem)
                request_download = WebDriverWait(request_download_root, 10, 0.5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.button div.content > slot > span')))
                logger.info('request_download: %s' % request_download.text.strip())

                self.driver.execute_script("arguments[0].click();", request_download)
                result = True
                logger.info('click request download.')
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                break

        return result

    def go_to_FBA_shipment_tax_download_page(self, country='us'):
        try:
            status = dict()
            result = self.trigger_reports_type('Fulfillment')

            if not result:
                status['message'] = 'Failed to select Fulfillment!'
                status['status'] = False
                return status

            time.sleep(random.randint(1, 3))
            
            result = self.choose_AFNShipment_tax_report()
            if not result:
                status['message'] = 'Failed to click AFN Shipment Report!'
                status['status'] = False
                return status
            
            version = self.get_fulfilled_shipments_version()
            logger.info(version)
            if not version:
                status['message'] = 'Failed to choose event date range!'
                status['status'] = False
                return status

            is_ready = self.check_shipment_status()
            if not is_ready:
                choose_event_date_method = getattr(self, 'choose_event_date_range_{}'.format(version))
                result = choose_event_date_method()
                if result:
                    click_request_download = getattr(
                    self, 'click_request_download_{}'.format(version))
                    result = click_request_download()
                status['message'] = 'Fulfillment report is not ready.'
                status['status'] = False
                return status
            else:
            
                download_FBA_shipment_tax_report_method = getattr(
                    self, 'download_FBA_shipment_tax_report_{}'.format(version))
                result = download_FBA_shipment_tax_report_method(country)
                if not result:
                    status['message'] = 'Failed to download shipment tax reports!'
                    status['status'] = False
                    return status
                elif result == None:
                    status['message'] = 'No shipment tax available.'
                    status['status'] = None
                else:
                    status['message'] = 'Download shipment tax report successfully!'
                    status['status'] = True
                    status['report_name'] = result
                    return status

            
        except Exception as e:
            self.save_page(traceback.format_exc())
            print(e)

    def choose_AFNShipment_tax_report(self):
        result = False
        AFNShipment_tax_report_xpath = '//*[@id="report-central-nav"]//h4[contains(text(), "Sales")]/following-sibling::div[1]/kat-popover[4]/a[@id="report-nav-link-url"]/li'
        for _ in range(20):
            try:
                tax_report_elem = WebDriverWait(self.driver, 12).until(EC.presence_of_element_located((By.XPATH, AFNShipment_tax_report_xpath)))
                tax_report_elem.click()
                result = True
                break
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                pass
        return result

    def go_to_FBA_shipment_download_page(self, country='us'):

        try:
            status = dict()

            result = self.trigger_reports_type('Fulfillment')
            if not result:
                status['message'] = 'Failed to select Fulfillment!'
                status['status'] = False
                return status

            time.sleep(random.randint(1, 3))

            # click Amazon Fulfilled Shipments
            version = self.report_type_version_check()
            select_report_by_type = getattr(self, 'select_report_by_type_%s' % version)
            result = select_report_by_type('fba_shipment')
            if not result:
                status['message'] = 'Failed to select Amazon Fulfillment Shipment!'
                status['status'] = False
                return status

            time.sleep(random.randint(1, 3))

            version = self.get_fulfilled_shipments_version()
            if not version:
                status['message'] = 'Failed to choose event date range!'
                status['status'] = False
                return status

            is_ready = self.check_shipment_status()
            if not is_ready:
                choose_event_date_method = getattr(self, 'choose_event_date_range_{}'.format(version))
                result = choose_event_date_method()
                if result:
                    click_request_download = getattr(
                    self, 'click_request_download_{}'.format(version))
                    result = click_request_download()
                status['message'] = 'Fulfillment report is not ready.'
                status['status'] = False
                return status

            else:
            
                download_FBA_shipment_report_method = getattr(
                    self, 'download_FBA_shipment_report_{}'.format(version))
                result = download_FBA_shipment_report_method(country)
                if not result:
                    status['message'] = 'Failed to download shipment reports!'
                    status['status'] = False
                    return status
                elif result == None:
                    status['message'] = 'No shipment data available.'
                    status['status'] = None
                else:
                    status['message'] = 'Download shipment reports successfully!'
                    status['status'] = True
                    status['report_name'] = result
                    return status
        except Exception as e:
            self.save_page(traceback.format_exc())
            print(e)

    def click_payment_btn(self):
        logger.info('click Payments')
        fulfillment_link = self.driver.find_element_by_xpath(
            '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Payments")]').get_attribute(
            'href')
        self.driver.get(fulfillment_link)

    def click_date_range_reports(self):
        for _ in range(30):
            try:
                WebDriverWait(self.driver, 5, 0.5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'kat-tab-header[tab-id="DATE_RANGE_REPORTS"]')))
                script = 'document.querySelector("kat-tab-header[tab-id=DATE_RANGE_REPORTS]").click();'
                self.driver.execute_script(script)
                return True
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                return False

    def click_generate_report(self):
        for _ in range(30):
            try:
                WebDriverWait(self.driver, 5, 0.5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '#drrGenerateReportButton')))
                script = 'document.querySelector("#drrGenerateReportButton").click();'
                self.driver.execute_script(script)
                return True
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                return False

    def select_transaction(self):
        for _ in range(30):
            try:
                logger.info("select transaction")
                report_type_elem = WebDriverWait(self.driver, 5, 0.5).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="drrReportTypeRadioTransaction"]')))
                report_type_elem.click()
                return True
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                return False
            except Exception as e:
                print(e)

    def choose_date_range_reports(self):
        pass

    def generate_finance_report(self):
        for _ in range(30):
            try:
                start = WebDriverWait(self.driver, 5, 0.5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '#drrFromDate')))
                start.click()
                seven_days_ago = (datetime.utcnow().date() - timedelta(days=random.randint(2, 4))).strftime("%m/%d/%Y")
                start.send_keys(seven_days_ago)
                time.sleep(random.randint(1, 3))
                end = WebDriverWait(self.driver, 5, 0.5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '#drrToDate')))
                end.click()
                yesterday = (datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-7))) - timedelta(days=1)).strftime("%m/%d/%Y")
                end.send_keys(yesterday)
                generate_elem = WebDriverWait(self.driver, 3, 0.5).until(EC.element_to_be_clickable((By.XPATH, ('//*[@id="drrGenerateReportsGenerateButton"]//input'))))
                generate_elem.click()
                return True
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                return False

    def get_finance_transaction_report_link(self):
        for _ in range(30):
            try:
                self.driver.refresh()

                flag = False
                for i in range(20):
                    try:
                        download_button = WebDriverWait(self.driver, 5, 0.5).until(
                            EC.presence_of_element_located(
                                (By.XPATH, '//*[@id="daterangereportstable"]//table/tbody/tr[2]//a[contains(text(), "Download")]')))
                        flag = True
                        break
                    except StaleElementReferenceException:
                        pass
                    except (NoSuchElementException, TimeoutException):
                        self.driver.refresh()

                if not flag:
                    return False

                time.sleep(random.randint(4, 7))

                return download_button.get_attribute("href")
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                return False

    def get_finance_transaction_report_name(self, download_link):
        bulk_report = re.findall(r"fileName=(.*)?\.csv", download_link)[0]
        return bulk_report + '.csv'

    def download_finance_transaction_report(self, download_link):
        self.driver.get(download_link)

    def generate_finance_transaction(self):
        for _ in range(30):
            try:
                self.driver.refresh()
                flag = False
                for i in range(20):
                    try:
                        download_button = WebDriverWait(self.driver, 5, 0.5).until(
                            EC.presence_of_element_located(
                                (By.XPATH, '//*[@id="daterangereportstable"]//table/tbody/tr[2]//a[contains(text(), "Download")]')))
                        flag = True
                        break
                    except StaleElementReferenceException:
                        pass
                    except (NoSuchElementException, TimeoutException):
                        self.driver.refresh()
                if not flag:
                    return False
                logger.info('click download')
                time.sleep(random.randint(4, 7))
                download_link = download_button.get_attribute("href")
                logger.info(download_link)
                self.driver.get(download_link)
                bulk_report = re.findall(r"fileName=(.*)?\.csv", download_link)[0]
                return bulk_report + '.csv'
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                return False

    def go_to_finance_download_page(self):
        try:
            # 移动鼠标到reports

            if REFACTOR:
                status = dict()
                result = self.trigger_reports_type('Payments')
                if not result:
                    status['message'] = 'Failed to select Payments!'
                    status['status'] = False
                    return status

                result = self.click_date_range_reports()
                if not result:
                    status['message'] = 'Failed to choose date range reports!'
                    status['status'] = False
                    return status

                result = self.click_generate_report()
                if not result:
                    status['message'] = 'Failed to click generate report!'
                    status['status'] = False
                    return status

                result = self.select_transaction()
                if not result:
                    status['message'] = 'Failed to choose transaction!'
                    status['status'] = False
                    return status

                result = self.generate_finance_report()
                if not result:
                    status['message'] = 'Failed to generate finance report!'
                    status['status'] = False
                    return status

                time.sleep(random.randint(5, 10))

                finance_transaction_report_download_link = self.get_finance_transaction_report_link()
                if not finance_transaction_report_download_link:
                    status['message'] = 'Failed to generate finance transaction!'
                    status['status'] = False
                    return status

                report_name = self.get_finance_transaction_report_name(
                    finance_transaction_report_download_link)
                # TODO: Detect whether finance report exists, if it exists, delete it and download a new one
                self.remove_old_downloaded_reports(report_name)

                self.download_finance_transaction_report(finance_transaction_report_download_link)

                status['message'] = 'Download finance transaction successfully!'
                status['status'] = True
                status['report_name'] = report_name

                return status
            else:
                for i in range(0, 8):
                    click = 'false'
                    try:
                        reports = WebDriverWait(self.driver, 940, 0.5).until(
                            EC.presence_of_element_located((By.ID, 'sc-navtab-reports')))
                        time.sleep(random.randint(4, 7))
                        webdriver.ActionChains(self.driver).move_to_element(reports).perform()

                        logger.info('go to reports')
                        js_change_display = 'document.querySelector("#sc-navtab-reports > ul").style.display = "block";'
                        js_change_opacity = 'document.querySelector("#sc-navtab-reports > ul").style.opacity = 1;'
                        self.driver.execute_script(js_change_display)
                        self.driver.execute_script(js_change_opacity)
                        # click payments
                        try:
                            self.click_payment_btn()
                            break
                        except Exception as e:
                            print(e)

                    except Exception as e:
                        print(e)

                # click data range report
                
                logger.info('click data range report')
                time.sleep(random.randint(4, 7))

                # click generate report

                self.click_generate_report()
                logger.info('click data range report')
                time.sleep(random.randint(4, 7))

                # select date

                logger.info('select date')
                time.sleep(random.randint(4, 7))

                # generate
                return self.generate_finance_transaction()
            
        except Exception as e:
            self.save_page(traceback.format_exc())
            print(e)

    def click_manage_FBA_inventory(self):
        # click inventory show more
        try:
            WebDriverWait(self.driver, 5, 0.5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "li[class='level3-header show-more'] a")))
            show_more_js = '''document.querySelector("li[class='level3-header show-more'] a").click()'''
            self.driver.execute_script(show_more_js)
        except Exception as e:
            print(e)
            try:
                WebDriverWait(self.driver, 5, 0.5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '#sc-sidepanel > div > ul:nth-child(3) > li.level3-header.show-more > a'))).click()
            except Exception as e:
                print(e)
        logger.info('click inventory show more')
        time.sleep(random.randint(4, 7))

        # click Manage FBA Inventory

        fba_inv_report_js = "document.querySelector('#FBA_MYI_UNSUPPRESSED_INVENTORY a').click();"
        self.driver.execute_script(fba_inv_report_js)
        logger.info('click Manage FBA Inventory')
        time.sleep(random.randint(5, 9))

    def has_shadow_root(self):
        result = True

        try:
            WebDriverWait(self.driver, 3, 0.5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'kat-box#report-page-kat-box')))
        except (NoSuchElementException, TimeoutException) as e:
            result = False

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
    

    def get_download_btn(self):
        logger.info('begin to download fba inventory report.')
        result = None
        try:
            try:
                download_btn_elem_xpath = '//*[@id="download-page-margin-style"]/kat-table/kat-table-body/kat-table-row[1]/kat-table-cell[5]/kat-button'
                download_btn_elem = WebDriverWait(self.driver, 7, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, download_btn_elem_xpath))
                )
            except (NoSuchElementException, TimeoutException):
                download_btn_elem_xpath = '//*[@id="report-page-margin-style"]/kat-table/kat-table-body/kat-table-row[1]/kat-table-cell[5]/kat-button'
                download_btn_elem = WebDriverWait(self.driver, 7, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, download_btn_elem_xpath))
                )
            logger.info('find download element.')
            download_btn_elem = self.get_shadow_dom(download_btn_elem)
            logger.info('go into download shadow.')
            download_btn = download_btn_elem.find_element_by_css_selector(
                'button.button div.content > slot > span')
            logger.info('download button: %s' % download_btn.text.strip())
            result = download_btn
            
        except Exception as e:
            logger.info(e)
        if result:
            logger.info('report status: %s' % result.text.strip())
        return result


    def get_shadow_dom(self, shadow_host_elem):
        show_dom = self.driver.execute_script(
            'return arguments[0].shadowRoot;', shadow_host_elem)
        return show_dom


    def click_request_download_v1(self):
        result = False
        try:
            request_tsv_xpath = '//kat-box[@id="report-page-kat-box"]/kat-button[value="TSV"]/button'
            request_tsv_btn = self.driver.find_element_by_xpath(request_tsv_xpath)
            request_tsv_btn.click()
            result = True
        except Exception as e:
            print(e)
        return result
        

    def download_inventory_report(self):
        last_request_time = self.get_FBA_inventory_report_time_v1()
        result = self.click_request_download_v3()
        if result:
            result = False
            for _ in range(30):
                try:
                    time.sleep(20)
                    new_request_time = self.get_FBA_inventory_report_time_v1()
                    if new_request_time == last_request_time:
                        continue
                    else:
                        download_btn = self.get_download_btn()
                        if download_btn.text.strip() == 'Download':
                            result = True
                            logger.info('find download button.')
                            download_btn.click()
                            break
                        else:
                            continue
                    break
                except StaleElementReferenceException:
                    pass
                except (NoSuchElementException, TimeoutException):
                    break
        return result

    def find_downloaded_inventory_report(self):
        time.sleep(3)
        dir_list = list(filter(lambda x: x.endswith('.txt'), os.listdir(os.path.expanduser('~/Downloads/'))))
        dir_list = sorted(dir_list, key=lambda x: os.path.getmtime(os.path.join(os.path.expanduser('~/Downloads/'), x)))
        return dir_list[-1]


    def download_FBA_inventory(self):
        # TODO: v1
        if self.has_shadow_root():
            logger.info('inventory report version is 1.')
            result = self.download_inventory_report()
            if result:
                for _ in range(60):
                    time.sleep(0.5)
                    report_name = self.find_downloaded_inventory_report()
                    if report_name.endswith('.txt'):
                        result = report_name
                        break
            logger.info('inventory report name: %s' % result)
            return result
        else:
            fba_inventory_report_name = self.get_FBA_inventory_report_name_v1()
            self.trigger_FBA_inventory_report_download_v1()

            for i in range(3):
                report_ready = self.is_FBA_inventory_report_ready_v1()
                if not report_ready:
                    continue

                report_name = self.get_FBA_inventory_report_name_v1()
                if report_name == fba_inventory_report_name:
                    continue

                break

            fba_inventory_report_name = self.download_FBA_inventory_report_v1()

            return fba_inventory_report_name
        
    def go_to_FBA_inventory_download_page(self):
        try:
            # 移动鼠标到reports
            if REFACTOR:
                status = dict()
                result = self.trigger_reports_type('Fulfillment')

                if not result:
                    status['message'] = 'Failed to click fulfillment!'
                    status['status'] = False
                    return status

                version = self.report_type_version_check()
                select_report_by_type = getattr(self, 'select_report_by_type_%s' % version)
                result = select_report_by_type('fba_inventory')

                if not result:
                    status['message'] = 'Failed to click FBA Inventory'
                    status['status'] = False
                    return status

                result = self.download_FBA_inventory()

                if not result:
                    status['message'] = 'Failed to download FBA Inventory report'
                    status['status'] = False
                    return status
                else:
                    status['message'] = 'Download FBA Inventory report successfuly!'
                    status['status'] = True
                    status['report_name'] = result
                    return status

            else:

                for i in range(0, 3):
                    click = 'false'
                    try:
                        reports = WebDriverWait(self.driver, 940, 0.5).until(
                            EC.presence_of_element_located((By.ID, 'sc-navtab-reports')))
                        time.sleep(random.randint(4, 7))
                        webdriver.ActionChains(self.driver).move_to_element(reports).perform()
                        logger.info('go to reports')
                        js_change_display = 'document.querySelector("#sc-navtab-reports > ul").style.display = "block";'
                        js_change_opacity = 'document.querySelector("#sc-navtab-reports > ul").style.opacity = 1;'
                        self.driver.execute_script(js_change_display)
                        self.driver.execute_script(js_change_opacity)
                        # click fulfillments
                        try:
                            logger.info('click fulfillments')
                            fulfillment_link = self.driver.find_element_by_xpath(
                                '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Fulfil")]').get_attribute('href')
                            self.driver.get(fulfillment_link)
                            break
                        except Exception as e:
                            print(e)

                    except Exception as e:
                        print(e)

                self.click_manage_FBA_inventory()
                return self.download_FBA_inventory()
        except Exception as e:
            self.save_page(traceback.format_exc())
            print(e)

    def click_advertising(self):
        logger.info('click Advertising')
        advertising_link = self.driver.find_element_by_xpath(
            '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Advertising")]').get_attribute('href')
        self.driver.get(advertising_link)

    def create_advertising_report(self):
        for _ in range(30):
            try:
                create_report_elem = WebDriverWait(self.driver, 7, 0.5).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="advertising-reports"]//a[1]/button')))
                # create_report_elem.click()
                click_create_report_js = 'document.querySelector("#advertising-reports a:first-child > button").click();'
                self.driver.execute_script(click_create_report_js)
                return True
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                return False

    def choose_advertising_report_time_unit(self):
        for _ in range(30):
            try:
                click_create_report_js = 'document.querySelector("#undefined-day").click();'
                self.driver.execute_script(click_create_report_js)
                return True
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                return False

    def choose_advertised_product(self):
        for _ in range(30):
            try:
                logger.info("choose advertised product")
                report_type_btn = WebDriverWait(self.driver, 3, 0.5).until(EC.element_to_be_clickable((By.XPATH, '//div[contains(text(), "Search")]')))
                report_type_btn.click()
                advertised_elem = WebDriverWait(self.driver, 3, 0.5).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="portal"]/div/div/button[3]')))
                advertised_elem.click()
                return True
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                return False

    def choose_advertising_report_period(self):
        for _ in range(30):
            try:
                report_period_elem = WebDriverWait(self.driver, 3, 0.5).until(EC.element_to_be_clickable((By.XPATH, '')))
                report_period_elem.click()

                # select date

                # click drop down

                report_period = "document.querySelector('#cards-container table tbody tr:nth-child(4) button').click()"
                self.driver.execute_script(report_period)
                time.sleep(random.randint(4, 7))

                js = "document.querySelector('#portal > div > div > div > div > button:nth-child(%s)').click();" % random.randint(1, 5)
                logger.info(js)
                self.driver.execute_script(js)
                logger.info('click drop down')

                time.sleep(random.randint(4, 7))

                logger.info('select date')
                time.sleep(random.randint(4, 7))
            except Exception as e:
                print(e)

    def find_downloaded_report(self):
        dir_list = list(filter(lambda x: x.endswith('.xlsx'), os.listdir(os.path.expanduser('~/Downloads/'))))
        dir_list = sorted(dir_list, key=lambda x: os.path.getmtime(os.path.join(os.path.expanduser('~/Downloads/'), x)))
        return dir_list[-1]

    def click_run_advertising_report(self):
        # click run report
        time.sleep(5)
        for _ in range(10):
            try:
                click_run_report_js = 'document.querySelector("#actions span:nth-child(2) button").click();'
                self.driver.execute_script(click_run_report_js)
                return True
            except StaleElementReferenceException:
                pass
            except (NoSuchElementException, TimeoutException):
                return False
            

    def download_advertising_report(self):
        for i in range(10):
            try:
                report_status_elem = WebDriverWait(self.driver, 3, 0.5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="advertising-reports"]//p[contains(text(), "Processing") or contains(text(), "Pending")]')))
                self.driver.refresh()
            except (NoSuchElementException, TimeoutException):
                pass
            try:
                report_status_elem = WebDriverWait(self.driver, 3, 0.5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="advertising-reports"]//p[contains(text(), "Completed")]')))
                logger.info("report is ready")
                break
            except (NoSuchElementException, TimeoutException):
                pass

        js_click_download = "document.querySelector('.ReactTable .rt-tbody .rt-tr:first-child .rt-td:last-child a').click();"
        self.driver.execute_script(js_click_download)

        logger.info('click download')
        time.sleep(random.randint(4, 7))

        return self.find_downloaded_report()
        # return 'Sponsored Products Search term report.xlsx'

    def open_ads_by_link(self, marketplace):
        result = True
        ad_marketplace = {
            'us': 'amazon.com',
            'ca': 'amazon.ca'
        }
        try:
            self.driver.get('https://advertising.%s/sspa/tresah/ref=xx_perftime_dnav_xx?' % ad_marketplace[marketplace.lower()])
            time.sleep(random.randint(4, 7))
        except Exception as e:
            result = False

        return result
    def go_to_advertising_reports_download_page(self, marketplace):
        try:
            # 移动鼠标到reports
            if REFACTOR:
                status = dict()
                result = self.trigger_reports_type('Advertising')

                if not result:
                    result = self.open_ads_by_link(marketplace)

                if not result:
                    status['message'] = 'Failed to click advertising!'
                    status['status'] = False
                    return status

                result = self.create_advertising_report()

                if not result:
                    status['message'] = 'Failed to click create advertising report!'
                    status['status'] = False
                    return status

                result = self.choose_advertised_product()

                if not result:
                    status['message'] = 'Failed to choose advertised product!'
                    status['status'] = False
                    return status

                result = self.choose_advertising_report_time_unit()

                if not result:
                    status['message'] = 'Failed to choose advertising report time unit daily!'
                    status['status'] = False
                    return status

                result = self.click_run_advertising_report()

                if not result:
                    status['message'] = 'Failed to click run advertising report!'
                    status['status'] = False
                    return status

                result = self.download_advertising_report()

                if not result:
                    status['message'] = 'Failed to download advertising report!'
                    status['status'] = False
                    return status
                else:
                    status['message'] = 'Download advertising report successfuly!'
                    status['status'] = True
                    status['report_name'] = result
                    return status
            else:
                for i in range(0, 3):
                    click = 'false'
                    try:
                        reports = WebDriverWait(self.driver, 940, 0.5).until(
                            EC.presence_of_element_located((By.ID, 'sc-navtab-reports')))
                        time.sleep(random.randint(4, 7))
                        webdriver.ActionChains(self.driver).move_to_element(reports).perform()
                        logger.info('go to reports')
                        js_change_display = 'document.querySelector("#sc-navtab-reports > ul").style.display = "block";'
                        js_change_opacity = 'document.querySelector("#sc-navtab-reports > ul").style.opacity = 1;'
                        self.driver.execute_script(js_change_display)
                        self.driver.execute_script(js_change_opacity)
                        # click Advertising
                        try:
                            self.click_advertising()
                            break
                        except Exception as e:
                            print(e)

                    except Exception as e:
                        print(e)

                # create report

                logger.info("create report")
                self.create_advertising_report()
                
                time.sleep(random.randint(4, 7))
                # advertised_product_drop_down = "document.querySelector('#cards-container > div.sc-qapaw.iJULWE > div > div.sc-fzppip.dsbAWo > table > tbody > tr:nth-child(2) > td > label > button').click()"
                advertised_product_drop_down = "document.querySelector('#cards-container > div > div > div > table > tbody > tr:nth-child(2) > td > label > button > span').click()"
                self.driver.execute_script(advertised_product_drop_down)
                time.sleep(random.randint(4, 7))
                choose_advertised_product = "document.querySelector('#portal > div > div > button:nth-child(3)').click()"

                self.driver.execute_script(choose_advertised_product)
                time.sleep(random.randint(4, 7))

                # click daily
                self.click_run_advertising_report()

                logger.info('click run report')
                time.sleep(random.randint(5, 10))

                for i in range(3):
                    report_status = self.driver.find_element_by_css_selector('#advertising-reports  div> div.ReactTable > div.rt-table > div.rt-tbody > div > div > div:nth-child(1) > div > p').text
                    logger.info(report_status)
                    if report_status == "Completed":
                        logger.info("report is ready")
                        break
                    else:
                        self.driver.refresh()
                        time.sleep(random.randint(15, 20))
                js_click_download = "document.querySelector('.ReactTable .rt-tbody .rt-tr:first-child .rt-td:last-child a').click();"
                self.driver.execute_script(js_click_download)

                logger.info('click download')
                time.sleep(random.randint(4, 7))

                return self.find_downloaded_report()
                # return 'Sponsored Products Search term report.xlsx'

        except Exception as e:
            self.save_page(traceback.format_exc())
            print(e)
        
        return {'status': False, 'message': 'Unknown Error!'}

    def upload_files(self, report_type, file_path, email, password, seller_id, country, seller_profit_domain):
        if report_type == "advertising_report":
            url = seller_profit_domain + "/import_ads"
            file_type = 'ads_file'
        elif report_type == "FBA_inventory_report":
            url = seller_profit_domain + '/import_inventory'
            file_type = 'inventory_file'
        elif report_type == "finance_report":
            url = seller_profit_domain + '/import_finances'
            file_type = 'finances_file'
        elif report_type == "listings_report":
            url = seller_profit_domain + '/import_listings'
            file_type = 'listings_file'
        elif report_type == "order_report":
            url = seller_profit_domain + "/import_orders"
            file_type = "orders_file"
        elif report_type == "FBA_shipment_report":
            url = seller_profit_domain + "/import_orders"
            file_type = "order_shipments_file"
        else:
            return

        try:
            logger.info("gideon login")

            handles = self.driver.window_handles
            js = 'window.open("{seller_profit_domain}/login");'.format(seller_profit_domain=seller_profit_domain)
            self.driver.execute_script(js)

            WebDriverWait(self.driver, 7).until(EC.new_window_is_opened(handles))
            self.driver.switch_to.window(self.driver.window_handles[-1])
            try:
                email_input_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['email'])))
                email_input_elem.clear()
                email_input_elem.send_keys(email)
                logger.info("put password")
                password_input_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['password'])))
                password_input_elem.clear()
                password_input_elem.send_keys(password)
                login_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['login'])))
                login_elem.click()
            except Exception as e:
                print(e)

            time.sleep(4)

            logger.info("upload file to gideon")
            self.driver.get(url)

            if file_type == "orders_file":
                seller_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['order_seller_selector'])))
                Select(seller_elem).select_by_value(seller_id)
                file_upload = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, file_type))
                )

                logger.info("file_upload")
                file_upload.send_keys(file_path)
                time.sleep(random.randint(1, 3))

                logger.info("file import")
                WebDriverWait(self.driver, 40, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['orders_import']))).click()

            if file_type == "order_shipments_file":

                logger.info("select seller")
                seller_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['FBA_shipments_seller_selector'])))
                Select(seller_elem).select_by_value(seller_id)

                logger.info("file_upload")
                file_upload = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, file_type))
                )
                file_upload.send_keys(file_path)

                self.scroll_down()
                time.sleep(random.randint(1, 5))

                logger.info("file import")
                WebDriverWait(self.driver, 40, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['FBA_shipments_import']))).click()

            if file_type == "finances_file":

                logger.info("select seller")
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
                file_upload.send_keys(file_path)
                time.sleep(random.randint(1, 5))

                logger.info("file import")
                WebDriverWait(self.driver, 40, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['finance_import']))).click()

            if file_type == "ads_file":

                logger.info("select seller")
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
                file_upload.send_keys(file_path)
                time.sleep(random.randint(1, 5))

                logger.info("file import")
                WebDriverWait(self.driver, 40, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['ads_import']))).click()

            if file_type == "campaigns_file":

                logger.info("select seller")
                seller_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['campaigns_seller_selector'])))
                Select(seller_elem).select_by_value(seller_id)

                logger.info("select country")
                country_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['campaigns_country'])))
                Select(country_elem).select_by_value(country)

                logger.info("select report date")
                date_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['campaigns_date'])))
                date_elem.value = (datetime.utcnow().date() - timedelta(days=1)).strftime("%Y-%m-%d")
                logger.info(date_elem.value)
                time.sleep(5)
                logger.info("file_upload")
                file_upload = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, file_type))
                )
                file_upload.send_keys(file_path)
                time.sleep(random.randint(1, 5))

                logger.info("file import")
                WebDriverWait(self.driver, 40, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['campaigns_import']))).click()

            if file_type == "searchterms_file":

                logger.info("select seller")
                seller_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['searchterms_seller_selector'])))
                Select(seller_elem).select_by_value(seller_id)

                logger.info("select country")
                country_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['searchterms_country'])))
                Select(country_elem).select_by_value(country)

                logger.info("file_upload")
                file_upload = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, file_type))
                )
                file_upload.send_keys(file_path)
                time.sleep(random.randint(1, 5))

                logger.info("file import")
                self.scroll_down()
                WebDriverWait(self.driver, 40, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['searchterms_import']))).click()

            if file_type == "listings_file":

                logger.info("select seller")
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
                file_upload.send_keys(file_path)
                time.sleep(random.randint(1, 5))

                logger.info("file import")
                WebDriverWait(self.driver, 40, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['listings_import']))).click()

            if file_type == "inventory_file":
                logger.info("select seller")
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
                file_upload.send_keys(file_path)
                time.sleep(random.randint(1, 5))

                logger.info("file import")
                WebDriverWait(self.driver, 40, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['FBA_inventory_import']))).click()

            if file_type == "business_file":
                logger.info("select seller")
                seller_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['business_seller_selector'])))
                Select(seller_elem).select_by_value(seller_id)

                logger.info("select report date")
                date_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['business_date'])))
                date_elem.value = datetime.utcnow().date().strftime("%Y-%m-%d")

                logger.info("select country")
                country_elem = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['business_country'])))
                Select(country_elem).select_by_value(country)

                logger.info("file_upload")
                file_upload = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, file_type))
                )
                file_upload.send_keys(file_path)
                time.sleep(random.randint(1, 5))

                logger.info("file import")
                WebDriverWait(self.driver, 40, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['business_import']))).click()

            time.sleep(random.randint(20, 30))
            self.driver.close()
            self.driver.switch_to.window(handles[0])
            os.remove(file_path)
        except Exception as e:
            self.save_page(traceback.format_exc())
            print(e)

    def close_webdriver(self):
        if self.driver is None:
            return

        close_web_driver(self.driver)
        self.driver = None

    def remove_old_downloaded_reports(self, report_name):
        report_path = os.path.join(downloaded_report_dir, report_name)
        if os.path.isfile(report_path):
            os.remove(report_path)

    def save_page(self, ex):
        try:
            logger.info('begin to save page')
            file_name = time.strftime("%b_%d_%a_%H_%M_%S", time.localtime()) + '.html'
            current_path = os.getcwd()
            file_path = current_path + '\\logs\\' + file_name

            if not os.path.exists(current_path + '\\logs\\'):
                os.makedirs(current_path + '\\logs\\')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)

            log_path = current_path + '\\logs\\' + 'log.txt'

            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(ex)
                f.write(time.strftime("%b %d %a %H:%M:%S", time.localtime()) + '----------------------------------------------------------------' + '\n')

            logger.info('page save done')
            time.sleep(random.randint(5, 10))
        except Exception as e:
            print(e)

    def add_asin(self, asin):
        try:
            logger.info('begin to add asin')
            current_path = os.getcwd()
            file_path = current_path + '\\' + 'asin.txt'
            f = open(file_path, 'a', encoding='utf-8')
            f.write(asin + '\n')
            f.close()
            logger.info('asin' + ' ' + asin + ' ' + 'save done')
            time.sleep(random.randint(5, 10))
        except Exception as e:
            print(e)

    def check_asin(self, asin):
        try:
            current_path = os.getcwd()
            file_path = current_path + '\\' + 'asin.txt'
            f = open(file_path, 'r', encoding='utf-8')
            for asin_done in f:
                if asin == asin_done.strip():
                    logger.info('asin' + ' ' + asin + ' ' + 'is done')
                    return True
            f.close()
            logger.info('asin' + ' ' + asin + ' ' + 'is not done yet')
            return False
        except Exception as e:
            print(e)

    def clear_asin(self):
        try:
            current_path = os.getcwd()
            file_path = current_path + '\\' + 'asin.txt'
            f = open(file_path, 'r+', encoding='utf-8')
            f.truncate()
            f.close()
            self.add_asin('asin')
            logger.info('clear asins')
            return False
        except Exception as e:
            print(e)


