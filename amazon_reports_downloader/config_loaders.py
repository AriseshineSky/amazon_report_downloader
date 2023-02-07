# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os
import io
try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

import yaml


class ConfigLoader(object):
    def load(self):
        raise NotImplementedError()


class IniConfigLoader(ConfigParser):
    def __init__(self, config_path):
        self.config_path = os.path.abspath(os.path.expanduser(config_path))

        if not os.path.isfile(self.config_path):
            raise ValueError('Could not find configuration file - {}'.format(config_path))

    def load(self):
        config = dict()
        cp = ConfigParser()
        cp.read(self.config_path)
        for section in cp.sections():
            config[section] = dict()
            for opt, val in cp.items(section):
                config[section][opt] = val

        return config


class YamlConfigLoader(ConfigLoader):
    def __init__(self, config_path):
        self._config_path = os.path.abspath(os.path.expanduser(config_path))

        if not os.path.isfile(self._config_path):
            raise ValueError('Could not find configuration file - {}'.format(config_path))

    def load(self):
        cfg = None
        with io.open(self._config_path, encoding='utf-8', errors='ignore') as fh:
            cfg = yaml.load(fh.read(), Loader=yaml.SafeLoader)

        return cfg
