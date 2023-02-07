# -*- coding: utf-8 -*-

# Copyright © 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import datetime
import pytz

from amazon_reports_downloader.operation_recorder import OperationRecorder

import pytest


def filter_report_records(now, record_time, record, seller_id, marketplace, download_hours):
    marketplace = marketplace.upper()

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

def downloaded_report_filter(record_time, record, seller_id, marketplace, date):
        record_date_str = record_time.astimezone(tz=pytz.utc).strftime('%Y-%m-%d')
        if record_date_str != date:
            return False

        return record['seller_id'] == seller_id and record['marketplace'] == marketplace

def test_get_last_record(order_report_record_dir):
    operation_recorder = OperationRecorder()
    setattr(operation_recorder, '_records_dir', order_report_record_dir)

    seller_id = 'ANDDF0E8IRDZ5'
    report_type = 'order_report'
    marketplace = 'US'
    download_hours = [4, 11, 19]

    now = datetime.datetime(2020, 10, 21, 3)
    last_record_time, last_record = operation_recorder.get_last_record(
        report_type,
        lambda record_time, record: filter_report_records(now, record_time, record, seller_id, marketplace, download_hours))

    assert last_record_time is None
    assert last_record is None

    now = datetime.datetime(2020, 10, 22, 3)
    last_record_time, last_record = operation_recorder.get_last_record(
        report_type,
        lambda record_time, record: filter_report_records(now, record_time, record, seller_id, marketplace, download_hours))

    assert last_record_time is None
    assert last_record is None

    target_record = {
        'seller_id': seller_id,
        'marketplace': marketplace,
        'report_path': 'C:\\AmazonReportDownloader\\order_report\\US\\24038229279018557.txt',
    }
    now = datetime.datetime(2020, 10, 22, 6)
    last_record_time, last_record = operation_recorder.get_last_record(
        report_type,
        lambda record_time, record: filter_report_records(now, record_time, record, seller_id, marketplace, download_hours))

    assert last_record_time is not None
    assert last_record is not None
    assert last_record == target_record

    now = datetime.datetime(2020, 10, 22, 12)
    last_record_time, last_record = operation_recorder.get_last_record(
        report_type,
        lambda record_time, record: filter_report_records(now, record_time, record, seller_id, marketplace, download_hours))

    assert last_record_time is None
    assert last_record is None

    date = '2020-10-22'
    last_record_time, last_record = operation_recorder.get_last_record(
        report_type,
        lambda record_time, record: downloaded_report_filter(record_time, record, seller_id, marketplace, date))
    target_record = {
        'seller_id': seller_id,
        'marketplace': marketplace,
        'report_path': 'C:\\AmazonReportDownloader\\order_report\\US\\24038229279018557.txt'
    }
    assert last_record == target_record

    marketplace = 'CA'
    last_record_time, last_record = operation_recorder.get_last_record(
        report_type,
        lambda record_time, record: downloaded_report_filter(record_time, record, seller_id, marketplace, date))
    target_record = {
        'seller_id': seller_id,
        'marketplace': marketplace,
        'report_path': 'C:\\AmazonReportDownloader\\order_report\\CA\\24050794717018557.txt'
    }
    assert last_record == target_record
