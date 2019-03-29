"""
Avocado CloudTest plugin for network performance tool -- shaker
"""
import Queue
import logging
import os
import re
import sys

from avocado.core import exceptions
from avocado.core import test
from avocado.core import loader
from avocado.core import output
from avocado.core.settings import settings

from avocado.utils import genio
from avocado.utils import process
from avocado.utils import stacktrace

# Avocado's plugin interface module has changed location. Let's keep
# compatibility with old for at, least, a new LTS release
# try:
#     from avocado.core.plugin_interfaces import CLI
# except ImportError:
#     from avocado.plugins.base import CLI    # pylint: disable=E0611,E0401

from cloudtest import data_dir
from cloudtest import utils_params

from avocado.plugins.ct_options import CloudTestOptionsProcess


class ShakerTestLoader(loader.TestLoader):
    """
    Avocado loader plugin to load avocado-ct tests
    """

    name = 'shaker'

    def __init__(self, args, extra_params):
        super(ShakerTestLoader, self).__init__(args, extra_params)
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

        return {ShakerTest: 'SHAKER'}

    @staticmethod
    def get_decorator_mapping():
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: decorator function}
        """
        term_support = output.TermSupport()
        return {ShakerTest: term_support.healthy_str}

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
            if 'shaker' in params.get('ct_type'):
                test_suite.append((ShakerTest, test_parameters))

        return test_suite

class ShakerTest(test.Test):
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
        :param ct_params: avocado-HealthCheckTest/cartesian_config params stored
        as `self.params`.
        """
        self.bindir = data_dir.get_root_dir()

        self.iteration = 0
        self.resultsdir = None
        self.file_handler = None
        self.background_errors = Queue.Queue()
        self.whiteboard = None
        self.casename = name
        super(ShakerTest, self).__init__(methodName=methodName, name=name,
                                         params=params,
                                         base_logdir=base_logdir, job=job,
                                         runner_queue=runner_queue)
        self.tmpdir = os.path.dirname(self.workdir)
        # Move self.params to self.avocado_params and initialize TempestTest
        # (cartesian_config) params
        self.avocado_params = self.params
        self.params = utils_params.Params(ct_params)

        self.resultsdir = self.logdir
        self.reportsdir = os.path.join(self.logdir, 'shaker.log')
        self.timeout = ct_params.get("test_timeout", self.timeout)
        # utils_misc.set_log_file_dir(self.logdir)

    @property
    def datadir(self):
        """
        Returns the path to the directory that contains test data files

        For HealthCheckTest tests, this always returns None. The reason is that
        individual HealthCheckTest tests do not map 1:1 to a file and do not
        provide the concept of a datadir.
        """
        return None

    @property
    def filename(self):
        """
        Returns the name of the file (path) that holds the current test

        For HealthCheckTest tests, this always returns None. The reason is that
        individual HealthCheckTest tests do not map 1:1 to a file.
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
        Avocado-HealthCheckTest replaces Test.params with avocado-ct params.
        This function reports the original params on `get_state` call.
        """
        state = super(ShakerTest, self).get_state()
        state["params"] = self.__dict__.get("avocado_params")
        return state

    def _start_logging(self):
        super(ShakerTest, self)._start_logging()
        root_logger = logging.getLogger()
        root_logger.addHandler(self.file_handler)

    def _stop_logging(self):
        super(ShakerTest, self)._stop_logging()
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

        :param env: The HealthCheckTest env object
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

        test_passed = False
        t_type = None

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
                    self.log.info("Try to run shaker test: %s" %
                                  test_name)
                    working_dir = os.getcwd()
                    shaker_dir = params.get('shaker_path')
                    scenario = params.get('scenario')
                    self.log.info("Try to change to shaker dir: %s" %
                                  shaker_dir)
                    os.chdir(shaker_dir)

                    test_name = test_name.replace('.', '/')
                    s_len = len(test_name)
                    test_name = test_name[len('shaker/scenario_list/'): s_len]
                    report_name = test_name.replace('/', '_')
                    conf_file = params.get('conf_path') + "shaker.conf"
                    output_path = params.get('output_path')
                    test_name = shaker_dir + "/scenarios/" + test_name

                    cmd = "shaker --debug --config-file %s " \
                          "--scenario %s.yaml --output %s%s.json" % \
                          (conf_file, test_name, output_path, report_name)

                    self.log.info('Try to run command: %s' % cmd)
                    process.run(cmd, shell=True, ignore_status=False)

                except Exception:
                    # try:
                    #     env_process.postprocess_on_error(self, params, env)
                    # finally:
                    #     self.__safe_env_save(env)
                    self.log.debug("Exception happened during running test")
                    raise

            finally:
                try:
                    cmd_gen_html = "shaker-report --input %s%s.json " \
                                   "--report %s%s.html" % \
                                   (output_path, report_name,
                                    output_path, report_name)
                    self.log.debug("Try to generate HTML report for shaker...")
                    process.run(cmd_gen_html, shell=True, ignore_status=False)
                    cmd = "cat %s%s.json" % (output_path, report_name)
                    result = process.run(cmd, shell=True,
                                         ignore_status=False).stdout
                    pat = ' "status": (.*) '
                    error_info = re.findall(pat, result)[0]
                    if error_info.find('error') != -1:
                        test_passed = False
                    else:
                        test_passed = True

                finally:
                    pass

        except Exception, e:
            if params.get("abort_on_error") != "yes":
                raise
            # Abort on error
            self.log.info("Aborting job (%s)", e)

        return test_passed
