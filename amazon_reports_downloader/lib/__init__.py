import logging
import re
import os
import sys
from logging.handlers import RotatingFileHandler

try:
    import urllib3
    urllib3.disable_warnings()
except ImportError:
    pass

import requests

def insecure_request(method, url, **kwargs):
    with requests.sessions.Session() as session:
        kwargs['verify'] = False
        return session.request(method=method, url=url, **kwargs)

requests.api.request = insecure_request

logger = logging.getLogger('shopify.' + __name__)
formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def set_logger_handler(log_file_name):
    # logger.removeHandler(stream_handler)

    work_dir = os.path.dirname(os.path.dirname(__file__))
    logs_dir = os.path.join(work_dir, 'logs')
    if not os.path.isdir(logs_dir):
        os.makedirs(logs_dir)
    log_path = os.path.join(logs_dir, log_file_name)
    level = logging.INFO
    max_bytes = 200 * 1024 ** 2
    fh = RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=5)
    fh.setLevel(level)
    formatter = logging.Formatter('%(asctime)s %(name)s [%(levelname)s]:%(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


local_config_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config_local.ini")
if os.path.exists(local_config_file_path):
    default_file_path = local_config_file_path
else:
    default_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")

data_dir_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
if not os.path.exists(data_dir_root):
    os.mkdir(data_dir_root, 0o777)


def get_config_file_path(site):
    config_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config-%s.ini" % site.lower())
    if not os.path.exists(config_file_path):
        config_file_path = default_file_path

    return config_file_path


default_filter_cond = {
    'rating': 80,
    'feedback': 25,
    'domestic': True,
    'shipping_time': 7,
    'subcondition': 70,
    'offers': 1,
    'expire_hour': 120,
    'picked_count': 2,
    'provider_type': 'fba'
}

def has_offer(asin, offers):
    return asin in offers and offers[asin] is not False and offers[asin] is not None and offers[asin]['price'] > 0
