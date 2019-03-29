import time

from avocado.core import exceptions
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase
from cloudtest.tests.nfv import test_utils


class LockComputeNodeTest(NFVTestBase):
    def __init__(self, params, env):
        super(LockComputeNodeTest, self).__init__(params, env)

    def setup(self):
        if self.env.get("node_for_lock"):
            self.node_for_lock = self.env.get("node_for_lock")
        else:
            nodes = self.compute_utils.get_all_hypervisors()
            if len(nodes) < 2:
                raise exceptions.TestError("No enough compute node for test,"
                                           " please check!")
            self.node_for_lock = nodes[0].hypervisor_hostname
            self.env["node_for_lock"] = self.node_for_lock

    def lock_compute_node(self):
        vm_count = int(self.params.get("vm_count"))
        net = test_utils.get_test_network(self.params)
        network_name = net['name']
        vm_name_list = self.compute_utils.create_vms_on_specific_node(
            node_name=self.node_for_lock,
            vm_count=vm_count,
            injected_key=self.pub_key,
            network_name=network_name)

        for vm_name in vm_name_list:
            vm = self.compute_utils.find_vm_from_name(vm_name)
            self.register_cleanup(vm)
            status = self.compute_utils.wait_for_vm_active(
                vm, delete_on_failure=False)
            if not status:
                raise exceptions.TestFail("Failed to create vm!")
        start_time = time.time()
        status = self.compute_utils.lock_compute_node(self.node_for_lock)
        if not status:
            raise exceptions.TestFail("Failed to lock compute node!")

        for vm_name in vm_name_list:
            vm = self.compute_utils.find_vm_from_name(vm_name)
            status = self.compute_utils.wait_for_vm_active(
                vm, delete_on_failure=False)
            if not status:
                raise exceptions.TestFail("Failed to migrate vm!")

        self.log.info("Time for lock node %s and vm migrate to another node "
                      "is %5.0f sec" % (self.node_for_lock,
                                    time.time() - start_time))

    def unlock_compute_node(self):
        node_name = self.env.get("node_for_lock")
        start_time = time.time()
        status = self.compute_utils.unlock_compute_node(node_name)
        if not status:
            raise exceptions.TestFail("Failed to lock compute node %s"
                                      % node_name)
        self.log.info("Time for unlock %s is: %5.0f sec"
                      % (node_name, time.time() - start_time))
        vm_name = self.compute_utils.create_vm_on_specific_node(node_name)
        vm = self.compute_utils.find_vm_from_name(vm_name)
        self.register_cleanup(vm)
        status = self.compute_utils.wait_for_vm_active(vm,
                                                       delete_on_failure=False)
        if not status:
            raise exceptions.TestFail("Create vm failed after unlock node %s"
                                      % node_name)

    def teardown(self):
        super(LockComputeNodeTest, self).teardown()