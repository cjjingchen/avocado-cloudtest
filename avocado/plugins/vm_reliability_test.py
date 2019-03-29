# Copyright: Lenovo Inc. 2016~2017
# Author: Yingfu Zhou <zhouyf6@lenovo.com>

"""
Avocado CloudTest plugin
"""

import ConfigParser
import Queue
import csv
import logging
import os
import shutil
import subprocess
import sys

from avocado.core import exceptions
from avocado.core import test
from avocado.core import loader
from avocado.core import output
from avocado.core.settings import settings

from avocado.utils import genio
from avocado.utils import stacktrace
from cloudtest import data_dir
from cloudtest import utils_params
from cloudtest import utils_misc

from avocado.plugins.ct_options import CloudTestOptionsProcess


class VMReliabilityTestLoader(loader.TestLoader):
    """
    Avocado loader plugin to load avocado-ct tests
    """

    name = 'vmreliability'

    def __init__(self, args, extra_params):
        super(VMReliabilityTestLoader, self).__init__(args, extra_params)
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

        return {VMReliabilityTest: 'VMRELIABILITY'}

    @staticmethod
    def get_decorator_mapping():
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: decorator function}
        """
        term_support = output.TermSupport()
        return {VMReliabilityTest: term_support.healthy_str}

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
            if 'vm_reliability' in params.get('ct_type'):
                test_suite.append((VMReliabilityTest, test_parameters))

        return test_suite


class VMReliabilityTest(test.Test):
    """
    Main test class used to run a cloud test.
    """

    # env_version = utils_env.get_env_version()

    def __init__(self, methodName='runTest', name=None, params=None,
                 base_logdir=None, job=None, runner_queue=None,
                 ct_params=None):
        """
        :note: methodName, name, base_logdir, job and runner_queue params
               are inherited from test.Test
        :param params: avocado/multiplexer params stored as
                       `self.avocado_params`.
        :param ct_params: avocado-VMReliabilityTest/cartesian_config params
        stored as `self.params`.
        """
        self.bindir = data_dir.get_root_dir()

        self.iteration = 0
        self.file_handler = None
        self.background_errors = Queue.Queue()
        self.whiteboard = None
        self.casename = name
        super(VMReliabilityTest, self).__init__(methodName=methodName,
                                                name=name,
                                                params=params,
                                                base_logdir=base_logdir,
                                                job=job,
                                                runner_queue=runner_queue)
        self.tmpdir = os.path.dirname(self.workdir)
        # Move self.params to self.avocado_params and init VMReliabilityTest
        # (cartesian_config) params
        self.avocado_params = self.params
        self.params = utils_params.Params(ct_params)

    @property
    def datadir(self):
        """
        Returns the path to the directory that contains test data files

        For VMReliabilityTest tests, this always returns None. The reason
        is that individual VMReliabilityTest tests do not map 1:1 to a file
        and do not provide the concept of a datadir.
        """
        return None

    @property
    def filename(self):
        """
        Returns the name of the file (path) that holds the current test

        For VMReliabilityTest tests, this always returns None. The reason
        is that individual VMReliabilityTest tests do not map 1:1 to a file.
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
        Avocado-VMReliabilityTest replaces Test.params with avocado-ct params.
        This function reports the original params on `get_state` call.
        """
        state = super(VMReliabilityTest, self).get_state()
        state["params"] = self.__dict__.get("avocado_params")
        return state

    def _start_logging(self):
        super(VMReliabilityTest, self)._start_logging()
        root_logger = logging.getLogger()
        root_logger.addHandler(self.file_handler)

    def _stop_logging(self):
        super(VMReliabilityTest, self)._stop_logging()
        root_logger = logging.getLogger()
        root_logger.removeHandler(self.file_handler)

    def write_test_keyval(self, d):
        self.whiteboard = str(d)

    def verify_background_errors(self):
        """
        Verify if there are any errors that happened on background threads.

        :raise Exception: Any exception stored on the background_errors queue.
        """
        try:
            exc = self.background_errors.get(block=False)
        except Queue.Empty:
            pass
        else:
            raise exc[1], None, exc[2]

    def __safe_env_save(self, env):
        """
        Treat "env.save()" exception as warnings

        :param env: The VMReliabilityTest env object
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

    def _generate_config_ini_file(self, file_location, is_remote):
        filename = 'config.ini'
        if is_remote:
            filename = 'remote_config.ini'
        config_ini_file = open(os.path.join(file_location, filename), 'w')
        config_parser = ConfigParser.ConfigParser()
        config_parser.add_section('SSH_CREDENTIALS')
        config_parser.set('SSH_CREDENTIALS', 'ssh.username',
                          self.params.get('created_vm_username'))
        config_parser.set('SSH_CREDENTIALS', 'ssh.password',
                          self.params.get('created_vm_password'))
        if os.path.isfile(self.params.get('created_vm_public_key')):
            config_parser.set('SSH_CREDENTIALS', 'ssh.public_key_filename',
                              self.params.get('created_vm_public_key'))
        else:
            config_parser.set('SSH_CREDENTIALS', 'ssh.public_key_filename',
                              os.path.join(file_location, 'id_rsa.pub'))
        if os.path.isfile(self.params.get('created_vm_private_key')):
            config_parser.set('SSH_CREDENTIALS', 'ssh.key_filename',
                              self.params.get('created_vm_private_key'))
        else:
            config_parser.set('SSH_CREDENTIALS', 'ssh.key_filename',
                              os.path.join(file_location, 'id_rsa'))
        if is_remote:
            config_parser.add_section('TEST_RUNS')
            config_parser.set('TEST_RUNS', 'test_start',
                              self.params.get('test_runs_start'))
            config_parser.set('TEST_RUNS', 'test_end',
                              self.params.get('test_runs_end'))
        else:
            config_parser.add_section('TOOL_DATA')
            config_parser.set('TOOL_DATA', 'markov.mode',
                              self.params.get('tool_data_mode'))
            config_parser.add_section('VM_INFO')
            config_parser.set('VM_INFO', 'image_name',
                              self.params.get('created_vm_image_name'))
            config_parser.set('VM_INFO', 'flavor_name',
                              self.params.get('created_vm_flavor_name'))
            config_parser.set('VM_INFO', 'network_name',
                              self.params.get('created_vm_network_name'))

        config_parser.write(config_ini_file)
        config_ini_file.flush()
        config_ini_file.close()

    def _generate_vm_list_csv_file(self, file_location):
        vm_list = ['master']
        vm_total_count = int(self.params.get('created_vm_count'))
        for counter in range(1, vm_total_count + 1):
            vm_name = "vm" + str(counter)
            vm_list.append(vm_name)
        self.log.info("vm list as below:")
        self.log.info(vm_list)
        with open(os.path.join(file_location, 'vm_list.csv'), 'wb') as f:
            writer = csv.writer(f, delimiter=';', quotechar='|')
            [writer.writerow([vm]) for vm in vm_list]

    def _collect_csv_result(self, file_location, dest_location):
        files = filter(lambda file: file.endswith('.csv'),
                       os.listdir(file_location))
        for item in files:
            shutil.copy(os.path.join(file_location, item),
                        os.path.join(dest_location, item))

    def _generate_openrc_py_file(self, file_location):
        content = """
import os
os.environ['OS_USERNAME'] = '%s'
os.environ['OS_PASSWORD'] = '%s'
os.environ['OS_AUTH_URL'] = '%s'
os.environ['OS_TENANT_NAME'] = '%s'
""" % (os.environ['OS_USERNAME'], os.environ['OS_PASSWORD'],
       os.environ['OS_AUTH_URL'], os.environ['OS_TENANT_NAME'])

        openrc_file = os.path.join(file_location, 'openrc.py')
        genio.write_file(openrc_file, content)

    def _get_algorithm_result(self, file_location, algorithm_name):
        parameters = None
        with open(os.path.join(file_location, 'validated_models.csv'),
                  'rb') as f:
            reader = csv.reader(f, delimiter=';', quotechar='|')
            for row in reader:
                if algorithm_name == row[0]:
                    parameters = tuple(
                        row[1].strip('()').replace(' ', '').split(','))
                    break
        return parameters

    def _get_success_rate(self, file_location):
        total_failure = 0
        times = 0
        with open(os.path.join(file_location, 'f_rates.csv'),
                  'rb') as f:
            reader = csv.reader(f, delimiter=';', quotechar='|')
            for row in reader:
                times += 1
                total_failure += float(row[0])
        avg_failure = total_failure / times
        vm_count = int(self.params.get('created_vm_count'))
        total_count = vm_count * 10 * 30
        success_rate = round(100.0 - avg_failure / total_count * 100, 2)
        self.log.info("success rate is: %.2f%%" % success_rate)
        return success_rate

    def _runTest(self):
        params = self.params

        # If a dependency test prior to this test has failed, let's fail
        # it right away as TestNA.
        if params.get("dependency_failed") == 'yes':
            raise exceptions.TestNotFoundError("Test dependency failed")

        # Report the parameters we've received and write them as keyvals
        self.log.info("Test parameters:")
        keys = params.keys()
        keys.sort()
        for key in keys:
            self.log.info("    %s = %s", key, params[key])

        # Set environment variables for OpenStack
        utils_misc.set_openstack_environment()

        test_passed = False
        vm_reliability_test_dir = os.path.join(data_dir.CLOUDTEST_TEST_DIR,
                                               'vm_reliability_tester')

        self._generate_openrc_py_file(vm_reliability_test_dir)
        self._generate_config_ini_file(vm_reliability_test_dir, False)
        self._generate_config_ini_file(vm_reliability_test_dir, True)
        self._generate_vm_list_csv_file(vm_reliability_test_dir)

        try:
            try:
                try:
                    self.log.info("start to execute vm reliability test")
                    execute_cmd = "python %s" % os.path.join(
                        vm_reliability_test_dir, "vm-reliability-tester.py")
                    process = subprocess.Popen(execute_cmd, shell=True,
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.STDOUT)
                    while True:
                        line = process.stdout.readline()
                        if line.strip() != '':
                            self.log.info(
                                "[vm reliability test run] %s" % line)
                        if line == '' and process.poll() is not None:
                            break
                    if process.returncode != 0:
                        test_passed = False
                        raise exceptions.TestFail(
                            "vm reliability test failed, return code is %s" %
                            process.returncode)
                    self._collect_csv_result(vm_reliability_test_dir,
                                             self.logdir)
                    algorithm_params = self._get_algorithm_result(
                        vm_reliability_test_dir, "dweibull")
                    self.log.info(algorithm_params)
                    success_rate = self._get_success_rate(
                        vm_reliability_test_dir)
                    if success_rate >= float(params.get('vm_success_rate')):
                        test_passed = True
                    else:
                        raise exceptions.TestFail(
                            "can not reach the success rate threshold")
                    self.verify_background_errors()
                except Exception:
                    # try:
                    #     env_process.postprocess_on_error(self, params, env)
                    # finally:
                    #     self.__safe_env_save(env)
                    self.log.debug("Exception happened during running test")
                    raise

            finally:
                pass
                #     if self.__safe_env_save(env):
                #         env.destroy()   # Force-clean as it can't be stored

        except Exception, e:
            if params.get("abort_on_error") != "yes":
                raise
            # Abort on error
            self.log.info("Aborting job (%s)", e)

        return test_passed
