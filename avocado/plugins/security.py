import os
import re
import sys
import json
import Queue
import logging
import subprocess
import ConfigParser

from avocado.core import exceptions
from avocado.core import test
from avocado.core import loader
from avocado.core import output
from avocado.core.settings import settings

from avocado.utils import genio
from avocado.utils import process
from avocado.utils import stacktrace
from cloudtest import utils_misc

# try:
#     from avocado.core.plugin_interfaces import CLI
# except ImportError:
#     from avocado.plugins.base import CLI    # pylint: disable=E0611,E0401

from cloudtest import data_dir
from cloudtest import utils_params

from avocado.plugins.ct_options import CloudTestOptionsProcess


class SecurityTestLoader(loader.TestLoader):
    """
    Avocado loader plugin to load avocado-ct tests
    """

    name = 'security'

    def __init__(self, args, extra_params):
        super(SecurityTestLoader, self).__init__(args, extra_params)
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

        return {SecurityTest: 'SECURITY'}

    @staticmethod
    def get_decorator_mapping():
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: decorator function}
        """
        term_support = output.TermSupport()
        return {SecurityTest: term_support.healthy_str}

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
            if 'security' in params.get('ct_type'):
                test_suite.append((SecurityTest, test_parameters))

        return test_suite


class SecurityTest(test.Test):
    def __init__(self, methodName='runTest', name=None, params=None,
                 base_logdir=None, job=None, runner_queue=None, ct_params=None):
        self.bindir = data_dir.get_root_dir()

        self.iteration = 0
        self.resultsdir = None
        self.file_handler = None
        self.background_errors = Queue.Queue()
        self.whiteboard = None
        self.casename = name
        super(SecurityTest, self).__init__(methodName=methodName, name=name,
                                           params=params,
                                           base_logdir=base_logdir,
                                           runner_queue=runner_queue, job=job)
        self.avocado_params = self.params
        self.params = utils_params.Params(ct_params)
        self.debugdir = self.logdir
        self.resultsdir = self.logdir
        self.timeout = ct_params.get("test_timeout", self.timeout)

    @property
    def datadir(self):
        """
        Returns the path to the directory that contains test data files

        For SecurityTest tests, this always returns None. The reason is that
        individual CloudTest tests do not map 1:1 to a file and do not provide
        the concept of a datadir.
        """
        return None

    @property
    def filename(self):
        """
        Returns the name of the file (path) that holds the current test

        For SecurityTest tests, this always returns None. The reason is that
        individual CloudTest tests do not map 1:1 to a file.
        """
        return None

    def get_state(self):
        """
        Avocado-cloudtest replaces Test.params with avocado-ct params.
        This function reports the original params on `get_state` call.
        """
        state = super(SecurityTest, self).get_state()
        state["params"] = self.__dict__.get("avocado_params")
        return state

    def _start_logging(self):
        super(SecurityTest, self)._start_logging()
        root_logger = logging.getLogger()
        root_logger.addHandler(self.file_handler)

    def _stop_logging(self):
        super(SecurityTest, self)._stop_logging()
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
        params = self.params
        if params.get("dependency_failed") == 'yes':
            raise exceptions.TestNotFoundError("Test dependency failed")
        try:
            if params.get("security_type") == "bandit":
                self._banditTest()
            else:
                self._syntribosTest()
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

    def _banditTest(self):
        params = self.params
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
        try:
            mould = __import__(str(params.get("openstack_project_name")))
        except ImportError:
            raise Exception("Not Found The Mould")
        project_path = os.path.split(mould.__file__)[0]
        cmd = 'bandit -r %s' % project_path
        severitymax = int(params.get("severity_max"))
        confidencemax = int(params.get("confidence_max"))
        self.log.info('Try to run command: %s' % cmd)
        try:
            result = process.run(cmd, ignore_status=True, shell=True, verbose=True)
            self.log.info("[Bandit output] %s" % result.stdout)
            self._log_detailed_cmd_info(result)
            pattern = "Total([\s\S]*)"
            matched_result = re.findall(pattern, result.stdout)
            tmp1 = matched_result[0]
            pat = "High:(.*)"
            tmp2 = re.findall(pat, tmp1)
            severity = tmp2[0]
            confidence = tmp2[1]
            self.log.info("The severity High is :%s" % severity)
            self.log.info("The confidence High is :%s" % confidence)
            if int(severity) > severitymax:
                self.log.info("The naumber of severity High is: %s" % severity)
                raise exceptions.TestFail("The number of severity High is greater"
                                          " than allowable value ")
            elif int(confidence) > confidencemax:
                self.log.info("The naumber of confidence High is: %s" % confidence)
                raise exceptions.TestFail("The number of confidence High is greater"
                                          " than allowable value ")
            self.log.info("Scan Completed")
        except Exception:
            self.log.debug("Exception happended during runing test")
            raise

    def _syntribosTest(self):
        params = self.params
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

        utils_misc.set_openstack_environment()
        process.run('syntribos init --force', shell=True)

        syntribos_dir = os.path.join(self.logdir, 'syntribos')
        os.mkdir(syntribos_dir)
        syntribos_config_file = os.path.join(syntribos_dir, 'syntribos.conf')

        conf1 = ConfigParser.ConfigParser()
        conf1.read(syntribos_config_file)
        conf1.add_section("syntribos")
        conf1.add_section("user")
        conf1.add_section("auth")
        conf1.add_section('logging')

        auth_url = params.get("OS_AUTH_URL")
        endpoint = '//'.join([i for i in auth_url.split('/') if ':' in i])

        conf1.set("syntribos", "endpoint",
                      self.__get_endpoint(params.get('project_name')))

        conf1.set("user", "endpoint", endpoint)
        conf1.set("user", "username", params.get('OS_USERNAME'))
        conf1.set("user", "password", params.get('OS_PASSWORD'))
        conf1.set("user", "domain_name", params.get('OS_DOMAIN_NAME', 'Default'))
        conf1.set("user", "project_name", params.get('OS_TENANT_NAME'))
        conf1.set("auth", "endpoint", auth_url)
        conf1.set("logging", "log_dir", self.logdir)

        try:
            syntribos_file = open(syntribos_config_file, "w")
            conf1.write(syntribos_file)
            syntribos_file.close()
        except IOError:
            raise exceptions.TestError("Failed to generate config file")

        with open(syntribos_config_file, 'r') as f:
            content = f.read()
            self.log.info("Syntribos config:\n %s" % content)

        cmd = 'syntribos --config-file %s --syntribos-custom_root %s run' % (
                  syntribos_config_file, syntribos_dir)
        failure_count = 0
        error_count = 0

        try:
            self.log.info('Try to run command: %s' % cmd)
            sub = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
            result = ""
            while True:
                line = sub.stdout.readline()
                if line.strip() != '':
                    self.log.info("[Syntribos output] %s" % line.strip('\n'))
                    result += '\n' + line
                if line == '' and sub.poll() is not None:
                    break

            pat1 = "%  :(.+?)Failure"
            pat2 = ",(.+?)Error"
            failures = re.findall(pat1, result)
            errors = re.findall(pat2, result)

            for failure in failures:
                if int(failure) > 0:
                    failure_count += int(failure)

            for error in errors:
                if int(error) > 0:
                    error_count += int(error)

            self.log.info('=================')
            self.log.info('Total Failure: %d' % failure_count)
            self.log.info('Total Error: %d' % error_count)
            if failure_count > 0:
                raise exceptions.TestFail("There are yntribos test failures")
        except Exception:
            self.log.debug("Exception happended during runing syntribos test")
            raise
        finally:
            syntribos_file = open(syntribos_config_file, "w")
            syntribos_file.truncate()
            syntribos_file.close()
            self.log.info("Test Completed")

    def __get_endpoint(self, service_name):
        index = 0
        cmd = "openstack endpoint list --long -c 'Service Name' -c 'PublicURL' -f json"
        result = process.run(cmd, shell=True).stdout
        dict_results = json.loads(result)
        for dict_result in dict_results:
            if service_name in dict_result.get('Service Name'):
                url = dict_result.get('PublicURL')
                if url is not None:
                    index = url.find('%')
                if index > 0:
                    return url[:index-1]
                else:
                    return url

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

        self.status = 'PASS'
