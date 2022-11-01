# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os

from amazon_reports_downloader.inventory_manager import InventoryManager, Download

import pytest


def test_get_fulfilled_shipments_version(driver, order_shipment_urls):
    inv_manager = Download(driver)
    for order_shipment_url in order_shipment_urls:
        driver.get(order_shipment_url)
        version = inv_manager.get_fulfilled_shipments_version()

        file_name, _ = os.path.splitext(order_shipment_url.split('/').pop())
        target_version = file_name.split('-').pop()

        assert version == target_version

def test_is_FBA_shipment_report_ready_v1(driver, order_shipment_urls):
    inv_manager = Download(driver)
    for order_shipment_url in order_shipment_urls:
        driver.get(order_shipment_url)

        file_name, _ = os.path.splitext(order_shipment_url.split('/').pop())
        target_version = file_name.split('-').pop()
        if target_version != 'v1':
            continue

        ready = inv_manager.is_FBA_shipment_report_ready_v1()
        assert ready

def test_is_FBA_inventory_report_ready_v1(driver, fba_inventory_urls):
    inv_manager = Download(driver)
    for fba_inventory_url in fba_inventory_urls:
        driver.get(fba_inventory_url)

        file_name, _ = os.path.splitext(fba_inventory_url.split('/').pop())
        target_version = file_name.split('-').pop()
        if target_version != 'v1':
            continue

        ready = inv_manager.is_FBA_inventory_report_ready_v1()
        assert ready

def test_get_FBA_inventory_report_name_v1(driver, fba_inventory_urls):
    inv_manager = Download(driver)
    for fba_inventory_url in fba_inventory_urls:
        driver.get(fba_inventory_url)

        file_name, _ = os.path.splitext(fba_inventory_url.split('/').pop())
        target_version = file_name.split('-').pop()
        if target_version != 'v1':
            continue

        report_name = inv_manager.get_FBA_inventory_report_name_v1()
        assert report_name == '24723730128018583.txt'
