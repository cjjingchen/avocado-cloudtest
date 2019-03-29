# -*- coding: utf-8 -*-
# Copyright: Lenovo Inc. 2016~2017
# Author: Yingfu Zhou <zhouyf6@lenovo.com>

"""
Avocado RallyTest plugin
"""

import os
import re
import sys
import time
import yaml
import logging
from enum import Enum

from avocado.core import exceptions
from avocado.core import test
from avocado.utils import genio
from avocado.utils import stacktrace
from avocado.utils import process

from cloudtest import data_dir
from cloudtest import utils_env
from cloudtest import utils_params
from cloudtest import funcatexit
from cloudtest import utils_injection
from cloudtest.openstack.conf import ConfigStability


def _run_rally_task(task_path, deployment, rally_arg_file, logdir,
                    debug='False', print_rally_output=False, env=None):
    err_count = None
    cmd = "rally --log-dir %s " % logdir
    if debug is 'True':
        cmd += " --debug"
    cmd += " task start %s --deployment %s" % (task_path, deployment)
    cmd += " --task-args-file %s" % rally_arg_file
    result = process.run(cmd, shell=True, verbose=print_rally_output,
                         ignore_status=False)
    if result.exit_status != 0:
        logging.error("Failed to execute rally test: %s" % result.stdout)

    pat = 'rally task report (.*) --out output.html'
    task_uuid = re.findall(pat, result.stdout)[0]
    pat1 = 'Task (.*) has (\d+) error'
    res = re.findall(pat1, result.stdout)[0]
    if task_uuid not in res[0]:
        logging.error("Failed to get correct rally task uuid")
        return None, err_count
    err_count = res[1]

    result_list = _get_rally_result(task_uuid, result.stdout, env)
    raw_success = result_list['Success']
    if raw_success.find('%') == -1:
        success = raw_success
    else:
        success = raw_success[0:raw_success.find('%')]
    return task_uuid, err_count, success


def _get_rally_result(task_uuid, stdout, env=None):
    result_items = Enum('Result', ('Action', 'Min(sec)', 'Median(sec)',
                                   '90%ile(sec)', '95%ile(sec)', 'Max(sec)',
                                   'Avg(sec)', 'Success', 'Count'))
    data = None
    pat = "total (.*)|"
    info = re.findall(pat, stdout)
    for i in range(len(info)):
        if info[i] != '' and info[i] != ' ':
            data = info[i]
            break

    result_list = data.split('|')
    result_dict = {}
    i = 0
    for name in result_items.__members__.items():
        result_dict[name[0]] = result_list[i].strip()
        i += 1

    result_dict['rally_task_uuid'] = task_uuid

    env.register_rally_total_result(result_dict)

    tmp_list = env.get_rally_total_result(task_uuid)
    for key, value in tmp_list.items():
        logging.info("%s => %s" % (key, value))

    return result_dict


class RallyTest(test.Test):
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
        super(RallyTest, self).__init__(methodName=methodName, name=name,
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

        For RallyTest tests, this always returns None. The reason is that
        individual CloudTest tests do not map 1:1 to a file and do not provide
        the concept of a datadir.
        """
        return None

    @property
    def filename(self):
        """
        Returns the name of the file (path) that holds the current test

        For RallyTest tests, this always returns None. The reason is that
        individual CloudTest tests do not map 1:1 to a file.
        """
        return None

    def get_state(self):
        """
        Avocado-cloudtest replaces Test.params with avocado-ct params.
        This function reports the original params on `get_state` call.
        """
        state = super(RallyTest, self).get_state()
        state["params"] = self.__dict__.get("avocado_params")
        return state

    def _start_logging(self):
        super(RallyTest, self)._start_logging()
        root_logger = logging.getLogger()
        root_logger.addHandler(self.file_handler)

    def _stop_logging(self):
        super(RallyTest, self)._stop_logging()
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

    def _run_performance_test(self, test_params, env):
        def _get_task_path_from_name(test_params, name):
            mod = test_params.get('id').split('.')[1]
            return os.path.join(data_dir.STABILITY_TEST_DIR, '%s/%s' % (
                mod, name))

        # Run performance test, convert test name to file path and execute
        # 'rally task start ...'
        # Generate argument file for rally yaml test cases
        rally_task_args = {}
        for k, v in test_params.items():
            if 'rally_task_arg_' in k:
                rally_task_args[k[len('rally_task_arg_'):]] = v

        test_name = test_params.get('file_path')
        rally_arg_file = '/tmp/rally_task_args.yaml'
        try:
            with open(rally_arg_file, 'w') as f:
                yaml.dump(rally_task_args, f, default_flow_style=False,
                          default_style="'")
        except Exception, e:
            raise exceptions.TestError("Failed to generate rally task"
                                       " arg file: %s" % e)
        try:
            if self.ct_type == 'performance':
                os.chdir(os.path.join(data_dir.PERFORMANCE_CASE_DIR))
                self.log.info("Try to run performance test: %s" % test_name)
            if self.ct_type == 'stability':
                os.chdir(os.path.join(data_dir.STABILITY_TEST_DIR))
                self.log.info("Try to run stability test: %s" % test_name)

            dependent_tasks = []
            dependencies = test_params.get("pre_process", "")
            if dependencies:
                dependent_tasks = dependencies.split(" ")
            recoveries_on_error = test_params.get("post_process_on_error", "")
            if recoveries_on_error:
                recovery_on_error_tasks = recoveries_on_error.split(" ")

            deployment = test_params.get('deployment')
            rerun_times = int(test_params.get('rerun_times', '1'))
            matched_result = None

            # Run dependencies in dependency list
            for dep in dependent_tasks:
                task_path = _get_task_path_from_name(test_params, dep)
                curr_run = 0
                test_passed = False

                while curr_run < rerun_times:
                    curr_run += 1
                    if test_passed:
                        break
                    self.log.info("Try to run dependent task: %s (%d/%d)" %
                                  (task_path, curr_run, rerun_times))
                    _, err_count, pass_rate = _run_rally_task(task_path,
                                                   deployment,
                                                   rally_arg_file,
                                                   self.logdir,
                                                   'False',
                                                   False, env)
                    if err_count is not None:
                        test_passed = int(err_count) == 0
                    if pass_rate == 'n/a' or float(pass_rate) < \
                            float(self.params.get('rally_task_arg_success_rate')):
                        test_passed = 0

                    if not test_passed:
                        recovery_on_error_task = \
                            recovery_on_error_tasks[
                                dependent_tasks.index(dep)]
                        recovery_task_path = _get_task_path_from_name(
                            test_params, recovery_on_error_task)
                        self.log.info("Try to run recovery task: %s" %
                                      recovery_on_error_task)
                        try:
                            _run_rally_task(recovery_task_path,
                                            deployment,
                                            rally_arg_file,
                                            self.logdir,
                                            'False',
                                            False, env)
                        except Exception:
                            self.log.error("Error while running recovery"
                                           " task: %s" %
                                           recovery_on_error_task)
                        if curr_run >= rerun_times:
                            raise exceptions.TestError(
                                "Failed to run dependent"
                                " tasks : %s" % dep)

            # Register final recoveries before running actual test
            final_recovers = test_params.get('post_process')
            if final_recovers is not None:
                final_recovers = final_recovers.split(' ')
                for final_recover in final_recovers:
                    t_path = _get_task_path_from_name(test_params,
                                                      final_recover)
                    self.log.info("Registering recoveries: %s" % t_path)
                    self.runner_queue.put({"func_at_exit": _run_rally_task,
                                           "args": (t_path,
                                                    deployment,
                                                    rally_arg_file,
                                                    self.logdir,
                                                    'False',
                                                    False),
                                           "once": True})

            # Run the indeed test
            task_id, err_count, pass_rate = _run_rally_task(test_name, deployment,
                                                 rally_arg_file, self.logdir,
                                                 'False', True, env)
            if task_id is None:
                raise exceptions.TestError("Failed to get rally task id")

            if test_params.get('html_report_for_each_rally_task',
                               'True') == 'True':
                cmd = ("rally task report %s --out %s --html-static"
                       % (task_id, os.path.join(self.logdir,
                                                'rally_report.html')))
                process.run(cmd)

            if (err_count is None or int(err_count) > 0) or \
                    (pass_rate == 'n/a' or float(pass_rate) <
                        float(self.params.get('rally_task_arg_success_rate'))):
                raise exceptions.TestFail("Rally task failed due to total "
                                          "pass_rate is %s" % pass_rate)

            # Sleep for some seconds between each test run
            time.sleep(int(test_params.get('test_interval', 1)))

        except process.CmdError as details:
            self._log_detailed_cmd_info(details.result)
            self.log.error("Failed to execute rally test: %s" %
                           details.result.stderr)
            raise exceptions.TestFail(details)

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

        run_func = None
        self.ct_type = self.params.get('ct_type')
        run_func = self._run_performance_test

        # TODO: the environment file is deprecated code, and should be removed
        # in future versions. Right now, it's being created on an Avocado temp
        # dir that is only persisted during the runtime of one job, which is
        # different from the original idea of the environment file (which was
        # persist information accross cloud-test/avocado-ct job runs)
        env_filename = os.path.join("/var/tmp/rally_env")
        env = utils_env.Env(env_filename, self.env_version)
        if self.ct_type == 'stability':
            if ((params.get('prepare_resource').lower() == 'true') and
            not (env.get_status_for_stability_resources())):
                env.set_status_for_stability_resources("ready")
                resource_util = ConfigStability(params)
                resource_util.create_resources_for_stability(params)

        test_passed = False
        try:
            try:
                try:
                    # Preprocess
                    # try:
                    #     params = env_process.preprocess(self, params, env)
                    # finally:
                    #     self.__safe_env_save(env)

                    # Initialize injection tests including workload and fault
                    need_injection = ( \
                            self.params.get('workload_injection') in 'true' or
                            self.params.get('fault_injection') in 'true')

                    force_injection = ( \
                            self.params.get('workload_injection_force', 'false')
                            in 'true' or
                            self.params.get('fault_injection_force', 'false')
                            in 'true')

                    if need_injection:
                        injector = utils_injection.Injection(params, env)
                        if not injector:
                            self.log.error("Failed to initialize injection")
                            if force_injection:
                                raise Exception("Failed to inject"
                                                "workload and/or fault")

                        if not injector.start() and force_injection:
                            msg = "Failed to inject workload/fault"
                            raise exceptions.InjectionFail(msg)
                        # Sleep specified time after injection
                        delay = int(params.get('sleep_after_injection', 3))
                        logging.info("Sleep %d seconds before running test" %
                                                                       delay)
                        time.sleep(delay)

                    # Run the test function
                    self.log.info("Start to run performance test")
                    try:
                        run_func(params, env)
                    finally:
                        self.__safe_env_save(env)

                except Exception, e:
                    # try:
                    #     env_process.postprocess_on_error(self, params, env)
                    # finally:
                    #     self.__safe_env_save(env)
                    logging.debug("Exception happened during running test")
                    raise e

            finally:

                # Postprocess
                try:
                    try:
                        # Stop injection
                        if need_injection:
                            injector.stop()

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

