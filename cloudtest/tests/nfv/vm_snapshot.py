import time
import sys

from avocado.core import exceptions
from cloudtest.openstack import image
from cloudtest.tests.nfv import test_utils
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class VMSnapshotTest(NFVTestBase):
    def __init__(self, params, env):
        super(VMSnapshotTest, self).__init__(params, env)
        self.image_utils = image.Image(self.params)
        self.image_name = None

    def setup(self):
        pass

    def __create_vm(self, image_name):
        net = test_utils.get_test_network(self.params)
        _network_name = net['name']
        vm = self.compute_utils.create_vm(vm_name=None,
                                          image_name=image_name,
                                          flavor_name=self.params.get('flavor_name'),
                                          network_name=_network_name,
                                          injected_key=self.pub_key, sec_group=None)
        self.vm_list.append(vm)
        if not self.compute_utils.wait_for_vm_active(vm):
            raise exceptions.TestFail("Failed to build VM: %s" % vm)
        time.sleep(60)
        return vm

    def __wait_for_vm_responsive(self, session, cmd, stdout, timeout=60):
        end_time = time.time() + timeout

        while time.time() < end_time:
            stdout_msg = session.run(cmd, timeout=timeout, ignore_status=True)
            self.log.info(stdout_msg)
            if (stdout_msg.exit_status == 0) and (stdout in stdout_msg.stdout):
                return True
        else:
            return False

    def __execute_cmd_within_vm(self, vm, cmd, stdout=''):
        vm_ip = self.compute_utils.assign_floating_ip_to_vm(vm)
        self.log.info("Created VM '%s', try to login via %s"
                      % (vm.name, vm_ip))
        session = test_utils.get_host_session(self.params, 'instance', vm_ip)
        status = self.__wait_for_vm_responsive(session, cmd, stdout)
        if status:
            self.log.info('Run cmd %s on %s successfully!' % (cmd, vm_ip))
        else:
            raise exceptions.TestFail(
                "Failed to execute cmd %s within vm %s!" % (cmd, vm_ip))

    def test_create_with_snapshot(self):
        # step1: create vm
        image_name = self.params.get('image_name')
        vm_origin = self.__create_vm(image_name)
        # step2: create folder within vm
        cmd = self.params.get("create_folder_cmd", "mkdir test")
        self.__execute_cmd_within_vm(vm_origin, cmd)
        time.sleep(60)
        # step3: create snapshot
        image = self.compute_utils.create_snapshot(vm_origin)
        if not image:
            raise exceptions.TestFail("Failed to create snapshot.")
        self.image_name = image.name
        time.sleep(60)
        # step4: use snapshot to creating vm
        vm_restore = self.__create_vm(self.image_name)
        # step5: check folder in new vm
        cmd = self.params.get("check_folder_cmd",
                              "find . -maxdepth 1 -name 'test' -type d")
        self.__execute_cmd_within_vm(vm_restore, cmd, 'test')

    def teardown(self):
        super(VMSnapshotTest, self).teardown()
        ex_type, ex_val, ex_stack = sys.exc_info()
        if (self.release_on_failure in 'yes' and ex_type is exceptions.TestFail) \
                or (ex_type is not exceptions.TestFail):
            time.sleep(300)
            if self.image_name:
                self.image_utils.delete_image(self.image_name)
