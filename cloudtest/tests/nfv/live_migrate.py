import re
import os
import time
import threading

from avocado.core import exceptions

from cloudtest import remote
from cloudtest import utils_misc
from cloudtest.tests.nfv import test_utils
from cloudtest import data_dir
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class LiveMigrateTest(NFVTestBase):
    def __init__(self, params, env):
        super(LiveMigrateTest, self).__init__(params, env)

        self.volume_id_list = []
        self.net_name_list = []
        self.nic_dict = {}
        self.nic_id_list = []
        self.session_list = []

        self.tool_install_path = data_dir.COMMON_TEST_DIR

        self.ram = self.params.get('ram', 2048)
        self.vcpus = self.params.get('vcpus', 2)
        self.disk = self.params.get('disk', 40)
        self.ping_msg = ""
        self.session = None

    def setup(self):
        self.dpdk_version = self.params.get('dpdk_version')
        self.dstpath = '/root'
        self.workload_path = data_dir.NFVI_TEST_DIR
        self.setup_pktgen = "setup_pktgen.sh"
        self.start_pktgen = "start_pktgen.sh"
        self.shell_dpdk = "dpdk_cmd.sh"

    def _create_vm_and_cpuset(self, cpu_type):
        if cpu_type == "dedicated":
            extra_spec = {"hw:cpu_policy": cpu_type,
                          "hw:cpu_thread_policy": "isolate"}
        elif cpu_type == "shared":
            extra_spec = {"hw:cpu_policy": cpu_type}
        else:
            raise exceptions.TestFail("cpu_policy: %s is NOT expected." %
                                      cpu_type)

        vm_name = 'cloudtest_' + utils_misc.generate_random_string(6)
        # Create instance1 with cpu_policy and cpu_thread_policy
        instance = test_utils.create_vm_with_cpu_pinning_and_wait_for_login(
            self.params, vm_name, injected_key=self.pub_key, ram=self.ram,
            vcpus=self.vcpus, disk=self.disk, **extra_spec)
        self.vm_list.append(instance)

        # Get host via name
        self.host = self.compute_utils.get_server_host(vm_name)
        self.log.info("host is %s" % self.host)

        return instance

    def __set_host_name(self):
        host_list = self.compute_utils.get_all_hypervisors()
        if len(host_list) > 1:
            self.host_name = host_list[0].hypervisor_hostname
            return
        raise exceptions.TestFail("This case need more than available "
                                  "compute node, please check!")

    def __create_net_with_subnet(self, count=1):
        """
        :param count: net count need create
        """
        for i in range(count):
            net_name = "net_dpdk_" + utils_misc.generate_random_string(6)
            self.net_name_list.append(net_name)

            segmentation_id = \
                int(self.params.get('segmentation_id', 12)) + i

            net = self.network_utils.create_network(
                name=net_name,
                subnet=True,
                start_cidr='192.168.%s.0/24' % segmentation_id)

            self.log.info(net["network"])

    def __create_several_port(self, net_name, count=1):
        """
        Create several port of one network
        :param net_name: network name
        :param count: port count
        """
        nic_name = "cloudtest_nic_" + utils_misc.generate_random_string(6)
        nic_list = []
        for i in range(count):
            nic_name_str = nic_name + '_' + str(i)
            nic = self.network_utils.create_port(name=nic_name_str,
                                                 network_name=net_name)
            self.nic_id_list.append(nic["id"])
            nic_list.append(nic)
        self.nic_dict[net_name] = nic_list

    def __create_port(self):
        """
        Create several port on several network
        :return:
        """
        for net_name in self.net_name_list:
            self.__create_several_port(net_name, count=2)

    def __create_flavor_with_cpu_pinning(self, cpu_type,
                                         ram=1024*4, vcpus=3, disk=32):
        if cpu_type == "dedicated":
            extra_spec = {"hw:cpu_policy": cpu_type,
                          "hw:cpu_thread_policy": "isolate"}
        elif cpu_type == "shared":
            extra_spec = {"hw:cpu_policy": cpu_type}
        else:
            raise exceptions.TestFail("cpu_policy: %s is NOT expected." %
                                      cpu_type)
        self.flavor = self.compute_utils.create_flavor(
            ram=ram, vcpus=vcpus, disk=disk, extra_spec=extra_spec)

    def __create_vm_with_extra_nic(self, index=0):
        """
        :param index: the nic index of one net
        """
        nics = []
        for net_name in self.net_name_list:
            nics.append(self.nic_dict[net_name][index])
        vm_name = self.compute_utils.create_vms_on_specific_node(
            node_name=self.host_name, flavor_name=self.flavor.name,
            injected_key=self.pub_key, nics=nics)
        vm = self.compute_utils.find_vm_from_name(vm_name=vm_name)
        self.vm_list.append(vm)

        # wait for vm active
        if not self.compute_utils.wait_for_vm_active(vm):
            raise exceptions.TestFail("Failed to build VM: %s" % vm_name)

        # bind floating ip
        vm_ip = self.compute_utils.assign_floating_ip_to_vm(vm)

        # wait for vm ping
        status = self.compute_utils.wait_for_vm_pingable(vm_ip=vm_ip, timeout=60)
        if not status:
            raise exceptions.TestFail('Can not ping vm %s by float ip %s' % (
                vm_name, vm_ip))
        self.log.info("Created VM '%s', try to login via %s" % (vm_name, vm_ip))

        return vm, vm_ip

    def __get_nic_macaddr(self, session_pktgen):
        pat = 'ether (.*)  txqueuelen'
        cmd1 = 'ifconfig eth1 up;'
        cmd2 = 'ifconfig eth2 up;'
        cmd3 = 'ifconfig'
        cmd = cmd1 + cmd2 + cmd3
        result = session_pktgen.run(cmd, timeout=60)
        self.log.info('%s' % result)
        macaddr_list = self.__analyse_msg(msg=result.stdout, pat=pat)
        return macaddr_list[1], macaddr_list[2]

    def __enable_DPDK(self):
        """
        Enable DPDK on vm_dpdk
        """
        self.log.info('Begin enable DPDK......')
        session = test_utils.get_host_session(self.params, 'instance',
                                              self.vm_ip_dpdk)
        self.session_list.append(session)
        cmd = "sh %s/%s %s" % (self.dstpath, self.shell_dpdk,
                                   os.path.join(self.dstpath,
                                                self.dpdk_version))
        self.log.info("run cmd: %s" % cmd)
        result = session.run(command=cmd, timeout=2000, ignore_status=True)
        self.dpdk_msg = result.stdout
        self.log.info(self.dpdk_msg)

    def __configure_pktgen(self):
        """
        Using linux pktgen send data
        :param ip: floating ip of vm_pktgen
        :return:
        """
        self.log.info('Begin configure pktgen......')
        session = test_utils.get_host_session(self.params, 'instance',
                                              self.vm_ip_pktgen)
        self.session_list.append(session)
        cmd_setup = "sh %s/%s %s %s" % (self.dstpath, self.setup_pktgen,
                                            self.eth2_macaddr, self.eth1_macaddr)
        cmd_start_pktgen = "sh %s/%s" % (self.dstpath, self.start_pktgen)
        session.run(command=cmd_setup, timeout=20)
        session.run(command=cmd_start_pktgen, timeout=2000)

    def __attach_volume(self):
        # Create volume
        vol_name = 'cloudtest_volume_' + utils_misc.generate_random_string(6)
        vol_id = self.volume_utils.create_volume(vol_name, 1)
        status = self.volume_utils.get_volume_status(vol_id)
        self.log.info("The status of volume %s is %s" % (vol_id, status))
        self.volume_id_list.append(vol_id)

        # Attach volume
        self.compute_utils.attach_volume(self.vm_dpdk.id, vol_id)
        status = self.volume_utils.get_volume_status(vol_id)
        self.log.info("The status of volume %s is %s" % (vol_id, status))
        return vol_id

    def __detach_volume(self, vol_id):
        # Detach volume
        self.compute_utils.detach_volume(self.vm_dpdk.id, vol_id)
        status = self.volume_utils.get_volume_status(vol_id)
        self.log.info("The status of volume %s is %s" % (vol_id, status))

    def __live_migrate(self):
        self.log.info('Begin live migration.....')
        # Get target host for specified instance live migrate
        target_host = self.compute_utils.get_different_host_from(
            host_name=self.host_name)
        self.log.info("Get other host is %s" % target_host)

        volume_id = self.__attach_volume()

        # Live migrate on shared storage
        block_migration = self.params.get('block_migration')
        self.compute_utils.live_migrate(self.vm_dpdk.id, target_host,
                                        block_migration)
        # time.sleep(50)
        # host = self.compute_utils.get_server_host(self.vm_dpdk.name)
        status = self.__wait_for_live_migrate(target_host)
        if not status:
            raise exceptions.TestFail("Instance %s failed to live migrate to "
                                      "host %s, the instance is on host %s." %
                                      (self.vm_dpdk.name, target_host,
                                       self.host_name))
        self.__detach_volume(vol_id=volume_id)
        self.log.info('live migration successfully')

    def __wait_for_live_migrate(self, target_host):
        def is_migration():
            host = self.compute_utils.get_server_host(self.vm_dpdk.name)
            if host == target_host:
                return True
            return False

        return utils_misc.wait_for(is_migration, timeout=100, first=0, step=5,
                                   text="Waiting for %s live migrate from %s to %s" % (
                                       self.vm_dpdk.name, self.host_name, target_host))

    def __run_multi_thread(self):
        t1 = threading.Thread(target=self.__enable_DPDK)
        t1.setDaemon(True)
        t1.start()

        # after enable dpdk 10s, enable pktgen
        time.sleep(10)

        t2 = threading.Thread(target=self.__configure_pktgen)
        # threads.append(t2)
        t2.setDaemon(True)
        t2.start()

        # after enable pktgen 10s, run live migration
        time.sleep(10)

    def __get_ifconfig_msg(self, session):
        cmd = "ifconfig"
        result = session.run(command=cmd, timeout=10)
        return result.stdout

    def __analyse_ifconfig_msg(self, config_msg):
        pat = 'RX packets (\d+)'
        result = self.__analyse_msg(msg=config_msg, pat=pat)
        recv_1 = int(result[1])
        recv_2 = int(result[2])
        return recv_1, recv_2

    def __analyse_dpdk_data(self):
        pat = 'Packets received:(.*)'
        result = self.__analyse_msg(msg=self.dpdk_msg, pat=pat)
        recv_1 = int(result[-2].strip())
        recv_2 = int(result[-1].strip())
        self.log.info('DPDK data, recv1: %s; recv2: %s' % (recv_1, recv_2))
        return recv_1, recv_2

    def __analyse_msg(self, msg, pat):
        msg = re.findall(pat, str(msg))
        if not len(msg):
            raise exceptions.TestFail('Msg data or pattern error, '
                                      'please check!')
        return msg

    def __get_send_pkg(self, session_pktgen):
        cmd1 = 'cd /proc/net/pktgen;cat eth1 | grep pkts-sofar'
        cmd2 = 'cat eth2 | grep pkts-sofar'

        result_1 = session_pktgen.run(cmd1)
        result_2 = session_pktgen.run(cmd2)

        pat = 'pkts-sofar: (\d+)'
        send_pkg_1 = self.__analyse_msg(msg=result_1, pat=pat)
        send_pkg_2 = self.__analyse_msg(msg=result_2, pat=pat)

        return int(send_pkg_1[0]), int(send_pkg_2[0])

    @staticmethod
    def __compute_result(send_pkg_1, send_pkg_2,
                         recv_pkg_1, recv_pkg_2,
                         origin_pkg_1=0, origin_pkg_2=0):
        """
        Compute vm break time when live migration
        :param send_pkg_1: eth1 packets send
        :param send_pkg_2: eth2 packets send
        :param recv_pkg_1: eth1 packets receive
        :param recv_pkg_2: eth2 packets receive
        :param origin_pkg_1: packets of eth1 before pktgen send messages
        (when use ifconfig need)
        :param origin_pkg_2: packets of eth2 before pktgen send messages
        (when use ifconfig need)
        :return:
        """
        return ((send_pkg_1 - recv_pkg_1 - origin_pkg_1) +
                (send_pkg_2 - recv_pkg_2 - origin_pkg_2)) / 1000.0

    def __generate_script(self, dpdk_tool_path="tools"):
        self.log.info("generate script")
        test_utils.generate_dpdk_shell_script(
            self.params, ip=self.vm_ip_dpdk,
            dpdk_path=os.path.join(self.dstpath, self.dpdk_version),
            file_path=os.path.join(self.dstpath, self.shell_dpdk),
            dpdk_tool_path=dpdk_tool_path)

        test_utils.generate_pktgen_config_script(
            self.params, ip=self.vm_ip_pktgen,
            mac_addr_eth1=self.eth1_macaddr, mac_addr_eth2=self.eth2_macaddr,
            file_path=os.path.join(self.dstpath, self.setup_pktgen))

        test_utils.generate_pktgen_start_script(
            self.params, ip=self.vm_ip_pktgen,
            file_path=os.path.join(self.dstpath, self.start_pktgen))

    def _volume_operation(self, operation_type, vol_id=None, instance=None):
        if operation_type in 'create':
            # Create volume
            vol_name = 'cloudtest_volume_' + utils_misc.generate_random_string(
                6)
            vol_id = self.volume_utils.create_volume(vol_name, 1)
            status = self.volume_utils.get_volume_status(vol_id)
            self.log.info("The status of volume %s is %s" % (vol_id, status))
            self.volume_id_list.append(vol_id)
            return vol_id
        elif operation_type in 'attach':
            # Attach volume
            self.compute_utils.attach_volume(instance.id, vol_id)
            status = self.volume_utils.get_volume_status(vol_id)
            self.log.info("The status of volume %s is %s" % (vol_id, status))
        elif operation_type in "detach":
            # Detach volume
            self.compute_utils.detach_volume(instance.id, vol_id)
            status = self.volume_utils.get_volume_status(vol_id)
            self.log.info("The status of volume %s is %s" % (vol_id, status))
        elif operation_type in 'delete':
            if not self.volume_utils.delete_volume(vol_id):
                raise exceptions.TestFail("Volume %s cannot be deleted" % vol_id)
        else:
            raise exceptions.TestFail("Volume operation %s is NOT supported." %
                                      type)

    def _install_udp_echo(self, server_ip, client_ip):
        # Copy udpecho_simple to server
        self._copy_udpecho_module_to_instance(server_ip, 'udpecho_simple_server.py')
        # Copy udpping_simple to client
        self._copy_udpecho_module_to_instance(client_ip, 'udpecho_simple_client.py')

    def _copy_udpecho_module_to_instance(self, host_ip, module_name):
        self.log.info('Prepare to copy %s to instance %s.' % (module_name, host_ip))

        self.session = test_utils.wait_for_get_instance_session(self.params, host_ip)
        if not self.session:
            raise exceptions.TestFail("Failed to get session for instance login.")

        local_path = '%s/%s' % \
                     (self.tool_install_path, module_name)
        remote_path = '/home/centos/%s' % module_name
        self.session.copy_file_to(local_path, remote_path)
        self.log.info('Success to copy %s to instance %s.' % (module_name, host_ip))

    def _run_udpecho_module(self, host_ip, module_name, remote_ip, recieve_ip):
        self.log.info('Prepare to run udpecho on %s' % host_ip)

        session = test_utils.wait_for_get_instance_session(self.params, host_ip)
        if not session:
            raise exceptions.TestFail("Failed to get session for instance login.")

        cmd = ''
        cmd += 'cd /home/centos && python %s %s %s >> ' \
               '/home/centos/udpecho.log && cat /home/centos/udpecho.log' \
               % (module_name, remote_ip, recieve_ip)
        self.log.info("Run %s cmd is %s" % (module_name, cmd))

        self.result = session.run(cmd, ignore_status=True)
        self.log.info("udpecho results is %s" % self.result)

    def _ping_and_collect_results(self, local_ip, remote_ip, step, timeout=60):
        self.log.info('Ping %s from %s' % (remote_ip, local_ip))

        session = test_utils.wait_for_get_instance_session(self.params, local_ip)
        if not session:
            raise exceptions.TestFail("Failed to get session for instance login.")

        cmd = 'ping %s -i %s >> /home/centos/ping.log && cat /home/centos/ping.log'\
              % (remote_ip, step)
        self.log.info("Ping cmd is %s" % cmd)
        result = session.run(cmd, ignore_status=False)
        self.ping_msg += result.stdout + '\n' + result.stderr
        self.log.info("Ping results %s" % self.ping_msg)

    def _kill_ping_and_get_results(self, local_ip, tool):
        self.log.info('Kill %s on %s' % (tool, local_ip))

        self.session = test_utils.wait_for_get_instance_session(self.params, local_ip)
        if not self.session:
            raise exceptions.TestFail("Failed to get session for instance login.")

        cmd = 'killall %s' % tool
        result = self.session.run(cmd, ignore_status=True)

        self.log.info("kill results %s" % result)

    def _get_results(self, local_ip, tool, path):
        self.log.info('get %s on %s' % (tool, local_ip))

        cmd = 'cat %s ' % path
        self.result = self.session.run(cmd, ignore_status=True)

        self.log.info("get %s %s" % (tool, self.result))

    def _analyse_udpecho_log(self):
        pat1 = 'TIME OUT (\d+)'
        res = re.findall(pat1, self.result.stdout)[-1]
        self.log.info("Time out is %s" % res)

    def test_live_migrate(self):
        # Create instance1 with cpu pinning
        self.log.info("Create VM with cpu_policy: dedicated, "
                      "cpu_thread_policy: isolate")
        cpu_policy_type = "dedicated"
        instance1 = self._create_vm_and_cpuset(cpu_policy_type)
        private_ip_1 = self.compute_utils.get_private_ip(instance1)
        self.log.info("Instance 1 private ip is %s " % str(private_ip_1))

        # Create volume and attach it to the instance1
        vol_id_1 = self._volume_operation('create')
        self._volume_operation('attach', vol_id=vol_id_1, instance=instance1)

        # Get target host for specified instance live migrate
        target_host = self.compute_utils.get_different_host_from(self.host)
        self.log.info("Get other host is %s" % target_host)

        # Create instance2 with cpu pinning
        instance2 = self._create_vm_and_cpuset(cpu_policy_type)
        private_ip_2 = self.compute_utils.get_private_ip(instance2)
        self.log.info("Instance 2 private ip is %s " % str(private_ip_2))

        # Create volume and attach it to the instance2
        vol_id_2 = self._volume_operation('create')
        self._volume_operation('attach', vol_id=vol_id_2, instance=instance2)

        # Associate floating ip to vm server
        floating_ip_server = \
            self.compute_utils.assign_floating_ip_to_vm(instance1)
        # Associate floating ip to vm client
        floating_ip_client = \
            self.compute_utils.assign_floating_ip_to_vm(instance2)

        self._install_udp_echo(floating_ip_server, floating_ip_client)

        t1 = threading.Thread(target=self._run_udpecho_module,
                              args=(
                                  floating_ip_server,
                                  'udpecho_simple_server.py',
                                  floating_ip_client,
                                  private_ip_1))
        t1.setDaemon(True)
        t1.start()
        time.sleep(10)

        t2 = threading.Thread(target=self._run_udpecho_module,
                              args=(floating_ip_client,
                                    'udpecho_simple_client.py',
                                    floating_ip_server,
                                    private_ip_2))
        t2.setDaemon(True)
        t2.start()
        time.sleep(10)

        # Live migrate on shared storage
        block_migration = self.params.get('block_migration')
        self.compute_utils.live_migrate(instance1.id, target_host,
                                        block_migration)

        self._kill_ping_and_get_results(floating_ip_client,
                                        'python udpecho_simple_client.py'
                                        )
        # self._kill_ping_and_get_results(floating_ip_server,
        # 'python udpecho_simple_server.py')

        time.sleep(20)
        host = \
            self.compute_utils.get_server_host(instance1.name)
        if host != target_host:
            raise exceptions.TestFail("Instance %s failed to live migrate to "
                                      "host %s, the instance is on host %s." %
                                      (instance1.name, target_host, host))

        self._get_results(floating_ip_client, 'udpecho_simple_client',
                          '/home/centos/udpecho.log')
        # self._analyse_udpecho_log()

        # Detach volume from the instance1
        self._volume_operation('detach', vol_id=vol_id_1, instance=instance1)
        # Detach volume from the instance2
        self._volume_operation('detach', vol_id=vol_id_2, instance=instance2)

    def test_live_migrate_dpdk_enabled(self, is_live_migrate=True):
        self.__set_host_name()
        self.__create_net_with_subnet(count=2)
        self.__create_port()
        cpu_policy_type = "dedicated"

        self.__create_flavor_with_cpu_pinning(cpu_type=cpu_policy_type)

        self.vm_dpdk, self.vm_ip_dpdk = self.__create_vm_with_extra_nic(index=0)
        self.vm_pktgen, self.vm_ip_pktgen = self.__create_vm_with_extra_nic(index=1)

        session_dpdk = test_utils.get_host_session(self.params, 'instance',
                                                   self.vm_ip_dpdk)
        session_pktgen = test_utils.get_host_session(self.params, 'instance',
                                                     self.vm_ip_pktgen)
        self.session_list.append(session_dpdk)
        self.session_list.append(session_pktgen)

        self.eth1_macaddr, self.eth2_macaddr = \
            self.__get_nic_macaddr(session_pktgen=session_pktgen)
        if is_live_migrate:
            self.__generate_script()
        else:
            self.__generate_script(dpdk_tool_path="usertools")

        # get ifconfig recv msg before enable pktgen
        ifconfig_msg_before = self.__get_ifconfig_msg(session=session_pktgen)
        # recv pkg num of eth1, eth2
        recv_1_before, recv_2_before = \
            self.__analyse_ifconfig_msg(config_msg=ifconfig_msg_before)

        self.__run_multi_thread()
        if is_live_migrate:
            self.__live_migrate()

        # after complete live migration 10s, stop l2fwd(dpdk) and pktgen
        time.sleep(10)

        # stop l2fwd and pktgen process
        cmd_pid = "ps aux | grep %s | awk '{print $2}'" % self.start_pktgen
        process_str = session_pktgen.run(cmd_pid)
        self.log.info('pktgen str %s' % process_str)
        pktgen_pid = process_str.stdout.split()[0]
        session_pktgen.run("kill -9 %s" % pktgen_pid)

        # get send pkg of eth1 and eth2 after run pktgen
        send_pkg_1, send_pkg_2 = self.__get_send_pkg(session_pktgen=
                                                     session_pktgen)
        # this 10s using for get new data while stop pktgen
        time.sleep(10)
        session_dpdk.run("pkill l2fwd")

        # this 5s using for get msg of l2fwd return
        time.sleep(5)

        ifconfig_msg_after = self.__get_ifconfig_msg(session=session_pktgen)
        # recv pkg num of eth1, eth2 after live migration
        recv_1_after, recv_2_after = \
            self.__analyse_ifconfig_msg(config_msg=ifconfig_msg_after)

        self.log.info("*********TEST RESULT*********")

        self.log.info("send pkt of pktgen eth1: %s; eth2: %s" % (send_pkg_1, send_pkg_2))
        self.log.info("Using ifconfig eth1 recv pkt: %s; eth2 recv pkt: %s"
                      % (recv_1_after, recv_2_after))

        # recv pkg num using dpdk
        recv_dpdk_1, recv_dpdk_2 = self.__analyse_dpdk_data()
        self.log.info("Using dpdk eth1 recv pkt: %s; eth2 recv pkt: %s"
                      % (recv_dpdk_1, recv_dpdk_2))

        self.log.info("*********END*********")

        if is_live_migrate:
            # compute live migration time by ifconfig
            result_ifconfig = self.__compute_result(send_pkg_1=send_pkg_1,
                                                    send_pkg_2=send_pkg_2,
                                                    recv_pkg_1=recv_1_after,
                                                    recv_pkg_2=recv_2_after,
                                                    origin_pkg_1=recv_1_before,
                                                    origin_pkg_2=recv_2_before)
            self.log.info("VM %s live migration time: %ssec while using ifconfig"
                          % (self.vm_dpdk.name, str(result_ifconfig)))

            if result_ifconfig > 0.2:
                raise exceptions.TestFail("VM migration time must under 0.2sec")

            # compute live migration time by dpdk
            result_dpdk = self.__compute_result(send_pkg_1=send_pkg_1,
                                                send_pkg_2=send_pkg_2,
                                                recv_pkg_1=recv_dpdk_1,
                                                recv_pkg_2=recv_dpdk_2)
            self.log.info("VM %s live migration time: %ssec while using DPDK" % (
                self.vm_dpdk.name, str(result_dpdk)))

            if result_dpdk > 0.2:
                raise exceptions.TestFail("VM migration time must under 0.2sec")
        else:
            diff1 = send_pkg_1 - recv_1_after
            diff2 = send_pkg_2- recv_2_after
            self.log.info("Loss %s pkts on eth1" % str(diff1))
            self.log.info("Loss %s pkts on eth2" % str(diff2))
            diff_total = diff1 + diff2
            if diff_total > 0:
                raise exceptions.TestFail("Too many pkts loss, "
                                          "when using different vesion dpdk.")

    def test_dpdk_compatibility(self):
        self.test_live_migrate_dpdk_enabled(is_live_migrate=False)

    def test_cold_migrate(self):
        # Create instance1 with cpu pinning
        self.log.info("Create VM with cpu_policy: dedicated, "
                      "cpu_thread_policy: isolate")
        cpu_policy_type = "dedicated"
        instance1 = self._create_vm_and_cpuset(cpu_policy_type)

        # Create volume and attach it to the instance1
        vol_id_1 = self._volume_operation('create')
        self._volume_operation('attach', vol_id=vol_id_1, instance=instance1)

        # Get target host for specified instance live migrate
        target_host = self.compute_utils.get_different_host_from(self.host)
        self.log.info("Get other host is %s" % target_host)

        # Create instance2 with cpu pinning
        instance2 = self._create_vm_and_cpuset(cpu_policy_type)

        # Create volume and attach it to the instance2
        vol_id_2 = self._volume_operation('create')
        self._volume_operation('attach', vol_id=vol_id_2, instance=instance2)

        # Associate floating ip to remote
        floating_ip_remote = \
            self.compute_utils.assign_floating_ip_to_vm(instance1)
        # Associate floating ip to local
        floating_ip_local = \
            self.compute_utils.assign_floating_ip_to_vm(instance2)

        t1 = threading.Thread(target=self._ping_and_collect_results,
                              args=(floating_ip_local, floating_ip_remote, 1))
        t1.setDaemon(True)
        t1.start()

        time.sleep(10)

        # Migrate on shared storage
        self.compute_utils.cold_migrate(instance1)
        time.sleep(20)

        # Kill ping and get collection
        self._kill_ping_and_get_results(floating_ip_local, 'ping')

        time.sleep(20)
        host = \
            self.compute_utils.get_server_host(instance1.name)
        if host != target_host:
            raise exceptions.TestFail("Instance %s failed to live migrate to "
                                      "host %s, the instance is on host %s." %
                                      (instance1.name, target_host, host))

        self._get_results(floating_ip_local, 'ping', '/home/centos/ping.log')

        # Detach volume from the instance1
        self._volume_operation('detach', vol_id=vol_id_1, instance=instance1)
        # Detach volume from the instance2
        self._volume_operation('detach', vol_id=vol_id_2, instance=instance2)

    def teardown(self):
        for session in self.session_list:
            session.session.close()

        for volume_id in self.volume_id_list:
            self.register_cleanup(resource=volume_id,
                                  res_type='volume')

        # delete port first
        for nic_id in self.nic_id_list:
            self.register_cleanup(resource=nic_id, res_type='port')

        for net_name in self.net_name_list:
            self.register_cleanup(resource=net_name, res_type='network')
            
        super(LiveMigrateTest, self).teardown()

