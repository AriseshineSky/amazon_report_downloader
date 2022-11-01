import time
import traceback

from gspread import WorksheetNotFound, CellNotFound
from gspread.exceptions import APIError
from oauth2client.client import OAuth2Credentials
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service_provider import GoogleServiceProvider
import gspread


class SheetAPI(object):
    TMM_EMAIL = 'newkbsky@gmail.com'
    SERVICE_TYPE = 'sheets'
    service = None

    def __init__(self):
        service_provider = GoogleServiceProvider()
        credentials = service_provider.get_creds(self.TMM_EMAIL, self.SERVICE_TYPE)
        credentials = OAuth2Credentials(None, credentials.client_id, credentials.client_secret, credentials.refresh_token, None,
                                        credentials.token_uri, "")
        self.service = gspread.authorize(credentials)

    def get_worksheet(self, spreadsheet_id, sheet_name):
        try:
            return self.service.open_by_key(spreadsheet_id).worksheet(sheet_name)
        except APIError as e:
            print(e.message)
            if "Quota exceeded" in e.message:
                time.sleep(30)
                return self.get_worksheet(spreadsheet_id, sheet_name)

            raise APIError(e)

    def create_new_sheet_if_not_existed(self, spreadsheet_id, sheet_name, template_name='template'):
        # check if existed
        gc = self.service.open_by_key(spreadsheet_id)
        try:
            worksheet = gc.worksheet(sheet_name)
            print('sheet %s already existed' % sheet_name)
            return worksheet
        except APIError as e:
            print(e.message)
            time.sleep(30)
            return self.create_new_sheet_if_not_existed(spreadsheet_id, sheet_name, template_name=template_name)
        except WorksheetNotFound as e:
            print('sheet %s not existed, will try to create' % sheet_name)

        try:
            template_worksheet = gc.worksheet(template_name)
        except WorksheetNotFound as e:
            raise Exception('Template sheet %s not found' % template_name)

        return template_worksheet.duplicate(new_sheet_name=sheet_name)

    def row_values(self, worksheet, row, value_render_option='FORMATTED_VALUE'):
        tried = 0
        while True:
            tried = tried + 1
            try:
                return worksheet.row_values(row, value_render_option=value_render_option)
            except APIError as e:
                if "Quota exceeded" in e.message:
                    time.sleep(30)
                    continue
            except CellNotFound as e:
                return None

            if tried >= 3:
                return None

    def col_values(self, worksheet, col, value_render_option='FORMATTED_VALUE'):
        tried = 0
        while True:
            tried = tried + 1
            try:
                return worksheet.col_values(col, value_render_option=value_render_option)
            except APIError as e:
                if "Quota exceeded" in e.message:
                    time.sleep(30)
                    continue
            except CellNotFound as e:
                return None

            if tried >= 3:
                return None

    def find_by_key(self, worksheet, key):
        tried = 0
        while True:
            tried = tried + 1
            try:
                cell = worksheet.find(key)
                return cell
            except APIError as e:
                if "Quota exceeded" in e.message:
                    time.sleep(30)
                    continue
            except CellNotFound as e:
                return None

            if tried >= 3:
                return None

    @staticmethod
    def update_cell(worksheet, row, col, value):
        while True:
            try:
                worksheet.update_cell(row, col, value)
                return
            except  Exception as e:
                time.sleep(30)
                pass

    @staticmethod
    def append_row(worksheet, values, value_input_option='RAW', table_range=None):
        while True:
            try:
                worksheet.append_row(values, table_range=table_range, value_input_option=value_input_option)
                return
            except:
                print(traceback.format_exc())
                time.sleep(30)
                pass

    # Quota exceeded for quota group
    def append_or_insert_row(self, worksheet, key, data=None, update_ignores=None, insertOnly=False):
        if update_ignores is None:
            update_ignores = []
        if data is None:
            data = {}

        cell = self.find_by_key(worksheet, key)
        if cell is None:
            row_data = list(data.values())
            self.append_row(worksheet, row_data, table_range='A1:BB1')
            return
        if insertOnly:
            return
        for col, value in data.items():
            if col in update_ignores:
                continue
            self.update_cell(worksheet, cell.row, col + 1, value)


if __name__ == '__main__':
    sheet_api = SheetAPI()
    spreadsheet_id = "1b8wHMP05Na4ELcyP5Jn9syb9g6uMc8FkBTsckOCIz7w"
    # print sheet_api.get_spreadsheet(spreadsheet_id)
    # rint SheetAPI.get_service().open_by_key(spreadsheet_id)
    sheet_api.create_new_sheet_if_not_existed(spreadsheet_id, sheet_name='03/01')
