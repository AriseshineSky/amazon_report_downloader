# -*- coding: utf-8 -*-

# Copyright © 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os
import io
import json
import datetime

from amazon_reports_downloader import shared_work_directory, logger


class OperationRecorder(object):
    def __init__(self):
        self._records_dir = os.path.join(shared_work_directory, 'operation_records')
        if not os.path.isdir(self._records_dir):
            os.makedirs(self._records_dir)
        self._time_format = '%Y%m%dT%H%M%S.%f'

    def record(self, operation, operation_details):
        operation_records_path = self.get_operation_records_path(operation)
        operation_time = self.format_time(datetime.datetime.now())
        with io.open(operation_records_path, 'a', encoding='utf-8', errors='ignore') as fh:
            params = dict(operation_details)
            params['time'] = operation_time
            record = json.dumps(params)
            record += '\n'
            fh.write(record)

    def get_last_record(self, operation, callback=None):
        result = (None, None)

        operation_records_path = self.get_operation_records_path(operation)
        if not os.path.isfile(operation_records_path):
            return result

        with io.open(operation_records_path, encoding='utf-8', errors='ignore') as fh:
            lines = fh.readlines()
            lines.reverse()
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except Exception as e:
                    logger.exception(e)
                    record = None

                if record is None:
                    continue

                record_time = self.deformat_time(record.pop('time'))
                if callback and callable(callback):
                    try:
                        res = callback(record_time, record)
                    except:
                        res = False
                    if res:
                        result = (record_time, record)
                        break
                else:
                    result = (record_time, record)
                    break

        return result

    def get_operation_records_path(self, operation):
        return os.path.join(self._records_dir, '{}.txt'.format(operation))

    def get_records(self, operation):
        result = []

        operation_records_path = self.get_operation_records_path(operation)
        if not os.path.isfile(operation_records_path):
            return result

        with io.open(operation_records_path, encoding='utf-8', errors='ignore') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except Exception as e:
                    logger.exception(e)
                    record = None

                if record is None:
                    continue

                record['time'] = self.deformat_time(record['time'])
                result.append(record)

        return result

    def format_time(self, t):
        return t.strftime(self._time_format)

    def deformat_time(self, t_str):
        return datetime.datetime.strptime(t_str, self._time_format)
