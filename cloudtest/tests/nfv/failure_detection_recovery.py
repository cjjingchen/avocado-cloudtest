from cloudtest import utils_misc
from avocado.core import exceptions
from cloudtest.remote import RemoteRunner
from cloudtest.openstack import ceilometer
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class VMFailureDetectionAndRecoveryTest(NFVTestBase):
    def __init__(self, params, env):
        super(VMFailureDetectionAndRecoveryTest, self).__init__(params, env)
        self.ceilometer_utils = ceilometer.Ceilometer(self.params)
        self.aodh_utils = ceilometer.AodhClient(self.params)

    def setup(self):
        self.params['vm_name'] = \
            'cloudtest_FDR_' + utils_misc.generate_random_string(6)

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

    def get_kvm_process_id(self, instance_name, host, cont_ip, password):
        session = RemoteRunner(client='ssh', host=cont_ip, username="root",
                               port="22", password=password)
        ssh_cmd = "ssh -q %s " % host
        cmd = "'ps -aux|grep kvm| grep %s'" % instance_name
        process_info = session.run(ssh_cmd + cmd)
        process_id = process_info.stdout.split()[1]
        self.log.info("KVM process id is %s" % process_id)
        return process_id

    def kill_kvm_process(self, process_id, host, cont_ip, password):
        session = RemoteRunner(client='ssh', host=cont_ip, username="root",
                               port="22", password=password)
        ssh_cmd = "ssh -q %s " % host
        cmd = "'kill -9 %s'" % process_id
        process_info = session.run(ssh_cmd + cmd)
        self.log.info("kill process id exit num is  %s" % process_info.exit_status)

    def get_failure_recovery_time(self):
        self.log.info("Prepare to get failure detection time.")
        alarm = self.ceilometer_utils.get_alarms_by_instance_name(
            instance_name=self.params['vm_name'])
        if not alarm:
            raise exceptions.TestFail(
                "Failed to get alarms about instance : %s." % self.params['vm_name'])
        failure_detection_recovery_time = \
            self.ceilometer_utils.get_failure_detection_recovery_time(alarm.alarm_id)
        if not failure_detection_recovery_time:
            raise exceptions.TestFail("Failed to get failure detection time or recovery time.")

    def get_alarms_info(self):
        self.log.info("Prepare to get alarms info.")
        try:
            alarm_list = self.aodh_utils.get_alarm_list()
        except Exception:
            raise Exception("We can not access alarm info.")
        self.log.info('We can access alert info,alert list length is %s' % len(alarm_list))

    def get_operationslog(self):
        self.log.info("Prepare to get operations info.")

    def test(self):
        """
        1、 create a vm
        2、 check where is the vm,and execute ps aux |grep kvm
        3、 find the process number of the kvm,and execute kill -9 [process
            number]
        4、 remember the time of failure detection and the time of vm recovery
            and the access to warn ifo and the operation logs
        :return:
        """
        self.create_vm()

        host = self.compute_utils.get_server_host(self.params['vm_name']).split('.')[0]
        self.log.info('The server located in %s.' % host)

        instance_name = self.compute_utils.get_vm_domain_name(self.params['vm_name'])
        self.log.info('The instance name of VM is %s.' % instance_name)
        process_id = self.get_kvm_process_id(instance_name, host, self.controller_ip,
                                             self.controller_password)
        self.kill_kvm_process(process_id, host, self.controller_ip,
                              self.controller_password)

        self.get_failure_recovery_time()

        self.get_alarms_info()

        self.get_operationslog()

    def teardown(self):
        super(VMFailureDetectionAndRecoveryTest, self).teardown()