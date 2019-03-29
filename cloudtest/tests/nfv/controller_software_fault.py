import threading
import time

from avocado.core import exceptions
from cloudtest.tests.nfv import test_utils
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class ControllerSoftwareFaultTest(NFVTestBase):
    def __init__(self, params, env):
        super(ControllerSoftwareFaultTest, self).__init__(params, env)
        self.ha_config_path = self.params.get('ha_config_path')
        self.master_session = None
        self.slave_session = None
        self.service_name = None

    def setup(self):
        self.service_action = self.params.get('action', 'restart')
        self.service_name, master_host_ip = test_utils.get_ha_protect_service_info(
            self.controller_ip, self.controller_password,
            self.ha_config_path, master=True)
        self.master_session = test_utils.get_host_session(self.params,
                                                          'controller',
                                                          master_host_ip)
        self.service_name, slave_host_ip = test_utils.get_ha_protect_service_info(
            self.controller_ip, self.controller_password,
            self.ha_config_path, master=False)
        self.slave_session = test_utils.get_host_session(self.params,
                                                          'controller',
                                                          master_host_ip)
        if self.params.get('service_name') is not None:
            self.service_name = self.params.get('service_name')

    def __act_to_service_and_create_vm(self, session):
        timeout = int(self.params.get('vm_creation_benchmark', 60))
        vm = self.compute_utils.create_vm(vm_name=None,
                                          image_name=self.params.get('image_name'),
                                          flavor_name=self.params.get('flavor_name'),
                                          network_name=self.params.get('network_name'),
                                          injected_key=self.pub_key)
        self.register_cleanup(vm)
        threads = []
        t = threading.Thread(
            target=test_utils.act_to_service,
            args=[session, self.service_name, self.service_action])
        threads.append(t)
        t = threading.Thread(
            target=self.compute_utils.wait_for_vm_in_status,
            args=[vm, 'ACTIVE', 3, timeout])
        threads.append(t)

        for t in threads:
            t.setDaemon(True)
            t.start()

        for i in range(0, len(threads)):
            try:
                threads[i].join(timeout)
            except Exception, e:
                raise exceptions.TestFail('Caught exception : %s!' % e.message)

        self.__wait_for_vm_responsive(vm)

    def __wait_for_vm_responsive(self, vm):
        login_benchmark = int(self.params.get('vm_creation_benchmark', '360'))
        cmd = self.params.get('test_vm_responsive_cmd', 'hostname')
        vm_fip = self.compute_utils.assign_floating_ip_to_vm(vm)
        session = test_utils.get_host_session(self.params, 'instance', vm_fip)
        expected_result = None
        if cmd in 'hostname':
            expected_result = vm.name
        elif cmd in 'whoami':
            expected_result = self.image_username
        status = test_utils.wait_for_cmd_execution_within_vm(session, cmd,
                                                             expected_result,
                                                             login_benchmark)
        if not status:
            self.compute_utils.capture_vm_console_log(vm_fip)
            raise exceptions.TestFail(
                "Exception happened during execute cmd within vm: %s"
                % vm.name)

    def test_controller_service_restart(self):
        self.__act_to_service_and_create_vm(self.master_session)
        time.sleep(int(self.params.get('sleep_after_test', 60)))
        self.__act_to_service_and_create_vm(self.slave_session)

    def teardown(self):
        super(ControllerSoftwareFaultTest, self).teardown()
        test_utils.act_to_service(self.master_session, self.service_name, 'start')
        test_utils.act_to_service(self.slave_session, self.service_name, 'start')
