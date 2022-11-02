# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os
import sys
import logging
import logging.handlers

import click

from amazon_reports_downloader.config_loaders import YamlConfigLoader
from amazon_reports_downloader.exchange_rate import EcbExchangeRate

from amazon_reports_downloader import logger
from amazon_reports_downloader.disburse_task import DisburseTask


@click.command()
@click.option('-c', '--config_path', help='Configuration file path.')
def disburse(config_path):
    if sys.platform.startswith('win'):
        work_dir = 'C:\\AmazonReportDownloader'
    else:
        work_dir = os.path.join(os.path.expanduser('~'), '.AmazonReportDownloader')

    log_dir = os.path.join(work_dir, 'logs')
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    log_path = os.path.join(log_dir, 'disburse.log')
    level = logging.INFO
    max_bytes = 100 * 1024 ** 2
    fh = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=5)
    fh.setLevel(level)
    formatter = logging.Formatter('%(asctime)s %(name)s [%(levelname)s]:%(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if not config_path:
        logger.error('config_path is required to run!')
        sys.exit(1)

    config_path = os.path.abspath(os.path.expanduser(config_path))
    if not os.path.isfile(config_path):
        logger.error('Could not find configuration file - %s', config_path)
        sys.exit(0)

    cl = YamlConfigLoader(config_path)
    config = cl.load()

    if 'account' not in config or not config['account']:
        logger.error('Could not find "account" configuration!')
        sys.exit(0)

    seller_id = config['account']['seller_id']
    code = config['account']['acc']
    domain = config['account']['domain']
    marketplaces = config['account']['marketplace']
    min_disburse_amount = 100
    exchange_rate = EcbExchangeRate()
    rates = exchange_rate.get_exchange_rate('USD')
    email = config['account']['email']
    password = config['account']['password']

    for marketplace in marketplaces:
        disburse_task = DisburseTask(
            seller_id, marketplace, email, password, domain, rates, min_disburse_amount, code)
        try:
            disburse_task.run()
        except Exception as e:
            logger.exception(e)


if __name__ == '__main__':
    disburse()
