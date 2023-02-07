# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from amazon_reports_downloader.payments_manager import PaymentsManager

import pytest


def test_get_exchange_rate(driver, disburse_payments_urls, target_exchange_rates):
    exchange_rates = dict()
    for marketplace, payments_urls in disburse_payments_urls.items():
        payments_manager = PaymentsManager(driver, marketplace)
        exchange_rates.setdefault(marketplace, [])
        for payments_url in payments_urls:
            driver.get(payments_url)
            exchange_rate = payments_manager.get_exchange_rate()
            exchange_rates[marketplace].append(exchange_rate)

    for marketplace, exchange_rates_by_m in exchange_rates.items():
        target_exchange_rates_by_m = target_exchange_rates.get(marketplace, [])
        for exchange_rate in exchange_rates_by_m:
            assert exchange_rate in target_exchange_rates_by_m

def test_payments_manager(driver, target_payments):
    for marketplace, target_payments_by_m in target_payments.items():
        for target_payment in target_payments_by_m:
            driver.get(target_payment['url'])

            payments_manager = PaymentsManager(driver, marketplace)
            # import pdb
            # pdb.set_trace()
            instant_transfer_balance = payments_manager.get_instant_transfer_balance()
            assert instant_transfer_balance == target_payment['instant_transfer_balance']

            total_balance = payments_manager.get_total_balance()
            assert total_balance == target_payment['total_balance']

            unavailable_balance = payments_manager.get_unavailable_balance()
            assert unavailable_balance == target_payment['unavailable_balance']

            disburse_button = payments_manager.get_disburse_button()
            has_disburse_button = disburse_button is not None
            assert has_disburse_button == target_payment['has_disburse_button']

            disburse_button_disabled = payments_manager.is_disburse_button_disabled(disburse_button)
            assert disburse_button_disabled == target_payment['disburse_button_disabled']
