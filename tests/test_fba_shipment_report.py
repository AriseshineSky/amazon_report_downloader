import datetime

from amazon_reports_downloader.fba_shipment_report import FBAShipmentReport
from amazon_reports_downloader.inventory_manager import Download
import pytest
import pdb

def test_get_selected_date_range(driver, order_shipment_url):
    driver.get(order_shipment_url)
    shipment_report = FBAShipmentReport(driver)
    days = shipment_report.get_selected_date_range()

    assert days == 0

def test_check_shipment_status(driver, order_shipment_urls):
    for order_shipment_url in order_shipment_urls:
        driver.get(order_shipment_url)
        shipment_report = FBAShipmentReport(driver)
        
        if order_shipment_url.endswith('v1.html'):
            status = shipment_report.check_shipment_status('2020-11-17')
            assert status == True
        if order_shipment_url.endswith('v3.html'):
            status = shipment_report.check_shipment_status('2020-11-04')
            assert status == True
        if order_shipment_url.endswith('v3.html'):
            status = shipment_report.check_shipment_status('2020-11-05')
            assert status == False

