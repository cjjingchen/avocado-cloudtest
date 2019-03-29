import re
import time
import threading

from avocado.core import exceptions
from cloudtest.openstack import ceilometer
from cloudtest import utils_misc
from avocado.utils import process
from cloudtest.tests.nfv import test_utils
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class VMCrashRecoveryTest(NFVTestBase):
    def __init__(self, params, env):
        super(VMCrashRecoveryTest, self).__init__(params, env)
        self.ceilometer_utils = ceilometer.Ceilometer(self.params)
        self.vm = None

    def setup(self):
        self.ping_count = self.params.get('vm_recovery_benchmark')

    def test(self):
        self.vm_name = 'vm_' + utils_misc.generate_random_string(6)

        extra_spec = {"hw:auto_recovery": "enabled"}
        self.flavor = self.compute_utils.create_flavor(extra_spec=extra_spec)

        self.vm = self.compute_utils.create_vm(
            vm_name=self.vm_name,
            flavor_name=self.flavor.name,
            image_name=self.params.get("image_name"),
            network_name=self.params.get("network_name"),
            injected_key=self.pub_key)

        if not self.compute_utils.wait_for_vm_active(self.vm):
            raise exceptions.TestFail("Failed to build VM: %s" % self.vm_name)

        self.vm_ip = self.compute_utils.assign_floating_ip_to_vm(self.vm)
        status = self.compute_utils.wait_for_vm_pingable(self.vm_ip, timeout=60)
        if not status:
            raise exceptions.TestFail('Can not ping vm %s by float ip %s' % (
                self.vm_name, self.vm_ip))
        self.log.info("Created VM '%s', try to login via %s"
                      % (self.vm_name, self.vm_ip))

        threads = []
        t_panic = threading.Thread(target=self.panic)
        threads.append(t_panic)
        t_ping = threading.Thread(target=self.check_ping)
        threads.append(t_ping)
        for t in threads:
            t.setDaemon(True)
            t.start()
        t_ping.join()
        t_panic.join()
        self.is_vm_pingable()
        test_utils.check_ping_msg(vm=self.vm,
                                  msg=self.result.stdout,
                                  ping_count=self.ping_count)
        self.check_alarm()

    def is_vm_pingable(self):
        pat = 'icmp_seq=(.*)'
        result = re.findall(pat, str(self.result.stdout))
        if 'Unreachable' in result[-1]:
            raise exceptions.TestFail('Failed to recover VM %s in %s(s)' %
                                      (self.vm_name, self.ping_count))

    def check_ping(self):
        cmd = 'ping -c %s -i 1 %s' % (self.ping_count, self.vm_ip)
        self.result = process.run(cmd=cmd, shell=True)
        self.log.info(self.result)

    def panic(self):
        cmd = 'echo 1 > /proc/sys/kernel/sysrq; echo c | tee /proc/sysrq-trigger'
        session = test_utils.get_host_session(self.params, 'instance',
                                              self.vm_ip)
        self.injection_time = time.time()
        session.run(cmd, timeout=20, ignore_status=True)
        self.log.info('Run cmd %s on %s successfully1' % (cmd, self.vm_ip))

    def check_alarm(self):
        """
        When a vm in kernel panic,
        'ceilometer alarm-list' will have a new alarm msg
        :return:
        """
        self.log.info('Start to check the alarms.')
        failure_detection_recovery_time = self.get_failure_recovery_time()
        detection_time = failure_detection_recovery_time[0].split('.')[0]

        injec_time = time.strftime('%Y-%m-%dT%H:%M:%S',
                                   time.localtime(self.injection_time))
        self.log.info('detection_time is %s, injection time is %s.' % (
            detection_time, injec_time))
        detection_time = time.strptime(detection_time, '%Y-%m-%dT%H:%M:%S')
        detection_time_zone = detection_time.tm_hour
        injec_time = time.strptime(injec_time, '%Y-%m-%dT%H:%M:%S')
        local_time_zone = injec_time.tm_hour

        detection_time = time.mktime(detection_time)
        detection_time = abs(detection_time - self.injection_time)
        if detection_time_zone != local_time_zone:
            self.log.info("Time zone is different between local and server.")
            time_zone_diff = abs(detection_time_zone - local_time_zone)
            detection_time = abs(time_zone_diff * 3600 - detection_time)

        self.log.info(
            'detection time is %s.' % self.params.get('detection_time'))
        if detection_time <= int(self.params.get('detection_time', 10)):
            self.log.info(
                'It takes %s seconds to check crash.' % detection_time)
        else:
            raise exceptions.TestFail(
                'It takes %s, more than 10s to find crash in VM.'
                % detection_time)

    def get_failure_recovery_time(self):
        self.log.info("Prepare to get failure detection time.")
        alarm = self.ceilometer_utils.get_alarms_by_instance_name(
            instance_name=self.vm_name)
        if not alarm:
            raise exceptions.TestFail(
                "Failed to get alarms about instance : %s." % self.vm_name)
        failure_detection_recovery_time = \
            self.ceilometer_utils.get_failure_detection_recovery_time(
                alarm.alarm_id)
        if not failure_detection_recovery_time:
            raise exceptions.TestFail(
                "Failed to get failure detection time or recovery time.")
        return failure_detection_recovery_time

    def teardown(self):
        if self.vm_name:
            vm = self.compute_utils.find_vm_from_name(self.vm_name)
            self.register_cleanup(vm)

        super(VMCrashRecoveryTest, self).teardown()
