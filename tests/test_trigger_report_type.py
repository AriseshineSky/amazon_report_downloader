# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os

from amazon_reports_downloader.inventory_manager import InventoryManager, Download


def test_get_trigger_report_type_version(driver, trigger_report_type_urls):
    report_type = Download(driver)
    for report_type_url in trigger_report_type_urls:
        driver.get(report_type_url)

        version = report_type.report_type_version_check()

        file_name, _ = os.path.splitext(report_type_url.split('-').pop())
        target_version = file_name.split('-').pop()
        if target_version == 'v3':
            target_version = 'v2'
        assert version == target_version

def test_get_trigger_report_type_version(driver, trigger_report_type_urls):
    report_type = Download(driver)
    for report_type_url in trigger_report_type_urls:
        driver.get(report_type_url)

        version = report_type.report_type_version_check()

        select_report_by_type = getattr(report_type, 'select_report_by_type_%s' % version)
        result = select_report_by_type('order')
        assert result == True