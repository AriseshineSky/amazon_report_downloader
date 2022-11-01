# -*- coding: utf-8 -*-

# Copyright © 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os
import sys
import time
import datetime
import click
import random
import shutil
import pytz
import logging
import logging.handlers

from amazon_reports_downloader.report_uploaders import GideonUploader
from cmutils.process_checker import ProcessChecker
from cmutils.config_loaders import YamlConfigLoader
from sentry_sdk import capture_message

from amazon_reports_downloader import (
    logger, get_shared_driver, MARKETPLACE_MAPPING, DEBUG,
    downloaded_report_dir
)
from amazon_reports_downloader.helpers import SellerLoginHelper
from amazon_reports_downloader.inventory_manager import Download
from amazon_reports_downloader.operation_recorder import OperationRecorder
from amazon_reports_downloader.listing_filter import ListingFilter


@click.command()
@click.option('-c', '--config_path', required=False, help='Configuration file path.')
@click.option('-d', '--debug', is_flag=True, help='Enable debug mode.')
def download_report(config_path, debug):
    if sys.platform.startswith('win'):
        work_dir = 'C:\\AmazonReportDownloader'
    else:
        work_dir = os.path.join(os.path.expanduser('~'), '.AmazonReportDownloader')

    log_dir = os.path.join(work_dir, 'logs')
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    log_path = os.path.join(log_dir, 'download_report.log')
    level = logging.INFO
    max_bytes = 100 * 1024 ** 2
    fh = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=5)
    fh.setLevel(level)
    formatter = logging.Formatter('%(asctime)s %(name)s [%(levelname)s]:%(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if config_path is None:
        if sys.platform.startswith('win'):
            config_path = os.path.join(work_dir, 'config.yml')
        else:
            config_path = os.path.join(work_dir, 'config.yml')
    else:
        config_path = os.path.abspath(os.path.expanduser(config_path))

    if not os.path.isfile(config_path):
        logger.error('Could not find configuration file - %s', config_path)
        sys.exit(0)

    cl = YamlConfigLoader(config_path)
    config = cl.load()

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
        report_downloader = ReportDownloader(config, debug)
        report_downloader.run()
    finally:
        pc.remove_pid(os.getpid())


class ReportDownloader():
    def __init__(self, config, debug=False):
        self.config = config
        self.debug = debug
        self.operation_recorder = OperationRecorder()
        self.listing_filter = ListingFilter()
        self.report_dir = downloaded_report_dir
        if sys.platform.startswith('win'):
            self.dst_report_dir = 'C:\\AmazonReportDownloader'
        else:
            self.dst_report_dir = os.path.join(os.path.expanduser('~'), '.AmazonReportDownloader')

        self.report_types_supported = [
            'advertising_report', 'FBA_inventory_report', 'finance_report', 'listings_report',
            'order_report', 'FBA_shipment_report', 'FBA_shipment_tax_report'
        ]

        self.uploader = None
        self.downloader = None
        message_tpl = 'Acc: {}, SellerID: {}, Domain: {}, '.format(
            config['account']['acc'], config['account']['seller_id'],
            config['account']['domain'])
        self.message_tpl = message_tpl + 'Marketplace: {}, ReportType: {}, Message: {}'

    def run(self):
        for marketplace in self.config['account']['marketplace']:
            marketplace = marketplace.upper()
            marketplace_lower = marketplace.lower()
            email = self.config['account']['email']
            password = self.config['account']['password']
            gideon_email = self.config['account']['gideon_email']
            gideon_password = self.config['account']['gideon_password']
            seller_id = self.config['account']['seller_id']
            seller_profit_domain = self.config['account']['domain']
            reports_to_download = self.config['account']['reports']

            if marketplace_lower not in MARKETPLACE_MAPPING:
                continue

            # We don't use driver now, so just leave it blank
            self.uploader = GideonUploader(
                None, seller_profit_domain, gideon_email, gideon_password)

            report_types_to_download = []
            reports_to_upload = dict()
            report_download_hour = dict()
            try:
                for report_to_download in reports_to_download:
                    if report_to_download['type'] not in self.report_types_supported:
                        logger.warning('[UnsupportedReportType] %s', report_to_download['type'])
                        continue

                    if report_to_download['type'] == 'FBA_shipment_tax_report' and marketplace.lower() != 'us' and marketplace.lower() != 'uk':
                        logger.warning('[UnsupportedReportType] %s, %s'% (report_to_download['type'], marketplace))
                        continue

                    if report_to_download['type'] == 'order_report' and marketplace.lower() != 'us' and marketplace.lower() != 'uk':
                        logger.warning('[UnsupportedReportType] %s, %s' % (report_to_download['type'], marketplace))
                        continue

                    if report_to_download['type'] == 'FBA_shipment_report' and marketplace.lower() != 'us' and marketplace.lower() != 'uk':
                        logger.warning('[UnsupportedReportType] %s, %s' % (report_to_download['type'], marketplace))
                        continue
                    report_type = report_to_download['type']
                    download_hours = report_to_download.get('download_hours', [3])
                    report_download_hour[report_type] = download_hours
                    # Use download hours to check whether report has already been downloaded
                    if self.is_report_downloaded(
                        seller_id, marketplace, report_type, download_hours):
                        # Check whether report has been uploaded to server
                        if self.uploader.is_report_uploaded(report_type, seller_id, marketplace):
                            logger.debug('[ReportAlreadyDownloaded] ReportType: %s', report_type)
                            continue

                        record = self.get_downloaded_report(report_type, seller_id, marketplace)
                        if record is None:
                            logger.warning(
                                '[GetDownloadedReportFailed] ReportType: %s, SellerID: %s, Marketplace: %s',
                                report_type, seller_id, marketplace)
                            continue

                        reports_to_upload.setdefault(report_type, [])
                        reports_to_upload[report_type].append(record)
                        continue

                    if not self.is_to_download(download_hours):
                        continue

                    report_types_to_download.append(report_type)
            except Exception as e:
                logger.exception(e)

            if not report_types_to_download and not reports_to_upload:
                continue

            try:
                driver = get_shared_driver(marketplace)
                helper = SellerLoginHelper(driver, email, password, marketplace)

                self.downloader = Download(driver)
                self.uploader.driver = driver

                for rt, records in reports_to_upload.items():
                    for record in records:
                        try:
                            self.uploader.upload_report(
                                rt, record['report_path'],
                                record['seller_id'], record['marketplace'])
                            message = '[UploadDownloadedReport] SellerID: {}, Marketplace: {}, ReportType: {}'.format(
                                record['seller_id'], record['marketplace'], rt)
                            logger.info(message)
                        except Exception as e:
                            logger.warning('[UploadReportError] %s', str(e))

                        time.sleep(3)

                seller_central_url = 'https://{}/home'.format(
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

                self.downloader.close_tooltips()

                for report_type in report_types_to_download:
                    try:
                        driver.get(seller_central_url)
                        if report_type == "advertising_report":
                            status = self.downloader.go_to_advertising_reports_download_page(marketplace)
                        elif report_type == "FBA_inventory_report":
                            status = self.downloader.go_to_FBA_inventory_download_page()
                        elif report_type == "finance_report":
                            status = self.downloader.go_to_finance_download_page()
                        elif report_type == "listings_report":
                            status = self.downloader.go_to_listings_download_page()
                        elif report_type == "order_report":
                            status = self.downloader.go_to_orders_download_page(report_download_hour.get("order_report"), marketplace.lower())
                        elif report_type == "FBA_shipment_report":
                            status = self.downloader.go_to_FBA_shipment_download_page(marketplace.lower())
                        elif report_type == "FBA_shipment_tax_report":
                            if marketplace.lower() == 'us' or marketplace.lower() == 'uk':
                                status = self.downloader.go_to_FBA_shipment_tax_download_page(marketplace.lower())
                        else:
                            status = {
                                'status': False,
                                'message': 'Unsupported Report Type - {}!'.format(report_type)
                            }

                        if status and status['status']:
                            report_name = status['report_name'] if 'report_name' in status else ''
                            logger.info('[ReportDownloaded] ReportType: %s, Report: %s', report_type, report_name)

                            retries = 12
                            downloaded_report_path = os.path.join(self.report_dir, status['report_name'])
                            while retries > 0:
                                if os.path.isfile(downloaded_report_path):
                                    break
                                retries = retries - 1
                                time.sleep(15)
                            if not os.path.isfile(downloaded_report_path):
                                continue

                            report_path = self.save_downloaded_report(
                                report_type, marketplace, status['report_name'])
                            if report_type == 'listings_report':
                                if os.stat(downloaded_report_path).st_size > 10 * 1024 * 1024:
                                    filtered_report_path = os.path.join(
                                        self.dst_report_dir, 'tmp', report_type, marketplace,
                                        datetime.datetime.today().strftime('%Y-%m-%d'),
                                        status['report_name'])
                                    self.listing_filter.filter_listing_report(downloaded_report_path, filtered_report_path)

                                    report_to_upload = filtered_report_path
                                else:
                                    report_to_upload = downloaded_report_path
                            else:
                                report_to_upload = downloaded_report_path

                            self.uploader.upload_report(report_type, report_to_upload, seller_id, marketplace)

                            record = {
                                'seller_id': seller_id,
                                'marketplace': marketplace,
                                'report_path': report_path
                            }
                            self.operation_recorder.record(report_type, record)

                            time.sleep(3)
                        else:
                            logger.warning(
                                '[ReportDownloadFailed] ReportType: %s', report_type)

                            if isinstance(status, dict) and 'message' in status:
                                message = status['message']
                            else:
                                message = 'Unknown Error.'
                            self.capture_error(report_type, marketplace, message)
                    except (SystemError, SystemExit, KeyboardInterrupt) as e:
                        raise e
                    except Exception as e:
                        logger.warning('[ReportDownloadFailed] ReportType: %s', report_type)
                        logger.exception(e)

                        self.capture_error(report_type, marketplace, str(e))
            except (SystemError, SystemExit, KeyboardInterrupt) as e:
                raise e
            except Exception as e:
                logger.exception(e)
            finally:
                self.cleanup()

    def cleanup(self):
        self.downloader.close_webdriver()

    def is_to_download(self, download_hours):
        if download_hours:
            now = datetime.datetime.now()
            to_download = now.hour >= download_hours[0]
        else:
            to_download = True

        return to_download

    def is_report_downloaded(self, seller_id, marketplace, report_type, download_hours):
        last_record_time, last_record = self.operation_recorder.get_last_record(
            report_type,
            lambda record_time, record: self.filter_report_records(record_time, record, seller_id, marketplace, download_hours))

        return last_record_time and last_record

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

    def save_downloaded_report(self, report_type, marketplace, report_file_name):
        today_str = datetime.datetime.today().strftime('%Y-%m-%d')
        downloaded_report_path = os.path.join(self.report_dir, report_file_name)
        dst_report_dir = os.path.join(self.dst_report_dir, report_type, marketplace, today_str)
        if not os.path.isdir(dst_report_dir):
            os.makedirs(dst_report_dir)
        dst_report_path = os.path.join(dst_report_dir, report_file_name)
        shutil.copy(downloaded_report_path, dst_report_path)

        return dst_report_path

    def get_downloaded_report(self, report_type, seller_id, marketplace, date=None):
        if date is None:
            date = datetime.datetime.utcnow().strftime('%Y-%m-%d')

        record_time, record = self.operation_recorder.get_last_record(
            report_type,
            lambda record_time, record: self.downloaded_report_filter(record_time, record, seller_id, marketplace, date))

        return record

    def downloaded_report_filter(self, record_time, record, seller_id, marketplace, date):
        record_date_str = record_time.astimezone(tz=pytz.utc).strftime('%Y-%m-%d')
        if record_date_str != date:
            return False

        return record['seller_id'] == seller_id and record['marketplace'] == marketplace

    def capture_error(self, report_type, marketplace, message):
        capture_message(self.message_tpl.format(marketplace, report_type, message))


if __name__ == '__main__':
    download_report()
