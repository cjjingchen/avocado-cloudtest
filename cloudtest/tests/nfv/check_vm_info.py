from cloudtest import utils_misc
from avocado.core import exceptions
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class CheckVMInfoTest(NFVTestBase):
    def __init__(self, params, env):
        super(CheckVMInfoTest, self).__init__(params, env)

    def setup(self):
        self.params['vm_name'] = \
            'cloudtest_VMQ_' + utils_misc.generate_random_string(6)

    def create_vm(self):
        self.flavor = self.compute_utils.create_flavor()
        vm = self.compute_utils.create_vm(vm_name=self.params['vm_name'],
                                          image_name=self.params.get('image_name'),
                                          flavor_name=self.flavor.name,
                                          network_name=self.params.get('network_name', 'share_net'),
                                          injected_key=None, sec_group=None)
        self.register_cleanup(vm)
        if not self.compute_utils.wait_for_vm_active(vm):
            raise exceptions.TestFail("Failed to build VM: %s" % vm)

        return vm

    def query_vm(self, vm_name=None):
        """
        :param vm_name:
        :return:
        """
        instance = self.compute_utils.find_vm_from_name(vm_name)
        self.log.info('Name of instance is: %s.' % vm_name)

        host = self.compute_utils.get_server_host(vm_name).split('.')[0]
        self.log.info('Host location is: %s.' % host)

        net_info = instance.addresses
        net_name = net_info.keys()[0]
        ip_address = net_info[net_name][0]['addr']
        self.log.info('Network is: %s, IP address is: %s.' % (net_name, ip_address))

        resource_info = instance.flavor
        resource_info = self.compute_utils.flavor_client.get(resource_info['id'])
        ram, vcpus, disk = resource_info.ram, resource_info.vcpus, resource_info.disk
        if ram == self.flavor.ram and vcpus == self.flavor.vcpus and disk == self.flavor.disk:
            self.log.info('Resource utilization, ram is: %s M, vcpus is %s core, disk is %s G.'
                          % (ram, vcpus, disk))
        else:
            raise Exception('Flavor info is not correct.')
        self.log.info('Status of instance is: %s.' % instance.status)
        return instance

    def test(self):
        vm = self.create_vm()

        self.query_vm(vm.name)

    def teardown(self):
        super(CheckVMInfoTest, self).teardown()