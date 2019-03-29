import imp
import inspect
import threading
import logging
import os

from avocado.core.exceptions import InjectionFail
from cloudtest import data_dir
from cloudtest.openstack.cloud_manager import CloudManager

LOG = logging.getLogger('avocado.test')


class Injection(object):

    def __init__(self, params, env):
        self.params = params
        self.env = env
        self.logger = logging.getLogger("avocado.test")
        self.ret_flag = 0
        self.ret_value_list = []
        self.injection_list = []
        self.session_list = []
        self.injection_objects = []
        self.cloud_manager = CloudManager(params, env)
        self._init_module_and_environment()
        self.threads = []
        self.nodes_list = []

    def _get_params_by_type(self, _type, sub_params):
        _str = "%s_%s" % (_type, sub_params)
        return self.params.get(_str)

    def _generate_injection_object(self, injection_type):
        mod_name = self._get_params_by_type(injection_type, "script")
        cls_name = self._get_params_by_type(injection_type, "class_name")
        injection_cls = self._get_class_from_module(mod_name,
                                                    cls_name)
        LOG.info("Try to initialize injection module: '%s:%s'"
                 % (mod_name, cls_name))

        role = self._get_params_by_type(injection_type, "node_type")
        select_policy = self._get_params_by_type(injection_type,
                                                 "injection_type")
        service_name = self._get_params_by_type(injection_type,
                                                "service_name")
        injection_nodes = self.cloud_manager.get_nodes(
            role, service_name, select_policy)
        injection_obj = injection_cls(injection_nodes, self.params, self.env)

        return injection_obj

    def _get_injection_object(self):
        if self.params.get("workload_injection") in "true":
            injection_obj = self._generate_injection_object("workload")
            self.injection_objects.append(injection_obj)

        if self.params.get("fault_injection") in "true":
            injection_obj = self._generate_injection_object("fault")
            self.injection_objects.append(injection_obj)

    def _setup_injection_env(self):
        for injection in self.injection_objects:
            LOG.info("Calling setup for injection")
            injection.setup()

    def _init_module_and_environment(self):
        try:
            self._get_injection_object()
            self._setup_injection_env()
        except Exception, e:
            if self.session_list:
                self._close_all_sessions()
            self.logger.error("Injection failed in init phase")
            raise e

    def start(self):
        try:
            for injection in self.injection_objects:
                thread = threading.Thread(target=injection.test)
                thread.start()
                self.threads.append(thread)

            for thread in self.threads:
                thread.join()
        except Exception, exp:
            self._call_teardown()
            self._close_all_sessions()
            raise exp

    def stop(self):
        self._call_teardown()
        self._close_all_sessions()

    def _call_teardown(self):
        LOG.info("Start to do teardown")
        for injection_obj in self.injection_objects:
            injection_obj.teardown()

    def _close_all_sessions(self):
        for session in self.session_list:
            session.session.close()

    @staticmethod
    def _get_class_from_module(_module, cls_name):
        cls_obj = None
        module_path_list = [
            os.path.join(data_dir.CLOUDTEST_TEST_DIR, "reliability",
                         "workload"),
            os.path.join(data_dir.CLOUDTEST_TEST_DIR, "reliability", "fault")]
        f, p, d = imp.find_module(_module, module_path_list)
        try:
            loaded_module = imp.load_module(_module, f, p, d)
            for _, obj in inspect.getmembers(loaded_module):
                if inspect.getmodule(obj) == loaded_module and inspect.isclass(
                        obj) and obj.__name__ == cls_name:
                    cls_obj = obj
        except:
            LOG.error("Load module %s error" % _module)
        finally:
            if f:
                f.close()

        return cls_obj


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    params = {}
    env = {}
    params["identity_uri_ip"] = "10.100.64.36"
    params["openstack_user_name"] = "admin"
    params["openstack_user_password"] = "admin"
    params["openstack_tenant_name"] = "admin"
    params["openstack_auth_url"] = "http://192.168.50.2:5000/v2.0/"
    params["workload_injection"] = "true"
    params["workload_injection_force"] = "true"
    params["fault_injection"] = "true"
    params["fault_injection_force"] = "false"
    params["workload_script"] = "stress_ng"
    params["workload_class_name"] = "StressNG"
    params["workload_timeout"] = 10
    params["fault_script"] = "process_second"
    params["fault_class_name"] = "StressFault"
    params["fault_node_type"] = "compute"
    params["fault_injection_type"] = "random"
    params["fault_timeout"] = 15
    a = Injection(params, env)
    a.start()
    a.stop()
