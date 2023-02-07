# -*- coding: utf-8 -*-
import re
import json
import traceback
import datetime
import pdb

import dateutil
import dateutil.parser

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
  TimeoutException, NoSuchElementException, WebDriverException,
  StaleElementReferenceException)

from amazon_reports_downloader.utils import extract_balance_amount


class DisbursementsManager(object):
  def __init__(self, driver, marketplace):
    self.driver = driver
    self.marketplace = marketplace.lower()

  def get_disbursements(self):
    disbursements_xpath = '//div[contains(@class, "financial-event-group-search-results")]'
    while True:
      disbursements = []
      try:
        disbursements_elem = WebDriverWait(self.driver, 60).until(
          EC.presence_of_element_located((By.XPATH, disbursements_xpath)))
        disbursements_elems = self.driver.find_elements(By.XPATH, disbursements_xpath)
        for disbursement_elem in disbursements_elems:
          disbursement = {'status': 'active'}

          timerange_elem = disbursement_elem.find_element_by_xpath('.//div[contains(@class, "financial-event-group-metadata")]/div[@class="group-timerange"]')
          timerange_s = timerange_elem.text.strip()
          if timerange_s.find('Present') != -1:
            continue

          disbursement['timerange'] = timerange_s

          workflow_elem = disbursement_elem.find_element_by_xpath(
            './/div[contains(@class, "fund-transfer-component")]/div[@class="fund-transfer-box"]/div[contains(@class, "fund-transfer-workflow")]/kat-workflowtracker')
          workflow_s = workflow_elem.get_attribute('steps')
          if workflow_s:
            try:
              workflow = json.loads(workflow_s)
              for item in workflow:
                label_lower = item['label'].lower()
                if label_lower.find('scheduled payout') != -1:
                  scheduled_payout_time_s = label_lower.replace('scheduled payout', '').replace('\n', ' ').strip()
                  # scheduled_payout_time = datetime.datetime.strptime(scheduled_payout_time_s.upper(), '%m/%d/%y %H:%M %p')
                  scheduled_payout_time = dateutil.parser.parse(scheduled_payout_time_s)
                  disbursement['scheduled_payout_time'] = scheduled_payout_time
                  disbursement['inaccurate_payout_time'] = (scheduled_payout_time.hour == 0 and scheduled_payout_time.minute == 0 and scheduled_payout_time.second == 0)
                  break
            except ValueError:
              print(traceback.format_exc())
              self.driver.refresh()

              continue
          else:
            # Already disbursed but Amazon didn't update payout information yet
            # Just record a probobly time to keep consistent
            disbursement['scheduled_payout_time'] = (datetime.datetime.now() - datetime.timedelta(minutes=20))
            disbursement['status'] = 'inactive'

          payout_status_elem = disbursement_elem.find_element_by_xpath('.//div[contains(@class, "payout-status")]/div[contains(@class, "status")]/kat-statusindicator')
          payout_status = payout_status_elem.get_attribute('label').lower()
          disbursement['payout_status'] = payout_status

          payout_amount_elem = disbursement_elem.find_element_by_xpath('.//div[contains(@class, "payout-status")]/div[contains(@class, "payout")]')
          payout_amount = payout_amount_elem.get_attribute('innerText').strip()
          disbursement['payout_amount'] = extract_balance_amount(self.marketplace, payout_amount)

          disbursements.append(disbursement)

        break
      except StaleElementReferenceException:
        pass
      except (NoSuchElementException, TimeoutException) as e:
        break

    return disbursements
