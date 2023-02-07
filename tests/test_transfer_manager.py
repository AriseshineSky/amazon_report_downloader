# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from amazon_reports_downloader.transfer_manager import TransferManager

import pytest


def test_transfer_manager(driver, target_transfers):
    transfer_manager = TransferManager(driver)

    for marketplace, transfers in target_transfers.items():
        for transfer in transfers:
            driver.get(transfer['url'])

            assert transfer_manager.get_transfer_amount(marketplace) == transfer['amount']
            assert transfer_manager.is_transfer_available() == transfer['available']
            assert transfer_manager.is_transfer_success() == transfer['success']

            if transfer['available']:
                assert transfer_manager.trigger_transfer()
            else:
                assert not transfer_manager.trigger_transfer()

            assert transfer_manager.has_transfer_alert() == transfer['has_transfer_alert']

            if transfer['has_transfer_alert']:
                assert transfer_manager.get_transfer_alert().find(transfer['transfer_alert']) != -1
