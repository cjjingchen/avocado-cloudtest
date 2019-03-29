import time
import threading

from avocado.core import exceptions
from cloudtest.tests.nfv import test_utils
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class ComputeNodeHATest(NFVTestBase):
    """
    Create two vms on different compute node.
    vm_for_ping use for ping vm_for_panic
    using ipmitool/os reboot compute node of vm2
    check vm_for_panic recovery time:
    include state active time t1 and can ping by vm_for_ping t2
    """
    def __init__(self, params, env):
        super(ComputeNodeHATest, self).__init__(params, env)
        self.vm_name_list = []

    def setup(self):
        self.ipmi_ip = self.params.get('ipmi_ip')
        self.ipmi_user = self.params.get('ipmi_user')
        self.ipmi_passwd = self.params.get('ipmi_passwd')

        self.fault_type = self.params.get('fault_type')
        self.ping_recovery_time = self.params.get("ping_recovery_time")
        self.status_recovery_time = int(self.params.get("status_recovery_time"))

        self.controller_session = test_utils.get_host_session(self.params,
                                                              'controller')

    def test(self):
        if self.fault_type in "hard_fault" and not self.ipmi_ip:
            raise exceptions.TestSkipError("This case need compute node support"
                                           " ipmi and must set ipmitool, "
                                           "please check!")
        host_list = self.compute_utils.get_all_hypervisors()
        if len(host_list) < 2:
            raise exceptions.TestFail('No enough compute node for test!')

        extra_spec = {"hw:auto_recovery": "enabled"}
        self.flavor = self.compute_utils.create_flavor(extra_spec=extra_spec)
        host_for_ping = host_list[0]
        host_for_panic = host_list[1]
        host_name_for_ping = host_for_ping.hypervisor_hostname
        host_name_for_panic = host_for_panic.hypervisor_hostname

        # compute node ip of vm for panic
        self.host_ip_for_panic = host_for_panic.host_ip

        self.vm_for_ping, self.ip_for_ping = \
            self.create_vm_and_bind_ip(host_name_for_ping)
        self.vm_for_panic, self.ip_for_panic = \
            self.create_vm_and_bind_ip(host_name_for_panic)

        self.__run_multi_thread()

        test_utils.check_ping_msg(vm=self.vm_for_panic,
                                  msg=self.ping_msg,
                                  ping_count=self.ping_recovery_time)

    def __run_multi_thread(self):
        threads = []
        if self.fault_type in "hard_fault":
            t_hard_fault = threading.Thread(target=self.inject_fault_by_ipmi)
            threads.append(t_hard_fault)
        elif self.fault_type in "soft_fault":
            t_soft_fault = threading.Thread(target=self.inject_fault_reboot)
            threads.append(t_soft_fault)

        t_ping = threading.Thread(target=self.wait_for_ping)
        threads.append(t_ping)
        t_check_vm_state = threading.Thread(target=self.wait_for_vm_active())
        threads.append(t_check_vm_state)

        for t in threads:
            t.setDaemon(True)
            t.start()
        for i in range(len(threads)):
            threads[i].join()

    def create_vm_and_bind_ip(self, host_name):
        vm_name = self.compute_utils.create_vms_on_specific_node(
            node_name=host_name, flavor_name=self.flavor.name,
            vm_count=1, injected_key=self.pub_key)
        self.vm_name_list.append(vm_name)
        vm = self.compute_utils.find_vm_from_name(vm_name)

        if not self.compute_utils.wait_for_vm_active(vm):
            raise exceptions.TestFail("Failed to build VM: %s" % vm_name)

        vm_ip = self.compute_utils.assign_floating_ip_to_vm(vm)
        status = self.compute_utils.wait_for_vm_pingable(vm_ip=vm_ip, timeout=60)
        if not status:
            raise exceptions.TestFail('Can not ping vm %s by float ip %s' % (
                vm_name, vm_ip))
        self.log.info("Created VM '%s', bind float ip %s" % (vm_name, vm_ip))
        return vm, vm_ip

    def inject_fault_by_ipmi(self):
        cmd = "ipmitool -I lanplus -H %s -U %s -P %s chassis power off" % \
              (self.ipmi_ip, self.ipmi_user, self.ipmi_passwd)
        # cmd = 'mkdir tianhn1'
        self.controller_session.run(cmd, timeout=60, ignore_status=True)
        self.log.info('Run cmd %s on %s successfully1' % (cmd, self.controller_ip))

    def inject_fault_reboot(self):
        """
        Reboot compute node of vm_for_panic.
        """
        cmd = "ssh root@%s reboot" % self.host_ip_for_panic
        # cmd = "ssh root@%s mkdir tianhn1" % self.host_ip_for_panic
        self.controller_session.run(cmd, timeout=60, ignore_status=True)
        self.log.info('Run cmd %s on %s successfully1' % (cmd, self.controller_ip))

    def wait_for_ping(self):
        """
        Waiting for vm_for_panic can ping by vm_for_ping.
        """
        cmd = 'ping -c %s -i 1 %s' % (self.ping_recovery_time,
                                      self.ip_for_panic)
        time_out = int(self.ping_recovery_time) + 10
        session = test_utils.get_host_session(self.params, 'instance',
                                              self.ip_for_ping)
        self.ping_msg = session.run(cmd, timeout=time_out, ignore_status=True)
        self.log.info('Run cmd %s on %s successfully1' % (cmd, self.ip_for_ping))
        self.log.debug(self.ping_msg)

    def wait_for_vm_active(self):
        start_time = time.time()
        status = self.compute_utils.wait_for_vm_in_status(
            vm=self.vm_for_panic, status="ACTIVE", step=3,
            timeout=self.status_recovery_time)
        if not status:
            raise exceptions.TestFail("VM %s failed to active!" %
                                      self.vm_for_panic.name)
        cost_time = time.time() - start_time
        self.log.info("After inject fault, VM %s cost %s s become active." %
                 (self.vm_for_panic.name, str(cost_time)))

    def teardown(self):
        for vm_name in self.vm_name_list:
            vm = self.compute_utils.find_vm_from_name(vm_name)
            self.register_cleanup(vm)
        super(ComputeNodeHATest, self).teardown()

