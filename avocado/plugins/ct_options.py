# -*- coding: utf-8 -*-
# Copyright: Lenovo Inc. 2016~2017
# Author: Yingfu Zhou <zhouyf6@lenovo.com>


import os
import logging

from avocado.core.settings import settings
from cloudtest import cartesian_config


class CloudTestOptionsProcess(object):

    """
    Pick cloud test options and parse them to get to a cartesian parser.
    """

    def __init__(self, options):
        """
        Parses options and initializes attributes.
        """
        self.options = options
        # There are a few options from the original virt-test runner
        # that don't quite make sense for avocado (avocado implements a
        # better version of the virt-test feature).
        # So let's just inject some values into options.
        self.options.ct_verbose = False
        self.options.ct_log_level = logging.DEBUG
        self.options.ct_console_level = logging.DEBUG

        # Here we'll inject values from the config file.
        # Doing this makes things configurable yet the number of options
        # is not overwhelming.
        # setup section

        # common section
        self.options.ct_data_dir = settings.get_value(
            'cloudtest.common', 'data_dir', default=None)

        self.cartesian_parser = None

    def _process_options(self):
        """
        Process the options given in the command line.
        """
        cfg = None
        # ct_type_setting = 'option --ct-type'
        # ct_config_setting = 'option --ct-config'
        # if (not self.options.ct_type) and (not self.options.ct_config):
        #     raise ValueError("No %s or %s specified" %
        #                      (ct_type_setting, ct_config_setting))

        # if self.options.ct_type:
        #     if self.options.ct_type not in SUPPORTED_TEST_TYPES:
        #         raise ValueError("Invalid %s %s. Valid values: %s. "
        #                          % (ct_type_setting,
        #                             self.options.vt_type,
        #                             " ".join(SUPPORTED_TEST_TYPES)))

        self.cartesian_parser = cartesian_config.Parser(debug=False)

        if self.options.ct_config:
            cfg = os.path.abspath(self.options.ct_config)
        else:
            cfg = os.path.join(settings.get_value('datadir.paths', 'base_dir'),
                               'config/tests.cfg')
        self.cartesian_parser.parse_file(cfg)

        if self.options.tempest_run_type:
            self.cartesian_parser.assign('tempest_run_type',
                                         self.options.tempest_run_type)
        if self.options.tempest_run_mode:
            self.cartesian_parser.assign('tempest_run_mode',
                                         self.options.tempest_run_type)
        # if self.options.rally_debug:
        #     self._process_general_options()
        # self._process_extra_params()

    def get_parser(self):
        self._process_options()
        return self.cartesian_parser
