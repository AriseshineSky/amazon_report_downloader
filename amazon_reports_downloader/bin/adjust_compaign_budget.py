import os
import sys

from cmutils.config_loaders import YamlConfigLoader

from amazon_reports_downloader.compaign_budget_adjuster import CampaignManager
from amazon_reports_downloader import logger

def main():
    if sys.platform.startswith('win'):
        work_dir = 'C:\\AmazonReportDownloader'
    else:
        work_dir = os.path.join(os.path.expanduser('~'), 'AmazonReportDownloader')


    if sys.platform.startswith('win'):
        config_path = os.path.join(work_dir, 'config.yml')
    else:
        config_path = os.path.join(work_dir, 'config.yml')

    if not os.path.isfile(config_path):
        logger.error('Could not find configuration file - %s', config_path)
        sys.exit(0)

    cl = YamlConfigLoader(config_path)
    config = cl.load()
    manager = CampaignManager(config)   
    manager.run()