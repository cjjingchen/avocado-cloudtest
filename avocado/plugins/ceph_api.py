# -*- coding: utf-8 -*-
# Copyright: Lenovo Inc. 2016~2017
# Author: Yingfu Zhou <zhouyf6@lenovo.com>

"""
Ceph REST API test plugin
"""

import os
import re
import sys
import time
import yaml
import inspect
import logging
import importlib
import threading

from avocado.core import exceptions
from avocado.core import test
from avocado.core import loader
from avocado.core import output
from avocado.core.settings import settings

from avocado.utils import genio
from avocado.utils import stacktrace
from avocado.utils import process

from cloudtest import data_dir
from cloudtest import utils_env
from cloudtest import utils_params
from cloudtest import funcatexit
from cloudtest import utils_injection

from avocado.plugins.ct_options import CloudTestOptionsProcess


def cleanup_token():
    """
    Delete the cached token file.
    """
    sds_token_file = '/tmp/sds_token'
    if os.path.exists(sds_token_file):
        os.remove(sds_token_file)


class CephApiTestLoader(loader.TestLoader):
    """
    Avocado loader plugin to load avocado-ct tests
    """

    name = 'ceph-api'

    def __init__(self, args, extra_params):
        super(CephApiTestLoader, self).__init__(args, extra_params)
        self._fill_optional_args()

    def _fill_optional_args(self):
        def _add_if_not_exist(arg, value):
            if not hasattr(self.args, arg):
                setattr(self.args, arg, value)

        _add_if_not_exist('ct_type', 'all')
        _add_if_not_exist('ct_config', None)
        _add_if_not_exist('show_job_log', False)
        _add_if_not_exist('test_lister', True)

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

        return {CephApiTest: 'CephMgmtApi'}

    @staticmethod
    def get_decorator_mapping():
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: decorator function}
        """
        term_support = output.TermSupport()
        return {CephApiTest: term_support.healthy_str}

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

            if 'ceph_management_api' in params.get('ct_type'):
                test_suite.append((CephApiTest, test_parameters))

        return test_suite


class CephApiTest(test.Test):
    """
    Main test class used to run a Rally test.
    """

    env_version = utils_env.get_env_version()

    def __init__(self, methodName='runTest', name=None, params=None,
                 base_logdir=None, job=None, runner_queue=None,
                 ct_params=None):
        """
        :note: methodName, name, base_logdir, job and runner_queue params
               are inherited from test.Test
        :param params: avocado/multiplexer params stored as
                       `self.avocado_params`.
        :param ct_params: avocado-cloudtest/cartesian_config params stored as
                          `self.params`.
        """
        self.bindir = data_dir.get_root_dir()

        self.iteration = 0
        self.outputdir = None
        self.resultsdir = None
        self.logfile = None
        self.file_handler = None
        self.whiteboard = None
        super(CephApiTest, self).__init__(methodName=methodName, name=name,
                                        params=params,
                                        base_logdir=base_logdir, job=job,
                                        runner_queue=runner_queue)
        self.tmpdir = os.path.dirname(self.workdir)
        # Move self.params to self.avocado_params and initialize cloudtest
        # (cartesian_config) params
        self.avocado_params = self.params
        self.params = utils_params.Params(ct_params)
        self.debugdir = self.logdir
        self.resultsdir = self.logdir
        self.timeout = ct_params.get("test_timeout", self.timeout)
        # utils_misc.set_log_file_dir(self.logdir)

    @property
    def datadir(self):
        """
        Returns the path to the directory that contains test data files

        For CephApiTest tests, this always returns None. The reason is that
        individual CloudTest tests do not map 1:1 to a file and do not provide
        the concept of a datadir.
        """
        return None

    @property
    def filename(self):
        """
        Returns the name of the file (path) that holds the current test

        For CephApiTest tests, this always returns None. The reason is that
        individual CloudTest tests do not map 1:1 to a file.
        """
        return None

    def get_state(self):
        """
        Avocado-cloudtest replaces Test.params with avocado-ct params.
        This function reports the original params on `get_state` call.
        """
        state = super(CephApiTest, self).get_state()
        state["params"] = self.__dict__.get("avocado_params")
        return state

    def _start_logging(self):
        super(CephApiTest, self)._start_logging()
        root_logger = logging.getLogger()
        root_logger.addHandler(self.file_handler)

    def _stop_logging(self):
        super(CephApiTest, self)._stop_logging()
        root_logger = logging.getLogger()
        root_logger.removeHandler(self.file_handler)

    def write_test_keyval(self, d):
        self.whiteboard = str(d)

    def __safe_env_save(self, env):
        """
        Treat "env.save()" exception as warnings

        :param env: The cloudtest env object
        :return: True on failure
        """
        try:
            env.save()
        except Exception as details:
            if hasattr(stacktrace, "str_unpickable_object"):
                self.log.warn("Unable to save environment: %s",
                              stacktrace.str_unpickable_object(env.data))
            else:  # TODO: Remove when 36.0 LTS is not supported
                self.log.warn("Unable to save environment: %s (%s)", details,
                              env.data)
            return True
        return False

    def runTest(self):
        env_lang = os.environ.get('LANG')
        os.environ['LANG'] = 'C'
        try:
            self._runTest()
        # This trick will give better reporting of cloud tests being executed
        # into avocado (skips, warns and errors will display correctly)
        except exceptions.TestNotFoundError, details:
            raise exceptions.TestSkipError(details)
        except exceptions.TestWarn, details:
            raise exceptions.TestWarn(details)
        except exceptions.TestError, details:
            raise exceptions.TestError(details)
        except exceptions.TestFail, details:
            raise exceptions.TestFail(details)
        except exceptions.BadRequest, details:
            raise exceptions.TestError(details)
        except exceptions.ServerFault, details:
            raise exceptions.TestError(details)
        finally:
            if env_lang:
                os.environ['LANG'] = env_lang
            else:
                del os.environ['LANG']

    def _log_detailed_cmd_info(self, result):
        """
        Log detailed command information.

        :param result: :class:`avocado.utils.process.CmdResult` instance.
        """
        self.log.info("Exit status: %s", result.exit_status)
        self.log.info("Duration: %s", result.duration)

    def _runTest(self):
        params = self.params

        # If a dependency test prior to this test has failed, let's fail
        # it right away as TestNA.
        if params.get("dependency_failed") == 'yes':
            raise exceptions.TestNotFoundError("Test dependency failed")

        # Report cloud test version
        # logging.info(version.get_pretty_version_info())
        # Report the parameters we've received and write them as keyvals
        self.log.info("Test parameters:")
        keys = params.keys()
        keys.sort()
        for key in keys:
            if key != 'test_cases':
                self.log.info("    %s = %s", key, params[key])

        self.ct_type = self.params.get('ct_type')
        test_script = self.params.get('script')
        class_name = self.params.get('class_name')
        # Import the module
        mod_name = 'cloudtest.tests.ceph_api.tests.%s.%s' % \
                (params.get('sds_mgmt_test_type'), test_script)
        test_module = importlib.import_module(mod_name)

        for _, obj in inspect.getmembers(test_module):
            if (inspect.isclass(obj) and obj.__name__ == class_name and
                    inspect.getmodule(obj) == test_module):
                test_class = obj
                break
        self.log.info("Initialize test class: %s" % class_name)

        env_filename = os.path.join(data_dir.get_tmp_dir(),
                                    params.get("env", "env"))
        env = utils_env.Env(env_filename, self.env_version)
        self.runner_queue.put({"func_at_exit": utils_env.cleanup_env,
                               "args": (env_filename, self.env_version),
                               "once": True})
        self.runner_queue.put({"func_at_exit": cleanup_token,
                               "once": True})
        comp = test_class(params, env)

        test_passed = False
        try:
            try:
                try:
                    # Preprocess
                    # try:
                    #     params = env_process.preprocess(self, params, env)
                    # finally:
                    #     self.__safe_env_save(env)

                    # Run the test function
                    self.log.info("Start to run ceph management API test")
                    try:
                        comp.setup()
                        func = getattr(comp, params.get('func_name', 'test'))
                        # fixme: To solve create monitor hang
                        if 'test_monitors' in test_script and \
                           'test_create' in params.get('func_name'):
                            t1 = threading.Thread(target=func)
                            t1.start()
                            time.sleep(20)
                        else:
                            func()
                    finally:
                        self.__safe_env_save(env)

                except Exception, e:
                    # try:
                    #     env_process.postprocess_on_error(self, params, env)
                    # finally:
                    #     self.__safe_env_save(env)
                    stacktrace.log_exc_info(sys.exc_info(),
                                            logger='avocado.test')
                    logging.debug("Exception happened during running test")
                    raise e

            finally:
                comp.teardown()
                # Postprocess
                try:
                    try:
                        params['test_passed'] = str(test_passed)
                        # env_process.postprocess(self, params, env)
                        error_message = funcatexit.run_exitfuncs(env,
                                                                 self.ct_type)
                        if error_message:
                            logging.error(error_message)
                    except Exception, e:
                        if test_passed:
                            raise
                        self.log.error("Exception raised during "
                                       "postprocessing: %s", e)

                finally:
                    if self.__safe_env_save(env):
                        env.destroy()  # Force-clean as it can't be stored

        except Exception, e:
            if params.get("abort_on_error") != "yes":
                raise
            # Abort on error
            self.log.info("Aborting job (%s)", e)
            raise exceptions.JobError("Aborted job as config specified.")

        return test_passed

    def _run_avocado(self):
        """
        Auxiliary method to run_avocado.

        We have to override this method because the avocado-ct plugin
        has to override the behavior that tests shouldn't raise
        exceptions.TestSkipError by themselves in avocado. In the old
        avocado-ct case, that rule is not in place, so we have to be
        a little more lenient for correct test status reporting.
        """
        testMethod = getattr(self, self._testMethodName)
        self._start_logging()
        self.sysinfo_logger.start_test_hook()
        test_exception = None
        cleanup_exception = None
        stdout_check_exception = None
        stderr_check_exception = None
        try:
            self.setUp()
        except exceptions.TestSkipError, details:
            stacktrace.log_exc_info(sys.exc_info(), logger='avocado.test')
            raise exceptions.TestSkipError(details)
        except Exception, details:
            stacktrace.log_exc_info(sys.exc_info(), logger='avocado.test')
            raise exceptions.TestSetupFail(details)
        try:
            testMethod()
        except Exception, details:
            stacktrace.log_exc_info(sys.exc_info(), logger='avocado.test')
            test_exception = details
        finally:
            try:
                self.tearDown()
            except Exception, details:
                stacktrace.log_exc_info(sys.exc_info(), logger='avocado.test')
                cleanup_exception = details

        whiteboard_file = os.path.join(self.logdir, 'whiteboard')
        genio.write_file(whiteboard_file, self.whiteboard)

        # pylint: disable=E0702
        if test_exception is not None:
            raise test_exception
        elif cleanup_exception is not None:
            raise exceptions.TestSetupFail(cleanup_exception)
        elif stdout_check_exception is not None:
            raise stdout_check_exception
        elif stderr_check_exception is not None:
            raise stderr_check_exception
        # elif self._Test__log_warn_used:
        #     raise exceptions.TestWarn("Test passed but there were warnings "
        #                               "during execution. Check the log for "
        #                               "details.")

        self.status = 'PASS'
        self.sysinfo_logger.end_test_hook()
