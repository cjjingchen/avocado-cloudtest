import time

from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest.openstack.cloud_manager import CloudManager
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase
from cloudtest.tests.nfv import test_utils


class ServicesHATest(NFVTestBase):
    def __init__(self, params, env):
        super(ServicesHATest, self).__init__(params, env)
        self.params = params
        self.env = env
        self.role = self.params.get('node_type', 'compute')
        self.service_name = self.params.get('service_name')
        self.select_policy = self.params.get('select_policy', 'random')
        self.fault_action = self.params.get('fault_action')
        self.fault_type = self.params.get('fault_type')
        cloud_manager = CloudManager(params, env)
        self.act_nodes = cloud_manager.get_nodes(self.role, self.service_name,
                                                 self.select_policy)
        self.vm = None
        self.fip = None
        self.benchmark = self.params.get('service_HA_benchmark', 360)
        self.test_vm_responsive_cmd = self.params.get('test_vm_responsive_cmd', 'ping')

    def setup(self):
        self.log.info("Create vm before service fault!")
        self.vm, self.fip = self.__create_vm(self.benchmark)

    def __wait_for_vm_responsive(self, vm_name, vm_fip):
        login_benchmark = int(self.params.get('vm_creation_benchmark', '360'))
        cmd = self.params.get('test_vm_responsive_cmd', 'hostname')
        session = test_utils.get_host_session(self.params, 'instance', vm_fip)
        expected_result = None
        if cmd in 'hostname':
            expected_result = vm_name
        elif cmd in 'whoami':
            expected_result = self.image_username
        status = test_utils.wait_for_cmd_execution_within_vm(session, cmd,
                                                             expected_result,
                                                             login_benchmark)
        if not status:
            self.compute_utils.capture_vm_console_log(vm_fip)
            raise exceptions.TestFail(
                "Exception happened during execute cmd within vm: %s"
                % vm_name)

    def __create_vm(self, timeout):
        cmd = self.test_vm_responsive_cmd
        net = test_utils.get_test_network(self.params)
        network_name = net['name']
        vm_name = 'cloudtest-' + utils_misc.generate_random_string(6)
        vm = self.compute_utils.create_vm(vm_name=vm_name,
                                          image_name=self.params.get('image_name'),
                                          flavor_name=self.params.get('flavor_name'),
                                          network_name=network_name,
                                          injected_key=self.pub_key, sec_group=None)
        self.register_cleanup(vm)

        if not self.compute_utils.wait_for_vm_active(vm):
            raise exceptions.TestFail("Failed to build VM: %s" % vm)

        vm_fip = self.compute_utils.assign_floating_ip_to_vm(vm)
        self.log.info("Created VM '%s', try to login via %s" % (vm_name, vm_fip))

        self.__wait_for_vm_responsive(vm_name, vm_fip)
        return vm, vm_fip

    def test_services_HA(self):
        self.log.info("Try to %s service %s"
                      % (self.fault_action, self.service_name))
        for node in self.act_nodes:
            service_info = node.get_service_info(service_name=self.service_name)
            self.log.info("service_info: %s" % service_info)
            if self.fault_type in 'process':
                pids = []
                pids.append(service_info['main_pid'])
                node.act_to_process(self.fault_action, pids)
            elif self.fault_type in 'service':
                node.act_to_service(self.fault_action, self.service_name)

        start_time = time.time()

        def _check_service_status():
            service_info = node.get_service_info(service_name=self.service_name)
            if service_info is not None:
                return True
            else:
                return False

        if not utils_misc.wait_for(_check_service_status, self.benchmark,
                                   text='Checking service status'):
            raise exceptions.TestFail('Service %s still not active!'
                                      % self.service_name)
        cost_time = time.time() - start_time
        self.log.info("Service %s has been pulled up by HA after %d(s)"
                      % (self.service_name, cost_time))

        self.log.info("Check created vm is still responsive")
        self.__wait_for_vm_responsive(self.vm.name, self.fip)
        self.log.info("Created vm is still responsive!")

        self.log.info("Create vm after service fault!")
        self.__create_vm(self.benchmark)

    def teardown(self):
        for node in self.act_nodes:
            service_info = node.get_service_info(service_name=self.service_name)
            if service_info is None:
                self.log.info("Try to pull up service %s manually!"
                              % self.service_name)
                node.act_to_service('start', self.service_name)
        super(ServicesHATest, self).teardown()
