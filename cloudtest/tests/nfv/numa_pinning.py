from avocado.utils import data_factory
from avocado.core import exceptions
from cloudtest.tests.nfv import test_utils
from cloudtest.openstack.cloud_manager import CloudManager
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class NumaPinningTest(NFVTestBase):
    def __init__(self, params, env):
        super(NumaPinningTest, self).__init__(params, env)

        self.ram = self.params.get('ram', 2048)
        self.vcpus = self.params.get('vcpus', 4)
        self.disk = self.params.get('disk', 32)

        self.controller_session = None

    def setup(self):
        cloud_manager = CloudManager(self.params, self.env)
        compute_node = cloud_manager.get_compute_node()
        self.compute_ip = compute_node[0].ip

        self.controller_ip = cloud_manager.get_controller_node()[0].ip

    def _create_vm_and_cpus(self, numa_count):
        self.log.info("NUMA count is %s" % numa_count)

        extra_spec = {"hw:numa_nodes": numa_count}
        i = 0
        while i < numa_count:
            extra_spec['hw:numa_node.'+str(i)] = str(i)
            i += 1
        for key, value in extra_spec.items():
            self.log.info('Flavor extra specs key %s => value %s', key, value)

        vm_name = 'cloudtest_' + data_factory.generate_random_string(6)

        self.flavor = self.compute_utils.create_flavor(
            ram=self.ram, vcpus=self.vcpus, disk=self.disk,
            extra_spec=extra_spec)

        # Create instance1 with cpu_policy and cpu_thread_policy
        instance = test_utils.create_vm_with_cpu_pinning_and_wait_for_login(
            self.params, vm_name, injected_key=self.pub_key, ram=self.ram,
            vcpus=self.vcpus, disk=self.disk, flavor_name=self.flavor.name,
            **extra_spec)
        self.vm_list.append(instance)

        # Get instance name via name
        self.instance_name = self.compute_utils.get_vm_domain_name(vm_name)
        self.log.info("instance name is %s" % self.instance_name)
        # Get host via name
        self.compute_ip = self.compute_utils.get_server_host(vm_name)
        self.log.info("host is %s" % self.compute_ip)

    def test_vm_operation_with_numa_node_pinning(self):
        self.controller_session = test_utils.get_host_session(self.params,
                                                              'controller')
        if self.controller_session is None:
            raise exceptions.TestFail("Log in controller with ip %s failed." %
                                      self.controller_ip)

        # Get NUMA count on computer node
        numa_count = test_utils.get_numa_count(self.compute_ip,
                                               self.controller_session)
        self.log.info("Create VM with NUMA pinning")
        self._create_vm_and_cpus(numa_count)

        # Verify NUMA pinning
        test_utils.check_numa_pinning(self.instance_name,
                                      self.compute_ip, numa_count,
                                      self.controller_session)

    def teardown(self):
        super(NumaPinningTest, self).teardown()




