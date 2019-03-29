from cloudtest import utils_misc
from avocado.core import exceptions
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class CheckVMLifeCycleTest(NFVTestBase):
    def __init__(self, params, env):
        super(CheckVMLifeCycleTest, self).__init__(params, env)

    def setup(self):
        self.params['vm_name'] = \
            'cloudtest_VMLC_' + utils_misc.generate_random_string(6)
        self.params['flavor_name'] = \
            'cloudtest_flavor_lc_' + utils_misc.generate_random_string(6)

    def create_vm(self):
        self.flavor = self.compute_utils.create_flavor(
            name=self.params['flavor_name'])
        vm = self.compute_utils.create_vm(vm_name=self.params['vm_name'],
                      image_name=self.params.get('image_name'),
                      flavor_name=self.flavor.name,
                      network_name=self.params.get('network_name', 'share_net'),
                      injected_key=None, sec_group=None)
#        self.register_cleanup(vm)
        if not self.compute_utils.wait_for_vm_active(vm):
            raise exceptions.TestFail("Failed to build VM: %s" % vm)

        return vm


    def test(self):
        vm = self.create_vm()

        if not self.compute_utils.reboot_vm(self.params['vm_name'],
                                            timeout=int(self.params['timeout'])):
            raise exceptions.TestFail("Failed to reboot VM: %s" % vm)

        if not self.compute_utils.pause_vm(self.params['vm_name'],
                                            timeout=int(self.params['timeout'])):
            raise exceptions.TestFail("Failed to pause VM: %s" % vm)
        if not self.compute_utils.unpause_vm(self.params['vm_name'],
                                            timeout=int(self.params['timeout'])):
            raise exceptions.TestFail("Failed to unpause VM: %s" % vm)
        if not self.compute_utils.suspend_vm(self.params['vm_name'],
                                            timeout=int(self.params['timeout'])):
            raise exceptions.TestFail("Failed to suspend VM: %s" % vm)
        if not self.compute_utils.resume_vm(self.params['vm_name'],
                                            timeout=int(self.params['timeout'])):
            raise exceptions.TestFail("Failed to resume VM: %s" % vm)
        if not self.compute_utils.stop_vm(self.params['vm_name'],
                                            timeout=int(self.params['timeout'])):
            raise exceptions.TestFail("Failed to stop VM: %s" % vm)
        if not self.compute_utils.start_vm(self.params['vm_name'],
                                            timeout=int(self.params['timeout'])):
            raise exceptions.TestFail("Failed to start VM: %s" % vm)
        
        if not self.compute_utils.delete_vm(self.params['vm_name'],
                                            timeout=int(self.params['timeout'])):
            raise exceptions.TestFail("Failed to delete VM: %s" % vm)


    def teardown(self):
        super(CheckVMLifeCycleTest, self).teardown()

