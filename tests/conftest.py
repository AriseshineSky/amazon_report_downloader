import os
import glob

import amazon_reports_downloader
from amazon_reports_downloader import drivers, get_shared_driver

import pytest

amazon_reports_downloader.DEBUG = True

@pytest.fixture(scope='module')
def driver():
    driver = get_shared_driver('Test')
    yield driver
    driver.quit()
    drivers.pop('TEST')

@pytest.fixture(scope='session')
def marketplaces():
    return ['us', 'ca', 'mx', 'uk', 'de', 'fr', 'it', 'es', 'jp', 'in', 'au', 'cn']

@pytest.fixture(scope='session')
def pages_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages')

@pytest.fixture(scope='session')
def order_shipment_url(pages_dir):
    return 'file:///' + os.path.join(pages_dir, 'order_shipment', 'FBA-Fulfillment-Report-v3.html')

@pytest.fixture(scope='session')
def order_shipment_urls(pages_dir):
    urls = []
    fulfillment_report_dir = os.path.join(pages_dir, 'order_shipment')
    for file_path in glob.glob('{}/FBA-Fulfillment-Report*.html'.format(fulfillment_report_dir)):
        urls.append('file:///' + file_path)

    return urls

@pytest.fixture(scope='session')
def fba_inventory_urls(pages_dir):
    urls = []
    inventory_report_dir = os.path.join(pages_dir, 'inventory_report')
    for file_path in glob.glob('{}/FBA-inventory*.html'.format(inventory_report_dir)):
        urls.append('file:///' + file_path)

    return urls

@pytest.fixture(scope='session')
def trigger_report_type_urls(pages_dir):
    urls = []
    fulfillment_report_dir = os.path.join(pages_dir, 'order_shipment')
    for file_path in glob.glob('{}/FBA-Fulfillment-Report*.html'.format(fulfillment_report_dir)):
        urls.append('file:///' + file_path)

    return urls

@pytest.fixture(scope='session')
def order_report_record_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages', 'order_report')

@pytest.fixture(scope='session')
def listing_report_pathes(pages_dir):
    listing_report_dir = os.path.join(
        pages_dir, 'listing_report')
    return glob.glob('{}/listing_report*.txt'.format(listing_report_dir))

@pytest.fixture(scope='session')
def health_report_page(pages_dir):
    account_health_report_dir = os.path.join(pages_dir, 'account_health')
    return 'file:///' + '{}/account_health.html'.format(account_health_report_dir)

@pytest.fixture(scope='session')
def ds_skus():
    return [
        'NRockecacd19-Nov27-G0000001', 'NRockecacd19-Nov27-G0000007', 'NRockecacd19-Nov27-G0000009',
        'NRockecacd19-Nov27-G0000014', 'NRockecacd19-Nov27-G0000015',
        'JGGJVGBOOK-0212-c000016', 'JGGJVGBOOK-0212-c000018', 'JGGJVGBOOK-0212-c000015',
        'JGGJVGBOOK-0212-c000014', 'JGGJVGBOOK-0212-c000011', 'JGGJVGBOOK-0212-c000010',
        'JGGJVGBOOK-0212-c000009', 'JGGJVGBOOK-0212-c000008', 'JGGJVGBOOK-0212-c000005',
        'JGGJVGBOOK-0212-c000002'
    ]

@pytest.fixture(scope='session')
def pl_skus():
    return ['0I-DXAG-P854', '1G-0MHG-TCAE', 'HR-AUHS-U0ZO', 'MR-ZJFN-NAH2', 'NE-BODC-H3L5']

@pytest.fixture(scope='session')
def disburse_pages_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages', 'disburse')

@pytest.fixture(scope='session')
def disburse_payments_urls(disburse_pages_dir, marketplaces):
    urls = dict()
    for marketplace in marketplaces:
        marketplace_dir = os.path.join(disburse_pages_dir, marketplace)
        if not os.path.isdir(marketplace_dir):
            continue

        payments_pathes = glob.glob('{}/payments*.*html'.format(marketplace_dir))
        urls[marketplace] = ['file://' + payments_path for payments_path in payments_pathes]

    return urls

@pytest.fixture(scope='session')
def disburse_transfer_urls(disburse_pages_dir, marketplaces):
    urls = dict()
    for marketplace in marketplaces:
        marketplace_dir = os.path.join(disburse_pages_dir, marketplace)
        if not os.path.isdir(marketplace_dir):
            continue

        transfer_pathes = glob.glob('{}/transfer*.*html'.format(marketplace_dir))
        urls[marketplace] = ['file://' + transfer_path for transfer_path in transfer_pathes]

    return urls

@pytest.fixture(scope='session')
def transfer_alert_url(disburse_pages_dir):
    return 'file://' + os.path.join(disburse_pages_dir, 'fr', 'transfer_uneligible.html')

@pytest.fixture(scope='session')
def target_exchange_rates():
    return {
        'us': [None],
        'uk': [1.07416, 1.33566, None],
        'fr': [1.07416, None],
        'de': [1.07416, None],
        'ca': [0.703931, None],
        'jp': [0.00915293, None],
    }


@pytest.fixture(scope='session')
def target_transfer_amounts():
    return {
        'us': [28.75, 28.75, 929.45],
        'fr': [0],
        'ca': [153.77, 153.77],
        'de': [1340.81]
    }

@pytest.fixture(scope='session')
def target_transfer_availabilities():
    return {
        'us': {'available': 2, 'unavailable': 1},
        'fr': {'available': 0, 'unavailable': 1},
        'ca': {'available': 1, 'unavailable': 1},
        'de': {'available': 1, 'unavailable': 1}
    }

@pytest.fixture(scope='session')
def target_transfer_statuses():
    return {
        'us': {'success': 1},
        'uk': {'success': 0},
        'fr': {'success': 0},
        'ca': {'success': 1},
        'de': {'success': 1},
        'jp': {'success': 0},
    }

@pytest.fixture(scope='session')
def target_payments(disburse_pages_dir):
    return {
        'us': [
            # {
            #     'url': 'file://' + os.path.join(disburse_pages_dir, 'us', 'payments_209us.mhtml'),
            #     'instant_transfer_balance': 0,
            #     'total_balance': 80569.80,
            #     'unavailable_balance': 31553.29,
            #     'disburse_available': True,
            #     'has_disburse_button': True,
            #     'disburse_button_disabled': True
            # },
            # {
            #     'url': 'file://' + os.path.join(disburse_pages_dir, 'us', 'payments_209us_daily_new.mhtml'),
            #     'instant_transfer_balance': 446.88,
            #     'total_balance': 15306.37,
            #     'unavailable_balance': 7058.18,
            #     'disburse_available': True,
            #     'has_disburse_button': True,
            #     'disburse_button_disabled': False
            # },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'us', 'payments_235us.html'),
                'instant_transfer_balance': 12.14,
                'total_balance': 18317.09,
                'unavailable_balance': 13396.23,
                'disburse_available': True,
                'has_disburse_button': True,
                'disburse_button_disabled': False
            },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'us', 'payments_245us.html'),
                'instant_transfer_balance': 81.60,
                'total_balance': 232.45,
                'unavailable_balance': 150.85,
                'disburse_available': True,
                'has_disburse_button': True,
                'disburse_button_disabled': False
            },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'us', 'payments_251us.html'),
                'instant_transfer_balance': 0,
                'total_balance': 12859.86,
                'unavailable_balance': 7328.50,
                'disburse_available': True,
                'has_disburse_button': True,
                'disburse_button_disabled': False
            },
            # {
            #     'url': 'file://' + os.path.join(disburse_pages_dir, 'us', 'payments_256us.mhtml'),
            #     'instant_transfer_balance': 0,
            #     'total_balance': 13394.37,
            #     'unavailable_balance': 6680.43,
            #     'disburse_available': True,
            #     'has_disburse_button': True,
            #     'disburse_button_disabled': True
            # },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'us', 'payments_no_need_transfer.html'),
                'instant_transfer_balance': None,
                'total_balance': 1654.16,
                'unavailable_balance': 1654.16,
                'disburse_available': False,
                'has_disburse_button': False,
                'disburse_button_disabled': None
            },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'us', 'payments_none_daily.html'),
                'instant_transfer_balance': 28.75,
                'total_balance': 41809.67,
                'unavailable_balance': 20259.87,
                'disburse_available': True,
                'has_disburse_button': True,
                'disburse_button_disabled': False
            },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'us', 'payments_none_daily_after_transfer.html'),
                'instant_transfer_balance': 28.75,
                'total_balance': 41809.67,
                'unavailable_balance': 41780.92,
                'disburse_available': True,
                'has_disburse_button': True,
                'disburse_button_disabled': False
            }
        ],
        'ca': [
            # {
            #     'url': 'file://' + os.path.join(disburse_pages_dir, 'ca', 'payments_105ca_daily_new.mhtml'),
            #     'instant_transfer_balance': 0,
            #     'total_balance': 25353.50,
            #     'unavailable_balance': 17142.62,
            #     'disburse_available': True,
            #     'has_disburse_button': True,
            #     'disburse_button_disabled': True
            # },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'ca', 'payments_none_daily.html'),
                'instant_transfer_balance': 153.77,
                'total_balance': 3515.72,
                'unavailable_balance': 1008.84,
                'disburse_available': True,
                'has_disburse_button': True,
                'disburse_button_disabled': False
            },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'ca', 'payments_none_daily_after_transfer.html'),
                'instant_transfer_balance': 153.77,
                'total_balance': 3515.72,
                'unavailable_balance': 3361.95,
                'disburse_available': True,
                'has_disburse_button': True,
                'disburse_button_disabled': False
            }
        ],
        'uk': [
            # {
            #     'url': 'file://' + os.path.join(disburse_pages_dir, 'uk', 'payments_105uk_daily_new.mhtml'),
            #     'instant_transfer_balance': 0,
            #     'total_balance': 4936.47,
            #     'unavailable_balance': 4936.47,
            #     'disburse_available': True,
            #     'has_disburse_button': True,
            #     'disburse_button_disabled': True
            # },
            # {
            #     'url': 'file://' + os.path.join(disburse_pages_dir, 'uk', 'payments_215uk_new.mhtml'),
            #     'instant_transfer_balance': -0.02,
            #     'total_balance': -0.02,
            #     'unavailable_balance': 0,
            #     'disburse_available': True,
            #     'has_disburse_button': True,
            #     'disburse_button_disabled': False
            # },
            # {
            #     'url': 'file://' + os.path.join(disburse_pages_dir, 'uk', 'payments_247uk.mhtml'),
            #     'instant_transfer_balance': 6.15,
            #     'total_balance': 4530.92,
            #     'unavailable_balance': 2562.48,
            #     'disburse_available': True,
            #     'has_disburse_button': True,
            #     'disburse_button_disabled': False
            # },
        ],
        'de': [
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'de', 'payments_233de.html'),
                'instant_transfer_balance': 1340.81,
                'total_balance': 25034.34,
                'unavailable_balance': 11360.44,
                'disburse_available': True,
                'has_disburse_button': True,
                'disburse_button_disabled': False
            },
            # {
            #     'url': 'file://' + os.path.join(disburse_pages_dir, 'de', 'payments_233de_daily_new.mhtml'),
            #     'instant_transfer_balance': 0,
            #     'total_balance': 2942.29,
            #     'unavailable_balance': 1866.29,
            #     'disburse_available': True,
            #     'has_disburse_button': True,
            #     'disburse_button_disabled': True
            # }
        ],
        'fr': [
            # {
            #     'url': 'file://' + os.path.join(disburse_pages_dir, 'fr', 'payments_248fr_daily_new.mhtml'),
            #     'instant_transfer_balance': 0,
            #     'total_balance': 7216.66,
            #     'unavailable_balance': 4735.71,
            #     'disburse_available': True,
            #     'has_disburse_button': True,
            #     'disburse_button_disabled': True
            # },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'fr', 'payments_daily.html'),
                'instant_transfer_balance': 445.76,
                'total_balance': 445.76,
                'unavailable_balance': None,
                'disburse_available': True,
                'has_disburse_button': True,
                'disburse_button_disabled': False
            },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'fr', 'payments_daily_after_transfer.html'),
                'instant_transfer_balance': 445.76,
                'total_balance': 445.76,
                'unavailable_balance': None,
                'disburse_available': True,
                'has_disburse_button': True,
                'disburse_button_disabled': False
            },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'fr', 'payments_unable_transfer.html'),
                'instant_transfer_balance': 0,
                'total_balance': 4139.86,
                'unavailable_balance': 1304.81,
                'disburse_available': True,
                'has_disburse_button': True,
                'disburse_button_disabled': False
            }
        ],
        'jp': [
            # {
            #     'url': 'file://' + os.path.join(disburse_pages_dir, 'jp', 'payments_215jp_daily_new.mhtml'),
            #     'instant_transfer_balance': 73627,
            #     'total_balance': 1050645,
            #     'unavailable_balance': 466529,
            #     'disburse_available': True,
            #     'has_disburse_button': True,
            #     'disburse_button_disabled': False
            # }
        ]
    }

@pytest.fixture(scope='session')
def target_transfers(disburse_pages_dir):
    return {
        'us': [
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'us', 'transfer.html'),
                'amount': 28.75,
                'available': True,
                'success': False,
                'has_transfer_alert': False,
                'transfer_alert': ''
            },
            # {
            #     'url': 'file://' + os.path.join(disburse_pages_dir, 'us', 'transfer_209us.mhtml'),
            #     'amount': 929.45,
            #     'available': True,
            #     'success': False,
            #     'has_transfer_alert': False,
            #     'transfer_alert': ''
            # },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'us', 'transfer_success.html'),
                'amount': 28.75,
                'available': False,
                'success': True,
                'has_transfer_alert': False,
                'transfer_alert': ''
            },
        ],
        'ca': [
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'ca', 'transfer.html'),
                'amount': 153.77,
                'available': True,
                'success': False,
                'has_transfer_alert': False,
                'transfer_alert': ''
            },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'ca', 'transfer_success.html'),
                'amount': 153.77,
                'available': False,
                'success': True,
                'has_transfer_alert': False,
                'transfer_alert': ''
            },
        ],
        'uk': [
            # {
            #     'url': 'file://' + os.path.join(disburse_pages_dir, 'uk', 'transfer_247uk.mhtml'),
            #     'amount': 6.15,
            #     'available': False,
            #     'success': False,
            #     'has_transfer_alert': True,
            #     'transfer_alert': 'This account is currently not eligible for On-Demand Disbursement.'
            # },
        ],
        'de': [
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'de', 'transfer_233de.html'),
                'amount': 1340.81,
                'available': True,
                'success': False,
                'has_transfer_alert': False,
                'transfer_alert': ''
            },
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'de', 'transfer_success_233de.html'),
                'amount': 1340.81,
                'available': False,
                'success': True,
                'has_transfer_alert': False,
                'transfer_alert': ''
            },
        ],
        'fr': [
            {
                'url': 'file://' + os.path.join(disburse_pages_dir, 'fr', 'transfer_uneligible.html'),
                'amount': 0.00,
                'available': False,
                'success': False,
                'has_transfer_alert': True,
                'transfer_alert': 'This account is not eligible for On Demand Disbursement.'
            },
        ]
    }
