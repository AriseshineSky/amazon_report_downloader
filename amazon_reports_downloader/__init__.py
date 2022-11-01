import os
import sys
from sys import platform
import logging
import csv
import sentry_sdk
import datetime
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver

import chromedriver_autoinstaller

from amazon_reports_downloader.signals import (
    get_shipping_fee_failure,
    pick_marketplace_failure,
    choose_template_failure,
    change_shipping_price_failure,
    trigger_report_request_failure,
    generate_report_failure
)

DEBUG = False

chromedriver_autoinstaller.install()

MARKETPLACE_MAPPING = {
    'us': {
        'sellercentral': 'sellercentral.amazon.com',
        'domain': 'www.amazon.com'
    },
    'ca': {
        'sellercentral': 'sellercentral.amazon.com',
        'domain': 'www.amazon.ca'
    },
    'mx': {
        'sellercentral': 'sellercentral.amazon.com',
        'domain': 'www.amazon.com.mx'
    },
    'uk': {
        'sellercentral': 'sellercentral.amazon.co.uk',
        'domain': 'www.amazon.co.uk'
    },
    'de': {
        'sellercentral': 'sellercentral.amazon.co.uk',
        'domain': 'www.amazon.de'
    },
    'fr': {
        'sellercentral': 'sellercentral.amazon.co.uk',
        'domain': 'www.amazon.fr'
    },
    'it': {
        'sellercentral': 'sellercentral.amazon.co.uk',
        'domain': 'www.amazon.it'
    },
    'es': {
        'sellercentral': 'sellercentral.amazon.co.uk',
        'domain': 'www.amazon.es'
    },
    'jp': {
        'sellercentral': 'sellercentral.amazon.co.jp',
        'domain': 'www.amazon.co.jp'
    },
    'au': {
        'sellercentral': 'sellercentral.amazon.com.au',
        'domain': 'www.amazon.com.au'
    },
    'in': {
        'sellercentral': 'sellercentral.amazon.in',
        'domain': 'www.amazon.in'
    },
    'cn': {
        'sellercentral': 'mai.amazon.cn',
        'domain': 'www.amazon.cn'
    }
}

MARKETPLACE_MAPPING_V2 = {
    'us': {
        'sellercentral': 'sellercentral.amazon.com',
        'country': 'United States'
    },
    'ca': {
        'sellercentral': 'sellercentral.amazon.com',
        'country': 'Canada'
    },
    'mx': {
        'sellercentral': 'sellercentral.amazon.com',
        'country': 'Mexico'
    },
    'uk': {
        'sellercentral': 'sellercentral-europe.amazon.com',
        'country': 'United Kingdom'
    },
    'de': {
        'sellercentral': 'sellercentral-europe.amazon.com',
        'country': 'Germany'
    },
    'it': {
        'sellercentral': 'sellercentral-europe.amazon.com',
        'country': 'Italy'
    },
    'fr': {
        'sellercentral': 'sellercentral-europe.amazon.com',
        'country': 'France'
    },
    'es': {
        'sellercentral': 'sellercentral-europe.amazon.com',
        'country': 'Spain'
    },
    'jp': {
        'sellercentral': 'sellercentral.amazon.co.jp',
        'country': 'Japan'
    },
    'au': {
        'sellercentral': 'sellercentral.amazon.com.au',
        'country': 'Australia'
    },
    'in': {
        'sellercentral': 'sellercentral.amazon.in',
        'country': 'India'
    },
}

SHIPPING_TEMPLATE_MAPPING = {
    'us': 'https://sellercentral.amazon.com/sbr/ref=xx_shipset_dnav_xx#shipping_templates',
    'uk': 'https://sellercentral.amazon.co.uk/sbr/ref=xx_shipset_dnav_xx#shipping_templates'
}

CUSTOM_PAYMENTS_REPORTS_MAPPING = {
    'us': "https://sellercentral.amazon.com/payments/reports/custom/request?tbla_daterangereportstable=sort:%7B%22sortOrder%22%3A%22DESCENDING%22%7D;search:undefined;pagination:1;",
}

shared_work_directory = os.path.join(os.path.expanduser('~'), '.amazon_seller_management')
if not os.path.isdir(shared_work_directory):
    os.makedirs(shared_work_directory)

downloaded_report_dir = os.path.join(os.path.expanduser('~'), 'Downloads')


drivers = dict()


def get_shared_driver(marketplace):
    marketplace = marketplace.upper()
    if drivers.get(marketplace, None):
        return drivers.get(marketplace)
    # data_dir = os.path.join(shared_work_directory, 'data')
    data_dir = os.path.join(shared_work_directory, marketplace)
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)

    opts = Options()
    opts.add_argument('--no-proxy-server')
    # opts.add_argument('-disable-web-security')
    # opts.add_argument('-allow-running-insecure-content')
    opts.add_argument('--profile-directory={}'.format(marketplace))
    opts.add_argument('user-data-dir={}'.format(data_dir))
    opts.add_argument('--lang=en-us')
    opts.page_load_strategy  = 'normal'

    caps = opts.to_capabilities()

    options = {
        'desired_capabilities': caps,
    }
    driver = WebDriver(**options)
    now = datetime.datetime.now()
    # if DEBUG or now.hour >= 20 or now.hour < 6:
    #     driver.set_window_position(0, 0)
    # else:
    #     driver.set_window_position(1200, -900)
    driver.set_window_size(1200, 900)

    drivers[marketplace] = driver

    return driver

csv.field_size_limit(10000000)

logger = logging.getLogger('AmazonSellerManagement')
formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

REFACTOR = True

sentry_sdk.init(
    "https://233f0e157d2847b6b3e9f3ba4dcaf041@o478920.ingest.sentry.io/5522217",
    traces_sample_rate=1.0
)
