import datetime

from amazon_reports_downloader.fba_inventory import FBAInventoryDownload
from amazon_reports_downloader.inventory_manager import Download
import pytest
import pdb

def test_check_shipment_status(driver, fba_inventory_urls):
    for fba_inventory_url in fba_inventory_urls:
        driver.get(fba_inventory_url)
        inventory_report = FBAInventoryDownload(driver)
        
        if fba_inventory_url.endswith('v1.html'):
            status = inventory_report.has_shadow_root()
            assert status == False
        # if fba_inventory_url.endswith('v3.html'):
        #     status = inventory_report.check_shipment_status('2020-11-04')
        #     assert status == True
        if fba_inventory_url.endswith('v3.html'):
            status = inventory_report.get_download_btn()
            assert status == None
            status = inventory_report.has_shadow_root()
            assert status == True
            status = inventory_report.get_FBA_inventory_report_time_v1()
            assert status == '11/26/20, 3:19 PM'
        if fba_inventory_url.endswith('v4.html'):
            status = inventory_report.get_download_btn()
            assert status.text == 'Download'
