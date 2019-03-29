import time
import threading
import os

from avocado.core import exceptions
from avocado.utils import process
from cloudtest.tests.nfv import test_utils
from cloudtest import utils_misc
from cloudtest import remote
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class VMThread(threading.Thread):
    def __init__(self, func, args=()):
        super(VMThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result
        except Exception:
            pass


class VMMaxConcurrenceTest(NFVTestBase):
    def __init__(self, params, env):
        super(VMMaxConcurrenceTest, self).__init__(params, env)
        self.max_count = int(self.params.get('vm_max_count', 50))
        self.vms_name = []
        self.availability_zone = None
        self.vnics_count_per_vm = int(self.params.get('vnics_count_per_vm', 1))
        self.vm_creation_benchmark = int(self.params.get('vm_creation_benchmark',
                                                         '900'))
        self.vm_creation_maximum_time = int(self.params.get(
            'vm_creation_maximum_time', '300'))
        self.test_vm_responsive_cmd = self.params.get('test_vm_responsive_cmd',
                                                      'ping')
        self.vm_name = None
        self.error_vm_list = []
        self.checking_vm_list = []
        self.wrong_status_vm_list = []
        self.vm_private_key_path = self.params.get('vm_identity_file_path',
                                                   '~/.ssh/')
        self.is_vm_creation_test = False
        self.captured_vm_log = False
        self.test_start_time = time.time()

    def setup(self):
        self.vm_name = 'cloudtest-' + utils_misc.generate_random_string(6)
        if self.params.get('vm_create_on_single_node') in 'yes':
            self.__get_available_node_name()

    def __get_available_node_name(self):
        host_vm_count = test_utils.get_node_vm_count_dict(self.params)
        tuple_list = sorted(host_vm_count.items(), key=lambda d: d[1])
        node_name = tuple_list[0][0]
        host_zone = self.compute_utils.get_host_by_name(host_name=node_name).zone
        self.availability_zone = '%s:%s' % (host_zone, node_name)
        self.log.info("Availability zone: %s" % self.availability_zone)

    def __get_existed_vms(self):
        self.vm_list = []
        self.vms_name = []
        for i in range(1, self.max_count+1):
            vm_name = self.env['vm_name'] + '-%d' % i
            _vm = self.compute_utils.find_vm_from_name(vm_name)
            self.vm_list.append(_vm)
            self.vms_name.append(vm_name)

    def __scp_private_key_to_vm(self, instance_session, instance_fip):
        if self.test_vm_responsive_cmd not in 'ping':
            local_path = '/root/.ssh/id_rsa'
            remote_path = self.vm_private_key_path
            self.log.info("Upload private key to vm: %s" % remote_path)
            try:
                remote.scp_to_remote(host=instance_fip,
                                     port=22,
                                     username=self.image_username,
                                     password=self.image_password,
                                     local_path=local_path,
                                     remote_path=remote_path)
            except:
                cmd = "scp -o PreferredAuthentications=publickey"
                cmd += " -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa"
                cmd += " -o UserKnownHostsFile=/dev/null %s %s@%s:%s" % (
                       local_path, self.image_username, instance_fip,
                       remote_path)
                instance_session.run('mkdir -p ~/.ssh/')
                result = process.run(cmd, verbose=True, timeout=3)
                if result.exit_status != 0:
                    raise exceptions.TestError('Failed to upload private key'
                                               ' to VM: %s' % result.stderr)

            if self.params.get('image_name') in ('cirros', 'TestVM'):
                # Cirros OS use dropbear SSH Client, we need to convert
                # pem format key to dropbear format
                tmp_key_path = '/tmp/id_rsa'
                cmd = 'dropbearconvert openssh dropbear %s %s' % (
                       os.path.join(remote_path, 'id_rsa'), tmp_key_path)
                instance_session.run(cmd)
                instance_session.run('cp -f %s %s' % (tmp_key_path, remote_path))

    def __wait_for_vm_ping_vm(self, session, vm, timeout=9, ignore_status=False):
        if hasattr(vm, 'networks'):
            if len(vm.networks.values()) < 1:
                vm = self.compute_utils.find_vm_from_name(vm.name)
            fixed_ip = [ip[0] for ip in vm.networks.values()][0]
        else:
            fixed_ip = self.compute_utils.assign_floating_ip_to_vm(vm)

        status = test_utils.wait_for_vm_pingable(session, fixed_ip, timeout)
        return status

    def __wait_for_cmd_execution_from_vm(self, session, vm, timeout=9):
        if hasattr(vm, 'networks'):
            if len(vm.networks.values()) < 1:
                vm = self.compute_utils.find_vm_from_name(vm.name)
            fixed_ip = [ip[0] for ip in vm.networks.values()][0]
        else:
            fixed_ip = self.compute_utils.assign_floating_ip_to_vm(vm)

        cmd = self.test_vm_responsive_cmd
        ssh_cmd = "ssh -i ~/.ssh/id_rsa"
        if self.params.get('image_name') in ('cirros', 'TestVM'):
            ssh_cmd += ' -y'
        else:
            ssh_cmd += ' -o StrictHostKeyChecking=no'

        ssh_cmd += ' -o UserKnownHostsFile=/dev/null -p 22'
        ssh_cmd += " %s@%s '%s'" % (self.image_username, fixed_ip, cmd)
        expected_result = None
        if cmd in 'hostname':
            expected_result = vm.name
        elif cmd in 'whoami':
            expected_result = self.image_username
        elif cmd in 'cat /proc/uptime':
            expected_result = int(self.test_start_time)
        status = test_utils.wait_for_cmd_execution_within_vm(session, ssh_cmd,
                                                             expected_result,
                                                             timeout)
        return status

    def __create_ports(self):
        net = test_utils.get_test_network(self.params)
        _network_name = net['name']
        vnic_count = int(self.params.get('vnics_count_per_vm', 1))
        nets = self.network_utils.list_networks()
        vnics = []
        for _k in nets:
            for _v in nets[_k]:
                if _network_name == _v['name']:
                    net = _v
                    break
        if not net:
            raise Exception("Miss to specify network or can not to get network")
        else:
            _network_id = str(net["id"])
        name_prefix = 'cloudtest_' + utils_misc.generate_random_string(6)
        for i in range(0, vnic_count):
            nic_name = name_prefix + '_%d' % i
            port = self.network_utils.create_port(nic_name,
                                                  network_id=_network_id)
            self.log.info("Created port successfully!")
            vnics.append(port)

        return vnics

    def __create_vms_sequentially(self):
        self.log.info("Test creating %d VMs concurrently!" % self.max_count)
        self.is_vm_creation_test = True
        start_time = time.time()
        benchmark = self.vm_creation_benchmark
        timeout = self.vm_creation_maximum_time
        net = test_utils.get_test_network(self.params)
        network_name = net['name']
        threads = []
        for i in range(1, self.max_count+1):
            _vm_name = self.vm_name + '_%d' % i
            vnics = []
            if self.vnics_count_per_vm > 1:
                vnics = self.__create_ports()
                for vnic in vnics:
                    self.register_cleanup(vnic["id"], 'port')

                network_name = None
            _vm = self.compute_utils.create_vm(vm_name=_vm_name,
                                               image_name=self.params.get('image_name'),
                                               flavor_name=self.params.get('flavor_name'),
                                               network_name=network_name,
                                               injected_key=self.pub_key,
                                               sec_group=None,
                                               availability_zone=self.availability_zone,
                                               nics=vnics)
            self.vm_list.append(_vm)
            self.checking_vm_list.append(_vm)
            self.vms_name.append(_vm_name)

        for i in range(0, self.max_count):
            t = VMThread(self.compute_utils.wait_for_vm_in_status,
                         args=(self.vm_list[i], 'ACTIVE', 3, timeout))
            threads.append(t)

        for t in threads:
            t.setDaemon(True)
            t.start()

        for i in range(0, self.max_count):
            try:
                threads[i].join(timeout)
                if not threads[i].get_result():
                    raise Exception("Failed to create vm %d!" % (i+1))
            except Exception, e:
                raise exceptions.TestFail("Test failed for: %s" % str(e))

        self.__check_vms_responsive(timeout)

        cost_time = time.time() - start_time
        if cost_time > benchmark:
            msg = ("Failed to create %d VMs within %d(s)!, "
                   "actually used %d(s)"
                   % (self.max_count, benchmark, cost_time))
            raise exceptions.TestFail(msg)

        self.log.info("Successfully created %d VMs within %d(s), "
                      "actually used %d(s)"
                      % (self.max_count, benchmark, cost_time))

    def __concurrent_ops(self, ops, ops_name, timeout=900):
        threads = []
        for i in range(0, self.max_count):
            t = VMThread(ops, args=[self.vm_list[i].name, timeout])
            threads.append(t)

        for t in threads:
            t.setDaemon(True)
            t.start()

        result = True
        for i in range(0, self.max_count):
            try:
                threads[i].join(timeout)
                if not threads[i].get_result():
                    self.wrong_status_vm_list.append(self.vm_list[i])
                    raise Exception("Failed to %s vm %d!" % (ops_name, i+1))

            except Exception, e:
                self.log.error("Test failed for : %s" % str(e))
                result = False

        if not result:
            for _vm in self.wrong_status_vm_list:
                self.compute_utils.capture_vm_console_log(_vm)
            self.captured_vm_log = True
            raise exceptions.TestFail("Totally %s %d VMs, %d VMs %s failed"
                                      % (ops_name, self.max_count,
                                         len(self.wrong_status_vm_list), ops_name))

    def __pause_vms_concurrently(self):
        self.log.info("Test pausing %d VMs concurrently!" % self.max_count)
        start_time = time.time()
        benchmark = int(self.params.get('vm_pause_benchmark', '60'))
        timeout = int(self.params.get('vm_pause_maximum_time', '900'))
        self.__concurrent_ops(self.compute_utils.pause_vm, 'pause', timeout)

        cost_time = time.time() - start_time
        if cost_time > benchmark:
            msg = ("Failed to pause %d VMs within %d(s), "
                   "actually used %d(s)"
                   % (self.max_count, benchmark, cost_time))
            raise exceptions.TestFail(msg)

        self.log.info("Successfully paused %d VMs within %d(s), "
                      "actually used %d(s)"
                      % (self.max_count, benchmark, cost_time))

    def __unpause_vms_concurrently(self):
        self.log.info("Test unpausing %d VMs concurrently!" % self.max_count)
        start_time = time.time()
        benchmark = int(self.params.get('vm_unpause_benchmark', '60'))
        timeout = int(self.params.get('vm_unpause_maximum_time', '300'))
        self.__concurrent_ops(self.compute_utils.unpause_vm, 'unpause', timeout)

        cost_time = time.time() - start_time
        if cost_time > benchmark:
            msg = ("Failed to unpause %d VMs within %d(s), "
                   "actually used %d(s)"
                   % (self.max_count, benchmark, cost_time))
            raise exceptions.TestFail(msg)

        self.log.info("Successfully unpaused %d VMs within %d(s), "
                      "actually used %d(s)"
                      % (self.max_count, benchmark, cost_time))

    def __reboot_vms_concurrently(self):
        self.log.info("Test rebooting %d VMs concurrently!" % self.max_count)
        vms_operation = self.params.get('vms_operation')
        self.params['vms_operation'] = 'soft_reboot'
        start_time = time.time()
        benchmark = int(self.params.get('vm_rebooting_benchmark', '360'))
        timeout = int(self.params.get('vm_rebooting_maximum_time', '900'))
        self.__concurrent_ops(self.compute_utils.reboot_vm, 'reboot', timeout)
        for _vm in self.vm_list:
            self.checking_vm_list.append(_vm)
        self.__check_vms_responsive(timeout)

        cost_time = time.time() - start_time
        if cost_time > benchmark:
            msg = ("Failed to reboot %d VMs within %d(s), "
                   "actually used %d(s)"
                   % (self.max_count, benchmark, cost_time))
            raise exceptions.TestFail(msg)

        self.log.info("Successfully reboot %d VMs within %d(s), "
                      "actually used %d(s)"
                      % (self.max_count, benchmark, cost_time))

        if vms_operation is not None:
            self.params['vms_operation'] = vms_operation
        else:
            del self.params['vms_operation']

    def __stop_vms_concurrently(self):
        self.log.info("Test stopping %d VMs concurrently!" % self.max_count)
        start_time = time.time()
        benchmark = int(self.params.get('vm_stop_benchmark', '60'))
        timeout = int(self.params.get('vm_stop_maximum_time', '900'))
        self.__concurrent_ops(self.compute_utils.stop_vm, 'stop', timeout)

        cost_time = time.time() - start_time
        if cost_time > benchmark:
            msg = ("Failed to stop %d VMs within %d(s), "
                   "actually used %d(s)"
                   % (self.max_count, benchmark, cost_time))
            raise exceptions.TestFail(msg)

        self.log.info("Successfully stop %d VMs within %d(s), actually used %d(s)"
                      % (self.max_count, benchmark, cost_time))

    def __start_vms_concurrently(self):
        self.log.info("Test starting %d VMs concurrently!" % self.max_count)
        start_time = time.time()
        benchmark = int(self.params.get('vm_start_benchmark', '60'))
        timeout = int(self.params.get('vm_start_maximum_time', '900'))
        self.__concurrent_ops(self.compute_utils.start_vm, 'start', timeout)

        cost_time = time.time() - start_time
        if cost_time > benchmark:
            msg = ("Failed to start %d VMs within %d(s), "
                   "actually used %d(s)"
                   % (self.max_count, benchmark, cost_time))
            raise exceptions.TestFail(msg)

        self.log.info("Successfully start %d VMs within %d(s), actually used %d(s)"
                      % (self.max_count, benchmark, cost_time))

    def __suspend_vms_concurrently(self):
        self.log.info("Test suspending %d VMs concurrently!" % self.max_count)
        start_time = time.time()
        benchmark = int(self.params.get('vm_suspending_benchmark', '300'))
        timeout = int(self.params.get('vm_suspending_maximum_time', '900'))
        self.__concurrent_ops(self.compute_utils.suspend_vm, 'suspend', timeout)

        cost_time = time.time() - start_time
        if cost_time > benchmark:
            msg = ("Failed to suspend %d VMs within %d(s), "
                   "actually used %d(s)"
                   % (self.max_count, benchmark, cost_time))
            raise exceptions.TestFail(msg)

        self.log.info("Successfully suspended %d VMs within %d(s), "
                      "actually used %d(s)"
                      % (self.max_count, benchmark, cost_time))

    def __resume_vms_concurrently(self):
        self.log.info("Test resuming %d VMs concurrently!" % self.max_count)
        start_time = time.time()
        benchmark = int(self.params.get('vm_resume_benchmark', '300'))
        timeout = int(self.params.get('vm_resume_maximum_time', '900'))
        self.__concurrent_ops(self.compute_utils.resume_vm, 'resume', timeout)

        cost_time = time.time() - start_time
        if cost_time > benchmark:
            msg = ("Failed to resume %d VMs within %d(s), "
                   "actually used %d(s)"
                   % (self.max_count, benchmark, cost_time))
            raise exceptions.TestFail(msg)

        self.log.info("Successfully resume %d VMs within %d(s), "
                      "actually used %d(s)"
                      % (self.max_count, benchmark, cost_time))

    def __delete_vms_concurrently(self):
        self.log.info("Test deleting %d VMs concurrently!" % self.max_count)
        start_time = time.time()
        benchmark = int(self.params.get('vm_deletion_benchmark', '60'))
        timeout = int(self.params.get('vm_deletion_maximum_time', '900'))
        self.__concurrent_ops(self.compute_utils.delete_vm, 'delete', timeout)

        cost_time = time.time() - start_time
        if cost_time > benchmark:
            msg = ("Failed to deleted %d VMs within %d(s), "
                   "actually used %d(s)"
                   % (self.max_count, benchmark, cost_time))
            raise exceptions.TestFail(msg)

        self.log.info("Successfully deleted %d VMs within %d(s), "
                      "actually used %d(s)"
                      % (self.max_count, benchmark, cost_time))

    def __create_flavor(self, flavor_name, ram, vcpus, disk):
        try:
            self.compute_utils.get_flavor_id(name=flavor_name)
        except:
            self.log.info("Failed to find flavor %s, try to create one!"
                          % flavor_name)
            self.flavor = self.compute_utils.create_flavor(name=flavor_name,
                                                           ram=ram, vcpus=vcpus,
                                                           disk=disk)

    def __check_vms_responsive(self, timeout):
        start_time = time.time()
        i = 0
        instance_session = None
        instance_fip = None
        while time.time() < (start_time + timeout):
            _vm = self.checking_vm_list[i]
            ret = self.compute_utils.wait_for_vm_in_status(_vm, 'ACTIVE',
                                                           3, timeout=9)
            if not ret:
                _vm = self.compute_utils.find_vm_from_name(_vm.name)
                if _vm.status == 'ERROR':
                    self.log.error("Failed to create vm %s" % _vm.name)
                    self.error_vm_list.append(_vm)
                    self.checking_vm_list.pop(i)
                else:
                    i += 1
            elif instance_session is None:
                if self.params.get('vms_operation', 'creation') in 'soft_reboot':
                    vm_ipaddr = self.compute_utils.get_vm_ipaddr(_vm.name)
                    self.log.info("vm addr: %s" % vm_ipaddr)
                    if vm_ipaddr.get('floating') is None:
                        i += 1
                        continue
                    else:
                        instance_fip = vm_ipaddr['floating']
                if instance_fip is None:
                    instance_fip = \
                        self.compute_utils.assign_floating_ip_to_vm(_vm)
                instance_session = test_utils.get_host_session(
                    self.params, 'instance', instance_fip)
                self.__scp_private_key_to_vm(instance_session, instance_fip)
                vm_nic_mtu = self.params.get('mtu', '1400')
                cmd = 'sudo ifconfig eth0 mtu %s' % vm_nic_mtu
                self.log.info('Changing mtu to %s of VM: %s' % (vm_nic_mtu,
                                                                self.vm_list[0]))
                instance_session.run(cmd, ignore_status=False)
                self.checking_vm_list.pop(i)
            else:
                if self.params.get('need_ssh_login') in 'yes':
                    if self.test_vm_responsive_cmd in 'ping':
                        ret = self.__wait_for_vm_ping_vm(instance_session, _vm)
                    else:
                        ret = self.__wait_for_cmd_execution_from_vm(
                            instance_session, _vm)
                if ret:
                    self.checking_vm_list.pop(i)
                else:
                    i += 1

            if len(self.checking_vm_list) == 0:
                break

            i = i % len(self.checking_vm_list)

        if len(self.error_vm_list) > 0 or len(self.checking_vm_list) > 0:
            for _vm in self.checking_vm_list:
                self.compute_utils.capture_vm_console_log(_vm)
            self.captured_vm_log = True
            raise exceptions.TestFail("Failed to wait all created vm responsive!")

    def _vm_concurrent_incremental_addition(self, concurrence_count, vm_add_delta):
        benchmark = self.vm_creation_benchmark
        start_time = time.time()

        self.__create_vms_concurrently_with_params(concurrence_count)

        self.max_count = concurrence_count
        vm_add_max_count = int(self.params.get("vm_add_max_count", "-1"))
        while vm_add_max_count == -1 or self.max_count < vm_add_max_count:
            self.log.info("Try to add %d vm!" % vm_add_delta)
            self.vm_name= 'cloudtest-' + utils_misc.generate_random_string(6)
            self.__create_vms_concurrently_with_params(vm_add_delta)
            self.max_count = self.max_count + vm_add_delta

        cost_time = time.time() - start_time
        if cost_time > benchmark:
            msg = ("Failed to create %d VMs within %d(s)!, "
                   "actually used %d(s)"
                   % (self.max_count, benchmark, cost_time))
            raise exceptions.TestFail(msg)

        self.log.info("Successfully create %d VMs within %d(s), "
                      "actually used %d(s)"
                      % (self.max_count, benchmark, cost_time))

    def __create_vms_concurrently_with_params(self, concurrence_count):
        self.log.info("Test creating %d VMs concurrently!" % concurrence_count)
        self.is_vm_creation_test = True
        timeout = self.vm_creation_maximum_time
        net = test_utils.get_test_network(self.params)
        network_name = net['name']

        vnics = []
        if self.vnics_count_per_vm > 1:
            vnics = self.__create_ports()
            for vnic in vnics:
                self.register_cleanup(vnic["id"], 'port')
            network_name = None

        self.compute_utils.create_vm(vm_name=self.vm_name,
                                     image_name=self.params.get('image_name'),
                                     flavor_name=self.params.get('flavor_name'),
                                     network_name=network_name,
                                     injected_key=self.pub_key,
                                     sec_group=None,
                                     availability_zone=self.availability_zone,
                                     nics=vnics,
                                     min_count=concurrence_count)

        for i in range(1, concurrence_count + 1):
            _vm_name = self.vm_name + '-%d' % i
            self.vms_name.append(_vm_name)
            _vm = self.compute_utils.find_vm_from_name(_vm_name)
            self.vm_list.append(_vm)
            self.checking_vm_list.append(_vm)

        self.__check_vms_responsive(timeout)

    def __create_vms_concurrently(self):
        benchmark = self.vm_creation_benchmark
        start_time = time.time()

        self.__create_vms_concurrently_with_params(self.max_count)
        cost_time = time.time() - start_time
        if cost_time > benchmark:
            msg = ("Failed to create %d VMs within %d(s)!, "
                   "actually used %d(s)"
                   % (self.max_count, benchmark, cost_time))
            raise exceptions.TestFail(msg)

        self.log.info("Successfully create %d VMs within %d(s), "
                      "actually used %d(s)"
                      % (self.max_count, benchmark, cost_time))

    def test_create_vms_concurrence(self):
        self.__create_vms_concurrently()
        self.__delete_vms_concurrently()

    def test_vms_operation_concurrence(self):
        if self.params.get('vms_operation') in 'creation':
            self.env['vm_name'] = self.vm_name
            self.__create_vms_concurrently()
        else:
            if self.env.get('vm_name') is not None:
                self.__get_existed_vms()
            else:
                self.env['vm_name'] = self.vm_name
                self.__create_vms_concurrently()

        if self.params.get('vms_operation') in 'suspend_and_resume':
            self.__suspend_vms_concurrently()
            self.__resume_vms_concurrently()
        if self.params.get('vms_operation') in 'soft_reboot':
            self.__reboot_vms_concurrently()
        if self.params.get('vms_operation') in 'pause_and_unpause':
            self.__pause_vms_concurrently()
            self.__unpause_vms_concurrently()
        if self.params.get('vms_operation') in 'stop_and_start':
            self.__stop_vms_concurrently()
            self.__start_vms_concurrently()
        if self.params.get('vms_operation') in 'delete':
            self.__delete_vms_concurrently()
            del self.env

    def test_vms_repeated_operation_concurrence(self):
        self.max_count = int(self.params.get('vm_max_count_times_1', 5))
        self.__create_vms_sequentially()
        self.__reboot_vms_concurrently()
        self.__pause_vms_concurrently()
        self.__delete_vms_concurrently()
        self.max_count = int(self.params.get('vm_max_count_times_2', 10))
        self.vms_name = []
        self.vm_list = []
        self.__create_vms_sequentially()
        self.__reboot_vms_concurrently()
        self.__pause_vms_concurrently()
        self.__delete_vms_concurrently()

    def test_vms_max_concurrent_number(self):
        stats = self.compute_utils.get_hypervisor_statistics()
        flavor_name = self.params.get('flavor_name', '2-2048-20')
        flavor_ram = int(self.params.get('flavor_ram', 2048))
        flavor_vcpus = int(self.params.get('flavor_vcpus', 2))
        flavor_disk = int(self.params.get('flavor_disk', 20))
        vm_add_delta = int(self.params.get('vm_add_delta', 1))
        if flavor_name is not None:
            self.__create_flavor(flavor_name, flavor_ram, flavor_vcpus,flavor_disk)
        vm_cardinal_number = min(stats.free_ram_mb/flavor_ram,
                                 stats.free_disk_gb/flavor_disk)/2
        self.log.info("VM creation cardinal number is: %d" % vm_cardinal_number)
        self._vm_concurrent_incremental_addition(vm_cardinal_number, vm_add_delta)
        self.__reboot_vms_concurrently()
        self.__stop_vms_concurrently()
        self.__start_vms_concurrently()
        self.__pause_vms_concurrently()
        self.__unpause_vms_concurrently()
        self.__delete_vms_concurrently()

    def teardown(self):
        if self.is_vm_creation_test:
            self.log.info('-' * 60)
            self.log.info("Totally create %d VMs, %d VMs ERROR, %d VMs is not responsive"
                          % (self.max_count, len(self.error_vm_list),
                             len(self.checking_vm_list)))
            self.log.info("ERROR VMs list: %s" % self.error_vm_list)
            self.log.info("Not responsive VMs list: %s" % self.checking_vm_list)
            self.log.info('-' * 60)
            if not self.captured_vm_log:
                for _vm in self.checking_vm_list:
                    self.compute_utils.capture_vm_console_log(_vm)

        if self.params.get('need_delete_vms') in 'no':
            self.vm_list = []

        super(VMMaxConcurrenceTest, self).teardown()
