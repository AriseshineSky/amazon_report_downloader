# -*- coding: utf-8 -*-

# Copyright :copyright: 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from setuptools import setup, find_packages
from os import path
import io

here = path.abspath(path.dirname(__file__))

try:
    with io.open(path.join(here, 'README.md'), encoding='utf-8', errors='ignore') as f:
        long_description = f.read()
except:
    long_description = ''

with open(path.join(here, 'amazon_reports_downloader', 'VERSION'), 'rb') as f:
    version = f.read().decode('ascii').strip()

with open(path.join(here, 'requirements.txt')) as f:
    requirements = []
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            requirements.append(line)

setup(
    name='amazon_reports_downloader',
    version=version,
    description='Amazon seller reports downloader.',
    long_description=long_description,
    url='https://bitbucket.org/ousfrd/amazon_report_downloader.git',
    author='Jia Zhao',
    author_email='befruitful12@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities'
    ],
    keywords='amazon seller management',
    packages=find_packages(exclude=('tests')),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            # 'deal_collector=amazon_reports_downloader.bin.deal_collector:deal_collector',
            # 'performance_notification=amazon_reports_downloader.bin.performance_notification:performance_notification',
            # 'account_health=amazon_reports_downloader.bin.account_health:account_health',
            # 'download_report=amazon_reports_downloader.bin.download_report:download_report',
            # 'download_report_v2=amazon_reports_downloader.bin.download_report_v2:download_report',
            # 'campaign_budget_adjuster=amazon_reports_downloader.bin.adjust_compaign_budget:main',
            'disburse=amazon_reports_downloader.bin.disburse:disburse',
            # 'upload_disburse_records=amazon_reports_downloader.bin.upload_disburse_records:upload_disburse_records',
        ]
    }
)
