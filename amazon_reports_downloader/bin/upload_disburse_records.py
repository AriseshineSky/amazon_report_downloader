import os
import sys
import logging
import logging.handlers

import click
from cmutils.config_loaders import YamlConfigLoader
from cmutils.exchange_rate import EcbExchangeRate
import gideon

from amazon_reports_downloader import logger
from amazon_reports_downloader.disburse_task import DisburseTask


@click.command()
@click.option('-c', '--config_path', help='Configuration file path.')
@click.option('-d', '--days', type=int, default=14, help="How many days disburse record should be upload.")
def upload_disburse_records(config_path, days=14):
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
    accounts_api = gideon.AccountsApi()
    accounts_api.api_client.configuration.host = domain
    accounts = accounts_api.accounts_get(seller_id=seller_id)
    if not accounts:
        logger.warning('No account has been configured to disburse!')
        return

    if len(accounts) > 1:
        logger.warning('More than 1 accounts with same SellerID - %s', seller_id)

    account = accounts[0]
    if account.status != 'Active':
        logger.warning(
            '[InactiveAccount] SellerID: %s, Code: %s, Name: %s, Status: %s',
            account.seller_id, account.code, account.name, account.status)
        return

    if not account.disburse_enabled:
        logger.warning(
            '[AccountDisbursreDisabled] SellerID: %s, Code: %s, Name: %s',
            account.seller_id, account.code, account.name)
        return

    marketplaces = account.marketplaces.split(',')
    if not marketplaces:
        logger.warning(
            '[NoMarketplace] SellerID: %s, Code: %s, Name: %s',
            account.seller_id, account.code, account.name)
        return

    min_disburse_amount = account.min_disburse_amount if account.min_disburse_amount > 0 else 500
    exchange_rate = EcbExchangeRate()
    rates = exchange_rate.get_exchange_rate('USD')
    email = config['account']['email']
    password = config['account']['password']

    for marketplace in marketplaces:
        disburse_task = DisburseTask(
            seller_id, marketplace, email, password, domain, rates, min_disburse_amount, code)
        try:
            disburse_task.upload_history_records(days)
        except Exception as e:
            logger.exception(e)


if __name__ == '__main__':
    upload_disburse_records()
