from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class VMAffinityTest(NFVTestBase):
    def __init__(self, params, env):
        super(VMAffinityTest, self).__init__(params, env)
        self.group_name = ''
        self.vm_name_list = []

    def setup(self):
        self.affinity_type = self.params.get('affinity_type')
        self.policy = self.params.get('policy')
        if self.policy == "anti-affinity":
            self.vm_diff_count = \
                int(self.params.get('vm_count_diff_between_host'))
            self.__create_vm_on_host_group()

    def test_host_affinity(self):
        self.group_name = 'group' + utils_misc.generate_random_string(6)
        group = self.compute_utils.create_server_group(policy=self.policy,
                                                       name=self.group_name)
        vm1_name = 'cloudtest-' + utils_misc.generate_random_string(6)
        vm2_name = 'cloudtest-' + utils_misc.generate_random_string(6)
        self.vm_name_list.append(vm1_name)
        self.vm_name_list.append(vm2_name)
        vm1 = self.compute_utils.create_vm(
            vm_name=vm1_name,
            image_name=self.params.get("image_name"),
            network_name=self.params.get("network_name"),
            injected_key=self.pub_key,
            scheduler_hints={"group": group.id})
        if not self.compute_utils.wait_for_vm_active(vm1):
            raise exceptions.TestFail("Failed to build VM: %s" % vm1_name)

        vm2 = self.compute_utils.create_vm(
            vm_name=vm2_name,
            image_name=self.params.get("image_name"),
            network_name=self.params.get("network_name"),
            injected_key=self.pub_key,
            scheduler_hints={"group": group.id})
        # wait for vm active
        if not self.compute_utils.wait_for_vm_active(vm2):
            raise exceptions.TestFail("Failed to build VM: %s" % vm2_name)

        vm1_host_id = self.compute_utils.find_vm_from_name(vm1_name).hostId
        vm2_host_id = self.compute_utils.find_vm_from_name(vm2_name).hostId
        # check the host of vm above
        if 'anti-affinity' in self.policy:
            if vm1_host_id == vm2_host_id:
                self.log.error("vm1_host_id: %s; vm2_host_id: %s" % (vm1_host_id,
                                                                vm2_host_id))
                raise exceptions.TestFail('After set anti-affinity policy,'
                                          'vm on same host.')
            self.log.info("Set anti-affinity successfully!")
        else:
            if vm1_host_id != vm2_host_id:
                self.log.error("vm1_host_id: %s; vm2_host_id: %s"
                               % (vm1_host_id, vm2_host_id))
                raise exceptions.TestFail('After set affinity policy,'
                                          'vm not on same host.')
            self.log.info("Set affinity successfully!")

    def __create_vm_on_host_group(self):
        """
        Realize load not balance by param host_count_per_group and diff_vm_of_host
        :return:
        """
        host_count_per_group = int(self.params.get("host_count_per_group"))
        vm_count_dict = self.compute_utils.get_host_vm_count()
        self.log.info(vm_count_dict)
        count = len(vm_count_dict.keys())
        tuple_list = sorted(vm_count_dict.items(), key=lambda d: d[1])
        if count <= 1:
            raise exceptions.TestFail('No enough compute node exited !')
        elif count <= host_count_per_group:
            self.__check_vm_count(vm_count_dict)
        else:
            group_count = count/host_count_per_group + 1
            for i in range(count-1):
                diff_count = self.vm_diff_count*(i/group_count)
                if diff_count:
                    node_name = tuple_list[i + 1][0]
                    name_list = self.compute_utils.create_vms_on_specific_node(
                                node_name=node_name,
                                vm_count=diff_count,
                                injected_key=self.pub_key)
                    self.vm_list.extend(name_list)

    def __check_vm_count(self, vm_count_dict):
        """
        We need load not balanced on each compute node.

        :return:
        """
        count = len(vm_count_dict.keys())
        tuple_list = sorted(vm_count_dict.items(), key=lambda d: d[1])
        for i in range(count-1):
            diff = tuple_list[i + 1][1] - tuple_list[i][1]
            if diff < self.vm_diff_count:
                node_name = tuple_list[i + 1][0]
                name_list = \
                    self.compute_utils.create_vms_on_specific_node(
                        node_name=node_name,
                        vm_count=self.vm_diff_count - diff,
                        injected_key=self.pub_key)
                self.vm_name_list.extend(name_list)
                key = tuple_list[i + 1][0]
                value = tuple_list[i + 1][1] + \
                        self.vm_diff_count - diff
                tuple_list[i + 1] = (key, value)
                self.log.info(tuple_list)

    def teardown(self):
        for vm_name in self.vm_name_list:
            vm = self.compute_utils.find_vm_from_name(vm_name)
            self.register_cleanup(vm)
        if self.group_name:
            self.compute_utils.delete_server_group(self.group_name)

        super(VMAffinityTest, self).teardown()
