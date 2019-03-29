# -*- coding: utf-8 -*-
# Copyright: Lenovo Inc. 2016~2017
# Author: Yingfu Zhou <zhouyf6@lenovo.com>

"""
Avocado CloudTest plugin
"""

import os

from avocado.core import output
from avocado.core import loader

from avocado.core.settings import settings

from avocado.plugins.ct_options import CloudTestOptionsProcess
from avocado.plugins.tempest_test import TempestTestLoader
from avocado.plugins.rally_test import RallyTest
from avocado.plugins.healthcheck_test import HealthCheckTestLoader
from avocado.plugins.security import SecurityTestLoader
from avocado.plugins.vm_reliability_test import VMReliabilityTestLoader
from avocado.plugins.benchmarker import BechmarkerTestLoader
from avocado.plugins.shaker import ShakerTestLoader
from avocado.plugins.ceph_api import CephApiTestLoader
from avocado.plugins.nfv import NFVTestLoader

# Avocado's plugin interface module has changed location. Let's keep
# compatibility with old for at, least, a new LTS release
try:
    from avocado.core.plugin_interfaces import CLI
except ImportError:
    from avocado.plugins.base import CLI  # pylint: disable=E0611,E0401


class CloudTestRun(CLI):
    """
    Avocado CloudTest support
    """

    name = 'ct'
    description = "Avocado CloudTest support to 'run' command"

    def configure(self, parser):
        """
        Add the subparser for the run action.

        :param parser: Main test runner parser.
        """
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        ct_compat_group_tempest = run_subcommand_parser.add_argument_group(
            'Cloudtest compat layer - tempest test options')
        ct_compat_group_rally = run_subcommand_parser.add_argument_group(
            'Cloudtest compat layer - rally test options')

        ct_compat_group_rally.add_argument("--rally-debug",
                                           action="store_true",
                                           default=False,
                                           help="Enable Rally DEBUG "
                                                "logging level")
        ct_compat_group_tempest.add_argument("--tempest-run-type",
                                             action="store",
                                             default="full",
                                             help="Run type of tempest: could"
                                                  " be 'case', 'suite', "
                                                  "smoke or 'full'")
        ct_compat_group_tempest.add_argument("--tempest-run-mode",
                                             action="store",
                                             default="serial",
                                             help="Run mode of tempest: could"
                                                  " be 'serial' or 'parallel'")

    def run(self, args):
        """
        Run test modules or Cloud tests.

        :param args: Command line args received from the run subparser.
        """
        loader.loader.register_plugin(CloudTestLoader)
        loader.loader.register_plugin(TempestTestLoader)
        loader.loader.register_plugin(HealthCheckTestLoader)
        loader.loader.register_plugin(SecurityTestLoader)
        loader.loader.register_plugin(VMReliabilityTestLoader)
        loader.loader.register_plugin(BechmarkerTestLoader)
        loader.loader.register_plugin(ShakerTestLoader)
        loader.loader.register_plugin(CephApiTestLoader)
        loader.loader.register_plugin(NFVTestLoader)


class CloudTestLoader(loader.TestLoader):
    """
    Avocado loader plugin to load avocado-ct tests
    """

    name = 'ct'

    def __init__(self, args, extra_params):
        super(CloudTestLoader, self).__init__(args, extra_params)
        self._fill_optional_args()

    def _fill_optional_args(self):
        def _add_if_not_exist(arg, value):
            if not hasattr(self.args, arg):
                setattr(self.args, arg, value)

        _add_if_not_exist('ct_type', 'all')
        _add_if_not_exist('ct_config', None)
        _add_if_not_exist('show_job_log', False)
        _add_if_not_exist('test_lister', True)
        _add_if_not_exist('product_build_number', '')

    def _get_parser(self):
        options_processor = CloudTestOptionsProcess(self.args)
        return options_processor.get_parser()

    def get_extra_listing(self):
        pass

    @staticmethod
    def get_type_label_mapping():
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: 'TEST_LABEL_STRING'}
        """

        return {RallyTest: 'CLOUDTEST'}

    @staticmethod
    def get_decorator_mapping():
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: decorator function}
        """
        term_support = output.TermSupport()
        return {RallyTest: term_support.healthy_str}

    def discover(self, url, which_tests=loader.DEFAULT):
        try:
            cartesian_parser = self._get_parser()
        except Exception as details:
            raise EnvironmentError(details)

        if url is not None:
            cartesian_parser.only_filter(url)
        elif which_tests is loader.DEFAULT:
            # By default don't run anythinig unless vt_config provided
            return []
        test_suite = []
        cloud_test_path = os.path.join(settings.get_value(
            'datadir.paths', 'base_dir'), 'tests')

        for params in (_ for _ in cartesian_parser.get_dicts()):
            test_name = params.get('shortname')

            params['id'] = test_name
            path_prefix = params.get(
                '_short_name_map_file')['subtests.cfg'].split('.')[:-1]
            params['file_path'] = os.path.join(cloud_test_path,
                                               '/'.join(path_prefix) + '.yaml')
            test_parameters = {'name': test_name,
                               'ct_params': params}

            if 'performance' in params.get('ct_type') \
                    or 'stability' in params.get('ct_type'):
                test_suite.append((RallyTest, test_parameters))

        return test_suite


class CloudTestLister(CLI):
    """
    Avocado Cloud Test - implements cloud test listing
    """

    name = 'ct-list'
    description = "Avocado-cloudtest test list"

    def configure(self, parser):
        """
        Add the subparser for the run action.

        :param parser: Main test runner parser.
        """
        list_subcommand_parser = parser.subcommands.choices.get('list', None)
        if list_subcommand_parser is None:
            return

        ct_compat_group_lister = list_subcommand_parser.add_argument_group(
            'CloudTest compat layer - Lister options')
        ct_compat_group_lister.add_argument("--rally-tests",
                                            action="store_true",
                                            default=False,
                                            help="Only list Rally tests")
        ct_compat_group_lister.add_argument("--tempest-tests",
                                            action="store_true",
                                            default=False,
                                            help="Only list Tempest tests")
        ct_compat_group_lister.add_argument("--bandit-tests",
                                            action="store_true",
                                            default=False,
                                            help="Only list bandit tests")
        ct_compat_group_lister.add_argument("--tempest-run-type",
                                            action="store",
                                            default="full",
                                            help="Run type of Tempest tests,"
                                                 " could be 'case', 'suite', "
                                                 "'full', 'smoke'")
        ct_compat_group_lister.add_argument("--tempest-run-mode",
                                            action="store",
                                            default="serial",
                                            help="Run type of Tempest tests, "
                                            "could be 'serial', 'paralle'")

    def run(self, args):
        loader.loader.register_plugin(CloudTestLoader)
