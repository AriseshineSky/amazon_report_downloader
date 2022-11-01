# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os
import sys
import logging
import logging.handlers
import datetime
import click
from cmutils.config_loaders import YamlConfigLoader
from cmutils.exchange_rate import EcbExchangeRate
import gideon
import time
from amazon_reports_downloader.helpers import SellerLoginHelper
from amazon_reports_downloader.account_health_parser import AccountHealthReporter
from amazon_reports_downloader import logger
from amazon_reports_downloader.disburse_task import DisburseTask
from cmutils.process_checker import ProcessChecker
from amazon_reports_downloader import (
    logger, get_shared_driver, MARKETPLACE_MAPPING, DEBUG,
    downloaded_report_dir
)

@click.command()
@click.option('-c', '--config_path', help='Configuration file path.')
@click.option('-d', '--debug', is_flag=True, help='Enable debug mode.')
def account_health(config_path, debug):
    now = datetime.datetime.now()
    if now.hour % 5 != 0:
        logger.info('It is not time to scrapy the account health report!')
        sys.exit(0)
    if sys.platform.startswith('win'):
        work_dir = 'C:\\AmazonReportDownloader'
    else:
        work_dir = os.path.join(os.path.expanduser('~'), '.AmazonReportDownloader')

    log_dir = os.path.join(work_dir, 'logs')
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    log_path = os.path.join(log_dir, 'disburse.log')
    level = logging.INFO
    max_bytes = 100 * 1024 ** 2
    fh = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=5)
    fh.setLevel(level)
    formatter = logging.Formatter('%(asctime)s %(name)s [%(levelname)s]:%(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if not config_path:
        logger.error('config_path is required to run!')
        sys.exit(1)

    config_path = os.path.abspath(os.path.expanduser(config_path))
    if not os.path.isfile(config_path):
        logger.error('Could not find configuration file - %s', config_path)
        sys.exit(0)

    cl = YamlConfigLoader(config_path)
    config = cl.load()

    if 'account' not in config or not config['account']:
        logger.error('Could not find "account" configuration!')
        sys.exit(0)

    seller_id = config['account']['seller_id']
    code = config['account']['acc']
    domain = config['account']['domain']

    cur_pid = os.getpid()
    pc = ProcessChecker(work_dir)
    pids = pc.get_pids()
    pids_count = len(pids)
    if pids_count <= 0:
        pid = -1
        logger.info('No downloader instance is running!')
    elif pids_count > 1:
        logger.warning(
            'Multiple downloader instances is running, '
            'shutdown all instances and start a new one')
        for pid in pids:
            pc.kill_proc(pid)
            pc.remove_pid(pid)

        pid = -1
    else:
        pid = pids[0]

    if pid == -1:
        # Existing downloader process already killed, or no instance is running, do nothing
        pass
    elif pc.is_running(pid):
        logger.info('One downloader instance is running, Exit!')
        sys.exit(0)
    else:
        logger.warning(
            'Current downloader instance is zombie, '
            'shutdown it and start a new one')
        pc.kill_proc(pid, True)
        pc.remove_pid(pid)

    # Save new repricer process information
    pc.save_pid(os.getpid())

    try:
        report_parser = HealthReportParser(config, debug)
        report_parser.run()
    finally:
        pc.remove_pid(os.getpid())

class HealthReportParser():
    def __init__(self, config, debug):
        self.config = config
        self.debug = debug
        

    def run(self):
        for marketplace in self.config['account']['marketplace']:
            marketplace = marketplace.upper()
            marketplace_lower = marketplace.lower()
            seller_id = self.config['account']['seller_id']
            email = self.config['account']['email']
            password = self.config['account']['password']
            if marketplace_lower not in MARKETPLACE_MAPPING:
                continue

            # We don't use driver now, so just leave it blank


            try:
                driver = get_shared_driver(marketplace)
                helper = SellerLoginHelper(driver, email, password, marketplace)

                self.account_health_reporter = AccountHealthReporter(driver)
                seller_central_url = 'https://{}/home'.format(
                    MARKETPLACE_MAPPING[marketplace_lower]['sellercentral'])
                account_health_report_link = 'https://{}/performance/account/health/product-policies?t='.format(
                    MARKETPLACE_MAPPING[marketplace_lower]['sellercentral'])
                driver.get(seller_central_url)

                rect = driver.get_window_rect()
                origin_x = rect['x']
                origin_y = rect['y']

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

                    driver.get(seller_central_url)

                if helper.is_login_required():
                    message = '[LoginSellerCentralFailed] SellerID: {}, Marketplace: {}'.format(
                        seller_id, marketplace)
                    raise Exception(message)

                # if DEBUG or self.debug:
                #     driver.set_window_position(0, 0)
                # else:
                #     driver.set_window_position(origin_x, origin_y)

                logger.info('begin to pick marketplace')
                helper.pick_marketplace()
                logger.info('Picked marketplace!')

                driver.get(account_health_report_link)
                self.driver = AccountHealthReporter(driver)
                self.driver.find_report_page(seller_id, marketplace)
                self.cleanup()
            except Exception as e:
                logger.info(e)
                self.cleanup()

    def cleanup(self):
        self.driver.close_webdriver()
if __name__ == '__main__':
    account_health()
