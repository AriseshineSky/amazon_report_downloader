# -*- coding: utf-8 -*-

import datetime

from amazon_reports_downloader.disbursements_manager import DisbursementsManager

import pytest


def test_get_disbursements(driver, disburse_payouts_urls):
  disbursements_by_marketplaces = dict()
  for marketplace, payouts_urls in disburse_payouts_urls.items():
    disbursements_by_marketplaces.setdefault(marketplace, [])
    disbursements_manager = DisbursementsManager(driver, marketplace)
    for payout_url in payouts_urls:
      driver.get(payout_url)
      disbursements = disbursements_manager.get_disbursements()
      disbursements_by_marketplaces[marketplace].append(disbursements)

  for marketplace, disbursements in disbursements_by_marketplaces.items():
    if not disbursements:
      continue

    assert {'timerange': '1/31/2023 – 2/1/2023', 'scheduled_payout_time': datetime.datetime.strptime('2/1/23 10:30 am', '%m/%d/%y %H:%M %p'), 'status': 'active', 'payout_status': 'started', 'payout_amount': 7167.26} in disbursements[0]
