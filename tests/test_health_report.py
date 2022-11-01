import os
import io
import csv

from amazon_reports_downloader.account_health_parser import AccountHealthReporter
from amazon_reports_downloader import drivers, get_shared_driver
import pytest

def test_account_health(driver, health_report_page):
    
    driver.get(health_report_page)
    health_reporter = AccountHealthReporter(driver)
    result = health_reporter.download_health_report('test', 'test')
    assert result
    # assert result == [{"sellerID": "test", "marketPlace": "test", "asin": "B07W1D2TNT", "action": "Listing removed", "reason": "Product Safety Issue", "date": "Feb 9, 2021", "impact": "EnaSkin Dark Spot Corrector Remover for Face and Body, 1 Fl Oz"}, {"sellerID": "test", "marketPlace": "test", "asin": "B07Z53XX61", "action": "Listing at risk of removal", "reason": "Product Condition Complaint - Expired", "date": "Feb 5, 2021", "impact": "Amada Pure Mole Corrector & Skin Tag Remover and Repair Lotion Set, Remove Moles and Skin Tags Easy at Home Use"}, {"sellerID": "test", "marketPlace": "test", "asin": "B07X9WRSY3", "action": "Listing removed", "reason": "Product Safety Issue", "date": "Jan 25, 2021", "impact": "Ariella Mole and Skin Tag Remover and Repair Lotion Set, Remove Moles and Skin Tags"}, {"sellerID": "test", "marketPlace": "test", "asin": "B07R69YCX4", "action": "Listing at risk of removal", "reason": "Product Condition Complaint - Expired", "date": "Dec 14, 2020", "impact": "Premium Eyelash Growth Serum and Eyebrow Enhancer by VieBeauti, Lash boost Serum for Longer, Fuller Thicker Lashes & Brows (3ML)"}, {"sellerID": "test", "marketPlace": "test", "asin": "B07WXMK62W", "action": "Listing removed", "reason": "Restricted Products Policy Violation", "date": "Oct 3, 2020", "impact": "PULCHRIE Lightening Serum with Kojic Acid, Fullerene and Arbutin, Dark Spot Corrector Remover Serum, Anti Wrinkle Reducer, Circle, Fine Line & Sun Damage Corrector,Skin Lightener for Face and Body"}]