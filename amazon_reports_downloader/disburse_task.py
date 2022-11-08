import datetime
import time
import pytz
from amazon_reports_downloader.currency_mapping import CurrencyMapping

from amazon_reports_downloader import (
    logger, get_shared_driver, MARKETPLACE_MAPPING, DEBUG
)
from amazon_reports_downloader.helpers import SellerLoginHelper
from amazon_reports_downloader.operation_recorder import OperationRecorder
from amazon_reports_downloader.payments_manager import PaymentsManager
from amazon_reports_downloader.transfer_manager import TransferManager

from amazon_reports_downloader.utils import close_web_driver
from amazon_reports_downloader.lib.google.sheet_api import SheetAPI
sheet_api = SheetAPI()
chicagoTz = pytz.timezone("America/Chicago") 
class DisburseTask():
    def __init__(self, seller_id, marketplace, email, password, seller_profit_domain,
        rates, min_disburse_amount, code=None):
        self.code = code
        self.seller_id = seller_id
        self.marketplace = marketplace
        self.email = email
        self.password = password
        self.rates = rates
        self.min_disburse_amount = min_disburse_amount
        self.operation_recorder = OperationRecorder()
        self.disburse_date_format = '%Y-%m-%d'
        self.reqest_transfer_url_template = 'https://{}/payments/dashboard/index.html'
        self.transfered_alerts = [
            "You cannot disburse more than once in a twenty-four hour period.",
            "You cannot disburse if your available balance is zero or less."
        ]

    def run(self):
        # Get last disburse record and check whether disbursed in one day
        now = datetime.datetime.now(chicagoTz)

        last_record_time, last_record = self.get_latest_disburse_record_local(
            self.seller_id, self.marketplace, self.code)

        if last_record:
            if 'disburse_date' in last_record and last_record['disburse_date']:
                try:
                    last_disburse_date = datetime.datetime.strptime(
                        last_record['disburse_date'], '%Y-%m-%dT%H:%M')
                except:
                    last_disburse_date = last_record_time
            else:
                last_disburse_date = last_record_time

            if last_disburse_date.tzinfo is None:
                LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
                last_disburse_date = last_disburse_date.replace(tzinfo=LOCAL_TIMEZONE)
        
            time_passed = now - last_disburse_date
            disbursed_in_one_day = time_passed < datetime.timedelta(days=1, minutes=15)

            disbursed_records = self.disbursed_records(self.seller_id, self.marketplace)
            is_disbursed = len(disbursed_records) > 0

            # Upload disbursed record if not uploaded to service
            if disbursed_in_one_day:
                # For compatible use only
                if 'seller_id' not in last_record:
                    last_record['seller_id'] = self.seller_id

                logger.info('[AccountAlreadyDisbursed] Report existing disburse record.')

                if is_disbursed:
                    record = disbursed_records[0]
                    amount = last_record.get('amount', last_record.get('disbursed_amount', 0))
                    if record.amount != amount and amount > 0:
                        self.save_disburse(last_record)
                else:
                    self.save_disburse(last_record)

                return

        record = None
        try:
            record = self.disburse(
                self.seller_id, self.marketplace, self.email, self.password,
                self.min_disburse_amount, self.code)
        except Exception as e:
            logger.exception(e)

        if record is None:
            return

        if record.get('total_balance', 0) == 0 and \
            record.get('unavailable_balance', 0) == 0 and \
            record.get('instant_transfer_balance', 0) == 0:
            return

        logger.info('[DisburseProcessed] %s', record)

        if record['status'] == 'REQUEST_TRANSFER_UNAVAILABLE':
            self.operation_recorder.record('disburse', record)
            self.save_disburse(record)
            return

        if record['status'] in ['REQUEST_TRANSFER_FAILURE', 'TRANSFER_FAILED']:
            return

        if record['status'] in ['REQUEST_TRANSFER_DISABLED', 'ZERO_INSTANT_TRANSFER_AMOUNT', 'ALREADY_DISBURSED', 'TRANSFER_UNAVAILABLE']:
            _, last_attempt_record = self.get_latest_disburse_attempt_record_local(
                self.seller_id, self.marketplace, self.code)
            if last_attempt_record:
                self.operation_recorder.record('disburse', last_attempt_record)
                self.save_disburse(last_attempt_record)
            else:
                self.operation_recorder.record('disburse', record)
                self.save_disburse(record)

            return

        if record['status'] == 'TRANSFER_SUCCEED':
            self.operation_recorder.record('disburse_attempt', record)
            self.save_disburse(record)

    def disburse(self, seller_id, marketplace, email, password, min_disburse_amount, code=None, retry_in_visible_area=False):
        currency = CurrencyMapping.get_currency(marketplace)
        if currency is None or marketplace.lower() not in MARKETPLACE_MAPPING:
            message = '[UnsupportedMarketplace] {}'.format(marketplace)
            logger.error(message)

            raise ValueError(message)

        driver = get_shared_driver(marketplace)
        helper = SellerLoginHelper(driver, email, password, marketplace)
        try:
            if seller_id == 'A2VDUPB6EZJ7VP':
                seller_central_url = 'https://sellercentral.amazon.ca/gp/homepage.html/ref=xx_home_logo_xx'
                sc_host = 'sellercentral.amazon.ca'
            else:
                sc_host = MARKETPLACE_MAPPING.get(marketplace.lower())['sellercentral']

                seller_central_url = 'https://{}/home'.format(sc_host)
            driver.get(seller_central_url)

            rect = driver.get_window_rect()
            origin_x = rect['x']
            origin_y = rect['y']

            while helper.is_login_required():
                logger.info('Login required! Trying to login...')

                helper.login()

                wait_time = 180
                while wait_time > 0:
                    wait_time -= 1
                    logger.debug('Waiting for login...')
                    if helper.is_login_required():
                        time.sleep(1)
                    else:
                        break

                if wait_time <= 0:
                    message = '[LoginSellerCentralFailed] SellerID: {}, Marketplace: {}'.format(
                        seller_id, marketplace)
                    raise Exception(message)

                time.sleep(7)

                driver.get(seller_central_url)

            if helper.is_login_required():
                message = '[LoginSellerCentralFailed] SellerID: {}, Marketplace: {}'.format(
                    seller_id, marketplace)
                raise Exception(message)

            if DEBUG or retry_in_visible_area:
                driver.set_window_position(0, 0)
            else:
                driver.set_window_position(origin_x, origin_y)

            logger.info('begin to pick marketplace')
            helper.pick_marketplace()
            logger.info('Picked marketplace!')

            request_transfer_url = self.reqest_transfer_url_template.format(sc_host)
            driver.get(request_transfer_url)

            payments_manager = PaymentsManager(driver, marketplace)
            transfer_manager = TransferManager(driver)

            current_rate = payments_manager.get_exchange_rate()
            rate = round(float(1 / current_rate), 6) if current_rate else self.rates[currency]

            retries = 3
            total_balance = None
            while retries > 0:
                try:
                    total_balance = payments_manager.get_total_balance()
                except Exception as e:
                    logger.exception(e)

                if total_balance is not None:
                    break

                retries -= 1

                driver.refresh()
                time.sleep(3)

                continue

            if total_balance is None:
                return

            try:
                unavailable_balance = payments_manager.get_unavailable_balance()
            except:
                unavailable_balance = None

                message = 'Could not extract unavailable balance!'
                logger.info(
                    'Could not extract total balance - SellerID: %s, Marketplace: %s',
                    seller_id, marketplace)

            if unavailable_balance is None:
                unavailable_balance = 0

            total_balance_in_usd = round(total_balance / rate, 2)
            if unavailable_balance:
                unavailable_balance_in_usd = round(unavailable_balance / rate, 2)
            else:
                unavailable_balance_in_usd = 0
            disburse_date = datetime.datetime.now(chicagoTz)
            disburse_date_str = disburse_date.strftime('%Y-%m-%dT%H:%M:%S%z')
            record = {
                'seller_id': seller_id,
                'account_code': code,
                'marketplace': marketplace,
                'disburse_date': disburse_date_str,
                'total_balance': total_balance_in_usd,
                'unavailable_balance': unavailable_balance_in_usd,
                'request_transfer_available': True
            }

            instant_transfer_balance = payments_manager.get_instant_transfer_balance()
            if instant_transfer_balance:
                record['instant_transfer_balance'] = instant_transfer_balance
            else:
                instant_transfer_balance = 0
                record['instant_transfer_balance'] = 0

            disburse_button = payments_manager.get_disburse_button()
            if disburse_button is None:
                # Handle disburse unavailable
                logger.info(
                    '[DisburseUnavailable] SellerID: %s, Marketplace: %s', seller_id, marketplace)

                record.update({
                    'status': 'REQUEST_TRANSFER_UNAVAILABLE',
                    'amount': 0,
                    'disbursed': True,
                    'request_transfer_available': False,
                    'message': 'Request transfer button is not found!'
                })

                return record
            
            if instant_transfer_balance <= min_disburse_amount:
                # Instant transfer balance is 0, try again later
                logger.info(
                    '[ZeroInstantTransferBalance] SellerID: %s, Marketplace: %s',
                    seller_id, marketplace)

                record.update({
                    'status': 'ZERO_INSTANT_TRANSFER_AMOUNT',
                    'amount': 0,
                    'disbursed': True,
                    'message': 'ZeroInstantTransferBalance'
                })

                return record

            disburse_button_disabled = payments_manager.is_disburse_button_disabled(
                disburse_button)
            if disburse_button_disabled:
                logger.info(
                    '[AccountDisburseButtonDisabled] SellerID: %s, Marketplace: %s',
                    seller_id, marketplace)

                record.update({
                    'status': 'REQUEST_TRANSFER_DISABLED',
                    'amount': 0,
                    'disbursed': False,
                    'message': 'Disburse button disabled!'
                })

                return record

            

            result = payments_manager.trigger_disburse()
            if not result:
                logger.warning(
                    '[TriggerDisburseError] SellerID: %s, Marketplace: %s',
                    seller_id, marketplace)
                record.update({
                    'status': 'REQUEST_TRANSFER_FAILURE',
                    'amount': 0,
                    'disbursed': False,
                    'message': 'Request transfer failure!'
                })

                return record

            message = 'Request disbursement succeed!'

            if transfer_manager.is_transfer_available():
                transfer_amount = transfer_manager.get_transfer_amount(marketplace)
                transfer_amount_in_usd = round(transfer_amount / rate, 2)

                result = transfer_manager.trigger_transfer()
                if result and transfer_manager.is_transfer_success():
                    record.update({
                        'status': 'TRANSFER_SUCCEED',
                        'amount': transfer_amount_in_usd,
                        'disbursed': True
                    })
                else:
                    if result:
                        if transfer_manager.has_transfer_alert():
                            message = transfer_manager.get_transfer_alert()
                            already_disbursed = any(
                                [message.find(alert) != -1 for alert in self.transfered_alerts])
                            if already_disbursed:
                                logger.info(
                                    '[AlreadyDisbursed] SellerID: %s, Marketplace: %s',
                                    seller_id, marketplace)

                                record.update({
                                    'status': 'ALREADY_DISBURSED',
                                    'amount': 0,
                                    'disbursed': True,
                                    'message': 'ALREADY_DISBURSED'
                                })
                        else:
                            record.update({
                                'status': 'TRANSFER_FAILED',
                                'amount': 0,
                                'disbursed': False,
                                'message': "Unknown error. " + \
                                    "Disbursement is requested and there is no alert."
                            })
                    else:
                        record.update({
                            'status': 'TRANSFER_FAILED',
                            'amount': 0,
                            'disbursed': False,
                            'message': 'Request disbursement failed!'
                        })
            else:
                transfer_amount = 0
                record['amount'] = 0
                if transfer_manager.has_transfer_alert():
                    message = transfer_manager.get_transfer_alert()
                    already_disbursed = any(
                        [message.find(alert) != -1 for alert in self.transfered_alerts])
                    if already_disbursed:
                        logger.info(
                            '[AlreadyDisbursed] SellerID: %s, Marketplace: %s',
                            seller_id, marketplace)

                        record.update({
                            'status': 'ALREADY_DISBURSED',
                            'disbursed': True,
                            'message': 'ALREADY_DISBURSED'
                        })
                    else:
                        record.update({
                            'status': 'TRANSFER_UNAVAILABLE',
                            'disbursed': True,
                            'message': message
                        })
                else:
                    record.update({
                        'status': 'TRANSFER_UNAVAILABLE',
                        'disbursed': True,
                        'message': 'Request disbursement is unavailable!'
                    })

            transfer_manager.return_to_summary()

            return record
        finally:
            close_web_driver(driver)

    def upload_history_records(self, days=14):
        now = datetime.datetime.now(chicagoTz)
        max_time_passed = days * 24 * 3600
        disburse_records = self.operation_recorder.get_records('disburse')
        for record in disburse_records:
            if 'disburse_date' in record and record['disburse_date']:
                try:
                    disburse_date = datetime.datetime.strptime(
                        record['disburse_date'], '%Y-%m-%dT%H:%M')
                except:
                    disburse_date = record['time']
            else:
                disburse_date = record['time']

            LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
            disburse_date = disburse_date.replace(tzinfo=LOCAL_TIMEZONE)
            
            if disburse_date.tzinfo is None:
                LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
                disburse_date = disburse_date.replace(tzinfo=LOCAL_TIMEZONE)

            time_passed = (now - disburse_date).total_seconds()
            
            if time_passed > max_time_passed:
                continue

            # For compatible use only
            if 'seller_id' not in record:
                record['seller_id'] = self.seller_id

            try:
                self.save_disburse(record)
                logger.info('[HistoryDisburseRecordUploaded] %s', record)
            except Exception as e:
                logger.exception(e)

            time.sleep(1.5)

    def check_exist_in_template(self, record):
        key = record['account_code'] + '-' + record['marketplace']
        sheet_id = "1b8wHMP05Na4ELcyP5Jn9syb9g6uMc8FkBTsckOCIz7w"
        sheet_name = "template"
        worksheet = sheet_api.create_new_sheet_if_not_existed(sheet_id, sheet_name=sheet_name)
        data = {0: '%s-%s' % (record['account_code'], record['marketplace'])}
        update_ignores = [0]
        sheet_api.append_or_insert_row(worksheet, key=key, data=data, update_ignores=update_ignores, insertOnly=True)

    def save_disburse(self, record):
        amount = record.get('amount', record.get('disbursed_amount', 0))
        message = record.get('status', record.get('message', 'No message available!'))
        if not message:
            message = 'No message available!'
        formatted_disburse = {
            'seller_id': record['seller_id'],
            'marketplace': record['marketplace'],
            'amount': amount,
            'total_balance': record['total_balance'],
            'unavailable_balance': record['unavailable_balance'],
            'instant_transfer_balance': record.get('instant_transfer_balance', amount),
            'request_transfer_available': record.get('request_transfer_available', True),
            'disburse_date': record['disburse_date'],
            'message': message
        }

        result = None

        sheet_id = "1b8wHMP05Na4ELcyP5Jn9syb9g6uMc8FkBTsckOCIz7w"
        
        chicagoTz = pytz.timezone("America/Chicago") 
        sheet_name = datetime.datetime.now(chicagoTz).strftime('%m/%d')
        sheets = list()
        self.check_exist_in_template(record)
        if len(sheets) == 0:
            try:
                worksheet = sheet_api.create_new_sheet_if_not_existed(sheet_id, sheet_name=sheet_name)
                sheets.append(worksheet)
            except Exception as e:
                logger.exception(e)

        if len(sheets) > 0:
            data = {0: '%s-%s' % (record['account_code'], record['marketplace']),
                    1: record['account_code'],
                    2: record['marketplace'],
                    3: amount,
                    4: record['total_balance'],
                    5: record['unavailable_balance'],
                    6: record.get('instant_transfer_balance', amount),
                    7: record.get('request_transfer_available', True),
                    8: record['disburse_date'],
                    9: message
                    }
            key = record['account_code'] + '-' + record['marketplace']
            update_ignores = [0]
            for sheet in sheets:
                sheet_api.append_or_insert_row(sheet, key=key, data=data, update_ignores=update_ignores, insertOnly=False)

    def get_disburse_records(self, seller_id, marketplace, date=None):
        if date is None:
            date = datetime.datetime.now(chicagoTz).strftime('%Y-%m-%d')

        disburses = []
        

        return disburses

    def disbursed_records(self, seller_id, marketplace, date=None):
        return self.get_disburse_records(seller_id, marketplace, date)

    def is_disbursed(self, seller_id, marketplace, date=None):
        disburses = self.get_disburse_records(seller_id, marketplace, date)

        disburse_cnt = len(disburses)
        if disburse_cnt == 0:
            return False

        disburse_record = disburses[0]

        # If instant transfer balance equal or less than 0, retry disburse

        return disburse_record.instant_transfer_balance > 0

    def get_latest_disburse_record_local(self, seller_id, marketplace, code=None):
        return self.operation_recorder.get_last_record(
            'disburse',
            lambda record_time, record: self.is_disburse_of_account(record_time, record, seller_id, marketplace, code))

    def get_latest_disburse_attempt_record_local(self, seller_id, marketplace, code=None):
        return self.operation_recorder.get_last_record(
            'disburse_attempt',
            lambda record_time, record: self.filter_disbursed_records(record_time, record, seller_id, marketplace, code))

    def filter_disbursed_records(self, record_time, record, seller_id, marketplace, code=None):
        marketplace = marketplace.lower()

        
        now = datetime.datetime.now(chicagoTz)

        if 'disburse_date' in record and record['disburse_date']:
            try:
                disburse_date = datetime.datetime.strptime(
                    record['disburse_date'], '%Y-%m-%dT%H:%M')
            except:
                disburse_date = record_time
        else:
            disburse_date = record_time


        if disburse_date.tzinfo is None:
            LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
            disburse_date = disburse_date.replace(tzinfo=LOCAL_TIMEZONE)

        time_passed = now - disburse_date
        
        disbursed_in_one_day = time_passed < datetime.timedelta(days=1, minutes=15)

        return disbursed_in_one_day and record.get('disbursed', False) and \
            (record.get('seller_id', '') == seller_id or record.get('account_code', '') == code) and \
            record.get('marketplace', '').lower() == marketplace

    def is_disburse_of_account(self, record_time, record, seller_id, marketplace, code=None):
        marketplace = marketplace.lower()

        return record.get('disbursed', False) and \
            (record.get('seller_id', '') == seller_id or record.get('account_code', '') == code) and \
            record.get('marketplace', '').lower() == marketplace
