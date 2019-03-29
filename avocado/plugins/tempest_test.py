# -*- coding: utf-8 -*-
# Copyright: Lenovo Inc. 2016~2017
# Author: Yingfu Zhou <zhouyf6@lenovo.com>

"""
Avocado CloudTest plugin
"""

import os
import re
import sys
import time
import logging

import unittest2
import subprocess

from avocado.core import output
from avocado.core import loader
from avocado.core import exceptions
from avocado.core import test

from avocado.utils import genio
from avocado.utils import stacktrace
from avocado.utils import process
from avocado.plugins.ct_options import CloudTestOptionsProcess

from cloudtest import data_dir
from cloudtest import utils_params
from cloudtest.openstack.conf import ConfigTempest

class TempestTestLoader(loader.TestLoader):
    """
    Avocado loader plugin to load avocado-ct tests
    """

    name = 'tempest_test'

    def __init__(self, args, extra_params):
        super(TempestTestLoader, self).__init__(args, extra_params)
        self._fill_optional_args()

    def _fill_optional_args(self):
        def _add_if_not_exist(arg, value):
            if not hasattr(self.args, arg):
                setattr(self.args, arg, value)

        _add_if_not_exist('ct_type', 'all')
        _add_if_not_exist('ct_config', None)
        _add_if_not_exist('show_job_log', False)
        _add_if_not_exist('test_lister', True)
        _add_if_not_exist('tempest_run_type', None)
        _add_if_not_exist('tempest_run_mode', None)

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
        return {TempestTest: 'TEMPEST'}

    @staticmethod
    def get_decorator_mapping():
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: decorator function}
        """
        term_support = output.TermSupport()
        return {TempestTest: term_support.healthy_str}

    def _find_tempest_tests(self):
        tempest_test_suite = []
        try:
            from tempest.test_discover import test_discover
        except Exception:
            return tempest_test_suite

        test_loader = unittest2.loader.TestLoader()
        test_suite = test_discover.load_tests(test_loader, None, None)
        for script in test_suite:
            for klass in script:
                try:
                    for case in klass:
                        full_case_name = case.id().split('[')[0]
                        tempest_test_suite.append(full_case_name)
                except Exception:
                    pass
        return tempest_test_suite

    def _find_integrate_tests(self, parser):
        # Get test_suite
        tempest_test_suite = self._find_tempest_tests()

        def _add_case_to_suite(case, params):
            params['id'] = case
            params['name'] = case
            test_parameters = {'name': case,
                               'ct_params': params}
            avocado_test_suite.append((TempestTest,
                                       test_parameters))

        avocado_test_suite = []
        for params in (_ for _ in parser.get_dicts()):
            if 'integrate' not in params.get('ct_type'):
                continue
            tempest_run_type = params.get('tempest_run_type')
            if tempest_run_type in 'full':
                _add_case_to_suite('tempest', params)
                return avocado_test_suite
            if tempest_run_type in 'smoke':
                _add_case_to_suite('tempest_smoke', params)
                return avocado_test_suite

            for case in tempest_test_suite:
                case_name_prefix = '.'.join(case.split('.')[:1])

                if tempest_run_type in 'module':
                    case = '.'.join(case.split('.')[:-3])
                if tempest_run_type in 'suite':
                    case = '.'.join(case.split('.')[:-2])
                if tempest_run_type in 'class':
                    case = '.'.join(case.split('.')[:-1])

                # if case_name_prefix in params.get('test_types').split(' '):
                if case_name_prefix in 'tempest':
                    if params.get('tests') not in 'all':
                        # User specified cases list
                        specified_cases = params.get('tests').split(' ')
                        if case in specified_cases:
                            _add_case_to_suite(case, params)
                    else:
                        _add_case_to_suite(case, params)

        return avocado_test_suite

    def discover(self, url, which_tests=loader.DEFAULT):
        try:
            cartesian_parser = self._get_parser()
        except Exception, details:
            raise EnvironmentError(details)

        all_tests = []
        all_tests.extend(self._find_integrate_tests(cartesian_parser))

        if url is not None:
            avocado_suite = []
            for klass, test_params in all_tests:
                if url in test_params.get('name'):
                    avocado_suite.append((klass, test_params))
            return avocado_suite
        elif which_tests is loader.DEFAULT:
            # By default don't run anythinig unless vt_config provided
            return []
        return all_tests


class TempestTest(test.Test):
    """
    Main test class used to run a cloud test.
    """

    def __init__(self, methodName='runTest', name=None, params=None,
                 base_logdir=None, job=None, runner_queue=None,
                 ct_params=None):
        """
        :note: methodName, name, base_logdir, job and runner_queue params
               are inherited from test.Test
        :param params: avocado/multiplexer params stored as
                       `self.avocado_params`.
        :param ct_params:
        avocado-TempestTest/cartesian_config params stored as
                          `self.params`.
        """
        self.bindir = data_dir.get_root_dir()

        self.iteration = 0
        self.resultsdir = None
        self.file_handler = None
        self.whiteboard = None
        self.casename = name
        super(TempestTest, self).__init__(methodName=methodName, name=name,
                                          params=params,
                                          base_logdir=base_logdir, job=job,
                                          runner_queue=runner_queue)
        self.tmpdir = os.path.dirname(self.workdir)
        # Move self.params to self.avocado_params and initialize TempestTest
        # (cartesian_config) params
        self.avocado_params = self.params
        self.params = utils_params.Params(ct_params)

        self.resultsdir = self.logdir
        self.reportsdir = os.path.join(self.logdir, 'tempest.log')
        self.timeout = ct_params.get("test_timeout", self.timeout)
        # utils_misc.set_log_file_dir(self.logdir)

    @property
    def datadir(self):
        """
        Returns the path to the directory that contains test data files

        For TempestTest tests, this always returns None. The reason is that
        individual TempestTest tests do not map 1:1 to a file and do
        not provide
        the concept of a datadir.
        """
        return None

    @property
    def filename(self):
        """
        Returns the name of the file (path) that holds the current test

        For TempestTest tests, this always returns None. The reason is that
        individual TempestTest tests do not map 1:1 to a file.
        """
        return None

    def _run_avocado(self):
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
        elif self._Test__log_warn_used:
            raise exceptions.TestWarn("Test passed but there were warnings "
                                      "during execution. Check the log for "
                                      "details.")

        self.status = 'PASS'
        self.sysinfo_logger.end_test_hook()

    def get_state(self):
        """
        Avocado-TempestTest replaces Test.params with avocado-ct params.
        This function reports the original params on `get_state` call.
        """
        state = super(TempestTest, self).get_state()
        state["params"] = self.__dict__.get("avocado_params")
        return state

    def _start_logging(self):
        super(TempestTest, self)._start_logging()
        root_logger = logging.getLogger()
        root_logger.addHandler(self.file_handler)

    def _stop_logging(self):
        super(TempestTest, self)._stop_logging()
        root_logger = logging.getLogger()
        root_logger.removeHandler(self.file_handler)

    def write_test_keyval(self, d):
        self.whiteboard = str(d)

    def __safe_env_save(self, env):
        """
        Treat "env.save()" exception as warnings

        :param env: The TempestTest env object
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
            self.log.info("    %s = %s", key, params[key])

        if params.get('prepare_resource').lower() == 'true':
            self.log.info("Start to prepare resource for tempest...")
            resource_util = ConfigTempest(params)
            resource_util.set_resources()
            resource_util.prepare_tempest_log()
            resource_util.prepare_images_tempest()
            resource_util.gen_tempest_conf()
            self.log.info("Prepare resource for tempest done...")

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
                    test_name = self.params.get("id")
                    smoke_str = "\\[.*\\bsmoke\\b.*\\]"
                    self.log.info("Try to run tempest test: %s" % test_name)
                    cloudtest_dir = os.environ.get("CLOUDTEST_SOURCEDIR")
                    tempest_dir = os.path.join(cloudtest_dir, 'dependencies',
                                               'Tempest', 'tempest')
                    self.log.info("Try to change to tempest dir: %s" %
                                  tempest_dir)
                    os.chdir(tempest_dir)
                    process.run("testr init", ignore_status=True, shell=True)
                    process.run(cmd="find . -name '*.pyc' -delete",
                                ignore_status=True, shell=True)

                    cmd = "testr run --subunit"
                    if test_name != 'tempest' and \
                                    test_name != 'tempest_smoke':
                        # Run module, suite, class or single case
                        cmd += ' %s' % self.name.name

                    if self.params.get('tempest_run_type') in 'smoke':
                        cmd += ' %s' % smoke_str

                    if params.get('tempest_run_mode') == 'parallel':
                        cmd += ' --parallel'

                    self.log.info('Try to run command: %s' % cmd)
                    proc = subprocess.Popen(cmd, shell=True,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
                    proc2 = subprocess.Popen('subunit-trace -n -f',
                                             stdin=proc.stdout,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE,
                                             shell=True)
                    test_timeout = params.get('tempest_test_timeout', 1200)
                    end_time = time.time() + int(test_timeout)
                    while time.time() < end_time:
                        line = proc2.stdout.readline()
                        if line.strip() != '':
                            self.log.info("[Tempest run] %s" % line)
                        if line == '' and proc2.poll() is not None:
                            break
                    else:
                        raise exceptions.TestError("Tempest test timed out"
                                                   " after %s seconds"
                                                   % test_timeout)

                    # Rerun failed case when needed
                    if params.get('auto_rerun_on_failure', 'false') == 'true':
                        curr_rerun = 0
                        try:
                            failed_case_file_path = \
                                os.path.join(self.logdir, "failed_cases.list")

                            failed_case_file = open(failed_case_file_path,
                                                    'w')
                        except IOError:
                            raise exceptions.TestError(
                                "Failed to create blank "
                                "failed_cases.list file")
                        while curr_rerun < int(
                                params.get('auto_rerun_times')):
                            curr_rerun += 1

                            cmd1 = "testr last --subunit"
                            cmd2 = "subunit-filter -s --xfail"
                            cmd2 += " --with-tag=worker-0"
                            cmd3 = "subunit-ls"
                            cmd = cmd1 + ' | ' + cmd2 + ' | ' + cmd3
                            self.log.debug("Try to get failed cases from last"
                                           " run via command: %s" % cmd)
                            proc = subprocess.Popen(cmd1, shell=True,
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.STDOUT)
                            proc1 = subprocess.Popen(cmd2, shell=True,
                                                     stdin=proc.stdout,
                                                     stdout=subprocess.PIPE,
                                                     stderr=subprocess.STDOUT)
                            proc2 = subprocess.Popen(
                                cmd3, shell=True,
                                stdin=proc1.stdout,
                                stdout=failed_case_file,
                                stderr=subprocess.STDOUT).wait()
                            self.log.info("Start to #%d round of rerun..." %
                                          curr_rerun)
                            cmd_rerun = "testr run --load-list=%s" % \
                                        failed_case_file_path
                            proc3 = subprocess.Popen(cmd_rerun, shell=True,
                                                     stdout=subprocess.PIPE,
                                                     stderr=subprocess.STDOUT)
                            while True:
                                line = proc3.stdout.readline()
                                if line.strip() != '':
                                    self.log.info("[Tempest rerun #%d] %s" % (
                                        curr_rerun, line))
                                if line == '' and proc3.poll() is not None:
                                    break

                except Exception:
                    # try:
                    #     env_process.postprocess_on_error(self, params, env)
                    # finally:
                    #     self.__safe_env_save(env)
                    self.log.debug("Exception happened during running test")
                    raise

            finally:
                # Postprocess
                try:
                    # Generate HTML report of tempest
                    latest_id = 0
                    testrepository_path = os.path.join(tempest_dir,
                                                       '.testrepository')
                    for _, _, files in os.walk(testrepository_path):
                        for stream_file in files:
                            try:
                                last_stream = int(stream_file)
                            except (TypeError, ValueError):
                                last_stream = 0
                            latest_id = max(latest_id, last_stream)
                    self.log.info("The last result stream id: %d" % latest_id)

                    cmd_gen_html = "subunit2html %s/%d %s" % (
                        testrepository_path,
                        latest_id,
                        os.path.join(self.job.logdir, 'tempest_result.html'))
                    self.log.info("Try to generate HTML report for tempest...")
                    process.run(cmd_gen_html, shell=True, ignore_status=False)

                    # Analyze test result
                    result = process.run(
                        'testr last --subunit | subunit-stats',
                        shell=True, ignore_status=False).stdout
                    self.log.info("Tempest result:\n%s" % result)
                    total_num = re.findall('Total tests:.*(\d+)', result)[0]
                    passed_num = re.findall('Passed tests:.*(\d+)', result)[0]
                    skipped_num = \
                        re.findall('Skipped tests:.*(\d+)', result)[0]
                    if int(total_num) != int(passed_num) + int(skipped_num):
                        raise exceptions.TestFail("Tempest result failed")

                    try:
                        params['test_passed'] = str(test_passed)
                        # env_process.postprocess(self, params, env)
                    except Exception, e:
                        if test_passed:
                            raise
                        self.log.error("Exception raised during "
                                       "postprocessing: %s", e)
                finally:
                    pass
                    # if self.__safe_env_save(env):
                    #     env.destroy()   # Force-clean as it can't be stored

        except Exception, e:
            if params.get("abort_on_error") != "yes":
                raise
            # Abort on error
            self.log.info("Aborting job (%s)", e)

        return test_passed
