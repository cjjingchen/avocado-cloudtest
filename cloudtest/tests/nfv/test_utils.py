# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Lenovo Inc. 2017
# Author: Yingfu Zhou <zhouyf6@lenovo.com>


import random
import logging
import re
import os
import time

from avocado.core import exceptions
from avocado.utils import process
from cloudtest import data_dir
from cloudtest.openstack.compute import Compute
from cloudtest.openstack.network import Network
from cloudtest.openstack.keystone import Keystone
from cloudtest import remote
from cloudtest import utils_misc
from cloudtest.remote import RemoteRunner


LOG = logging.getLogger('avocado.test')


def create_vm_and_wait_for_login(params):
    """
    Create a new VM and wait for ssh login.

    :param params: the dict of parameters from config file
    :returns: nova server instance
    """
    compute_utils = Compute(params)

    image_login_user = params.get('image_ssh_username', 'root')
    login_benchmark = int(params.get('timeout_for_creation', '360'))
    extra_spec = {"hw:cpu_policy": "dedicated", "hw:cpu_thread_policy": "isolate"}

    flavor_name = compute_utils.create_flavor(extra_spec=extra_spec).name
    vm_name = params.get('vm_name')

    vm = compute_utils.create_vm(vm_name=vm_name,
                                 image_name=params.get('image_name'),
                                 #flavor_name=params.get('flavor_name'),
                                 flavor_name=flavor_name,
                                 network_name=params.get('network_name'),
                                 injected_key=None, sec_group=None)

    if not compute_utils.wait_for_vm_active(vm):
        raise exceptions.TestFail("Failed to build VM: %s" % vm)

    vm_ip = compute_utils.assign_floating_ip_to_vm(vm)
    LOG.info("Created VM '%s', try to login via %s" % (vm_name, vm_ip))

    def _check_vm_responsive():
        try:
            cmd = params.get('test_vm_responsive_cmd', 'hostname')
            ssh_cmd = "ssh -i ~/.ssh/id_rsa -o UserKnownHostsFile=/dev/null"
            ssh_cmd += " -o StrictHostKeyChecking=no -p 22 "
            ssh_cmd += "%s@%s '%s'" % (image_login_user, vm_ip, cmd)
            result = process.run(ssh_cmd, timeout=2, ignore_status=True)
            if image_login_user in result.stdout:
                return True
            return False
        except Exception, e:
            msg = "Exception happened during execute cmd within vm: %s" % e
            LOG.error(msg)
            return False

    if not utils_misc.wait_for(_check_vm_responsive, login_benchmark,
                        text='Check execute command within VM'):
        raise exceptions.TestFail('Failed to run command within VM')

    return True


def get_node_vm_count_dict(params):
    compute_utils = Compute(params)
    vm_count_dict = compute_utils.get_host_vm_count()
    LOG.info("VM count for each host: %s" % vm_count_dict)
    return vm_count_dict


def get_test_network(params):
    """
    Check if the network in config file is ready for use. If not, create one.

    :param params: the dict parameters from config file
    """
    network_utils = Network(params)
    net_name = params.get('network_name', 'cloudtest_net')
    net = network_utils.get_network(net_name)
    if not net:
        LOG.info('Try to create network: %s' % net_name)
        network_utils.create_network(name=net_name, subnet=True,
                                     start_cidr='192.168.0.0/24')
        net = network_utils.get_network(net_name)
        network_utils.create_router('cloudtest_router', external_gw=True,
                                    subnet_name=net_name + '_subnet')
        router_id = network_utils.get_router_id('cloudtest_router')
        cmd = 'openstack router add subnet %s %s' % (router_id, net['subnets'][0])
        process.run(cmd)
    return net


def create_ports(params):
    network_utils = Network(params)
    vnic_count = int(params.get('vnics_count_per_vm', 1))
    vnics = []
    net = get_test_network(params)
    _network_id = str(net["id"])
    name_prefix = 'cloudtest_' + utils_misc.generate_random_string(6)
    for i in range(0, vnic_count):
        nic_name = name_prefix + '_%d' % i
        port = network_utils.create_port(nic_name,
                                         network_id=_network_id)
        LOG.info("Created port successfully!")
        vnics.append(port)
    return vnics


def wait_for_vm_pingable(session, vm_ip, timeout=60):

    def __check_vm_pingable():
        try:
            cmd = 'ping -c 1 %s' % vm_ip
            stdout_msg = session.run(cmd, timeout=timeout, ignore_status=True)
            LOG.info(stdout_msg.stdout)
            pat = '(\d+).*? received'
            result = re.findall(pat, str(stdout_msg))
            if not len(result):
                LOG.info("VM[%s] is not pingable" % vm_ip)
                return False
            else:
                value = int(result[0])
                if value:
                    return True
        except Exception, e:
            msg = "Exception happened during ping vm: %s" % e
            LOG.error(msg)
            return False

    if not utils_misc.wait_for(__check_vm_pingable, timeout,
                               text='Check vm pingable'):
        LOG.error("VM[%s] is not pingable within %d(s)" % (vm_ip, timeout))
        return False
    return True


def wait_for_cmd_execution_within_vm(session, cmd, expected_result, timeout=60):
    LOG.info("Waiting for cmd[%s] execution within vm" % cmd)

    def __check_cmd_execution():
        try:
            stdout_msg = session.run(cmd, timeout=10, ignore_status=True)
            LOG.info(stdout_msg.stdout.split('\n')[0])
            if not isinstance(expected_result, int):
                if expected_result.lower() in stdout_msg.stdout:
                    LOG.info("Successfully execute cmd[%s] within vm \n" % cmd)
                    return True
            else:
                restart_time = stdout_msg.stdout.split('\n')[0].split(' ')[0]
                LOG.debug('System start time: %s' % restart_time)
                LOG.debug('Test start time: %s' % (time.time() - expected_result))
                if float(restart_time) < float(time.time() - expected_result):
                    return True
                else:
                    return False
            LOG.info("Failed to execute cmd[%s] within vm" % cmd)
            return False
        except Exception, e:
            msg = "Exception happened during execute cmd within vm: %s" % e
            LOG.error(msg)
            return False

    if not utils_misc.wait_for(__check_cmd_execution, timeout,
                               text='Check execute command within VM'):
        LOG.error("Failed to execute cmd[%s] within %d(s)" % (cmd, timeout))
        return False
    return True


def create_vm_with_cpu_pinning_and_wait_for_login(params, name,
                                                  injected_key=None, ram=None,
                                                  vcpus=None, disk=None,
                                                  flavor_name=None,
                                                  **kwargs):
    """
    Create a new VM and wait for ssh login.

    :param params: the dict of parameters from config file
    :returns: nova server instance
    """
    compute_utils = Compute(params)

    image_login_user = params.get('image_ssh_username', 'root')
    login_benchmark = int(params.get('timeout_for_creation', '360'))

    if flavor_name == None:
        flavor_name = compute_utils.create_flavor(ram=ram, vcpus=vcpus,
                                                  disk=disk,
                                                  extra_spec=kwargs).name

    vm = compute_utils.create_vm(vm_name=name,
                                 image_name=params.get('image_name'),
                                 flavor_name=flavor_name,
                                 network_name=params.get('network_name', 'share_net'),
                                 injected_key=injected_key, sec_group=None)


    if not compute_utils.wait_for_vm_active(vm):
        raise exceptions.TestFail("Failed to build VM: %s" % vm)

    return vm


def check_cpuset(instance_name, host, type, controller_session):
    ssh_cmd = "ssh -q %s -t " % host
    cmd = 'virsh dumpxml %s|grep cpuset|grep vcpu' % instance_name
    result = controller_session.run(ssh_cmd+cmd)
    LOG.info("result stdout is %s" % result.stdout)
    pat = "(?<=<)(.+?)(?=/>)"
    cpusets = re.findall(pat, result.stdout)
    cpu_list = []
    def verify_cpu_policy(type, cpuset):
        if type == "dedicated":
            if cpuset.isdigit():
                cpu_list.append(int(cpuset))
                return True
            else:
                return False

        if type == "shared":
            if not cpuset.find('-') == -1:
                if not cpuset.find(',') == -1:
                    shared_cpus = re.split(' |,|-', cpuset)
                else:
                    shared_cpus = cpuset.split('-')
                for cpu in shared_cpus:
                    if not cpu.isdigit():
                        return False
                return True

            else:
                return False

    for cpuset in cpusets:
        LOG.info("cpuset is %s" % cpuset)
        cpu = cpuset[cpuset.find("cpuset='") + len("cpuset='"):len(cpuset) - 1]
        if not verify_cpu_policy(type, cpu):
            raise exceptions.TestFail('%s: cpu policy is %s, cpuset is %s.' %
                                      (instance_name, type, cpuset))

    return True, cpu_list


def check_vm_cpu_isolation(host, controller_session, dpdk_core_list=[]):
    """
    :param host: compute node ip
    :param controller_session:
    :param dpdk_core_list: cores used by dpdk
    :return:
    """
    ssh_cmd = "ssh -q %s -t " % host
    cmd = "virsh list|grep instance|awk '{print $2}'"
    result = controller_session.run(ssh_cmd+cmd)
    instance_list = result.stdout.split("\n")
    LOG.info("result stdout is %s" % result.stdout)

    cpuset_list = []
    if dpdk_core_list:
        cpuset_list.extend(dpdk_core_list)

    for instance in instance_list:
        if instance.strip() == "":
            break
        cmd = "virsh dumpxml %s|grep vcpupin" % instance
        result = controller_session.run(ssh_cmd + cmd)
        LOG.info("result stdout is %s" % result.stdout)
        pat = "(?<=<)(.+?)(?=/>)"
        cpusets = re.findall(pat, result.stdout)

        for cpuset in cpusets:
            LOG.info("cpuset is %s" % cpuset)
            cpu = cpuset[cpuset.find("cpuset='") +
                         len("cpuset='"):len(cpuset) - 1]
            if cpu.find(',') == -1 and cpu.find('-') == -1:
                if cpu in cpuset_list:
                    raise exceptions.TestFail('cpu_thread_policy is isolate, '
                                          'cpuset=%s is duplicated in host %s.'
                                          %(cpu, host))
                else:
                    cpuset_list.append(cpu)

    return True


def get_numa_count(host, controller_session):
    ssh_cmd = "ssh -q %s -t " % host
    cmd = "lscpu | grep NUMA"
    result = controller_session.run(ssh_cmd + cmd)
    numa_line_list = result.stdout.split("\n")
    numa_count = re.findall(r"\d+", numa_line_list[0])

    return int(numa_count[0])


def check_numa_pinning(instance_name, host, numa_count, controller_session):
    ssh_cmd = "ssh -q %s -t " % host
    cmd = 'virsh dumpxml %s|grep memAccess' % instance_name
    result = controller_session.run(ssh_cmd + cmd)
    LOG.info("result stdout is %s" % result.stdout)
    pat = "(?<=<)(.+?)(?=/>)"
    numa_lines = re.findall(pat, result.stdout)
    cpu_list = []

    def verify_cpu(cpu, numa_count):
        if not cpu.isdigit():
            return False
        elif int(cpu) < 0:
            return False
        elif int(cpu) > (numa_count - 1):
            return False
        elif cpu in cpu_list:
            return False
        else:
            cpu_list.append(cpu)
            return True

    numa_bit = 1
    numa_bit += numa_count/10
    i = 0
    for numa_line in numa_lines:
        LOG.info("numa line is %s" % numa_line)
        i += 1
        if i > numa_count:
            raise exceptions.TestFail("Numa count is %s totally, "
                                      "current numa number is %s." %
                                      (numa_count, i))
        cpu = numa_line[numa_line.find("cpus='") + len("cpus='"):
        numa_line.find("cpus='") + len("cpus='") + numa_bit]
        if not verify_cpu(cpu, int(numa_count)):
            raise exceptions.TestFail('%s: numa count is %s, current cpus is %s.' %
                                      (instance_name, numa_count, cpu))


def run_test_within_vm(params, vm_name, test_name, cmd):
    """
    Run specified test program within vm.

    :param params: the dict of params from config file
    :param vm_name: the name of the VM to run program
    :param test_name: the test tar ball name, any test like
                      'fio-2.14.tar.gz' in cloudtest/tests/common
    :param cmd: the command to run within vm
    """

    compute_utils = Compute(params)
    vm = compute_utils.find_vm_from_name(vm_name)
    fip = [address for address in vm.addresses.values()[0]
               if address[u'OS-EXT-IPS:type'] == u'floating']
    if fip:
        fip = fip[0]
    else:
        raise exceptions.TestError("No floating ip for VM %s" % vm_name)

    session = remote.RemoteRunner(host=fip, use_key=True)
    src_tarball = os.path.join(data_dir.CLOUDTEST_TEST_DIR,
                               'common/%s' % test_name)
    session.copy_file_to(src_tarball, '/root/')
    session.run('cd /root/ && tar zxvf %s' % test_name)
    return session.run(cmd)


def get_ha_protect_service_info(host_ip, host_password, config_path, master=True):
    session = RemoteRunner(client='ssh', host=host_ip, username="root",
                           port="22", password=host_password)
    cmd = "ls %s|grep -E 'nova|neutron|rabbitmq|keystone' " % config_path
    result = session.run(cmd)
    config_files = result.stdout.split("\n")
    LOG.info("Haproxy config file list: %s" % config_files)
    if len(config_files) < 2:
        config_file = config_files[0]
    else:
        config_file = config_files[random.randint(0, len(config_files)-2)]
    cmd = "grep 'listen' %s%s" % (config_path, config_file)
    result = session.run(cmd)
    service_name = result.stdout.split(' ')[1]
    tmp = re.findall(r'-\d+', service_name)
    if tmp:
        service_name = service_name.split(tmp[0])[0]
    cmd = "grep 'server' %s%s" % (config_path, config_file)
    result = session.run(cmd)
    LOG.info("Service info : %s" % result.stdout)
    info_list = re.findall(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
                              r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
                              result.stdout)
    if master:
        info = info_list[0]
    else:
        info = info_list[1]
    LOG.info("Service info: %s, %s" % (service_name, info))
    return service_name.strip(), info


def act_to_service(session, service_name, action):
    cmd = "systemctl list-unit-files --type=service | grep %s" % service_name
    result = session.run(cmd)
    service_full_name = result.stdout.split(' ')[0]
    start_time = time.time()
    LOG.info("Try to %s %s" % (action, service_full_name))
    ret = True
    if action in ['restart', 'stop', 'start']:
        cmd = "systemctl %s %s" % (action, service_full_name)
        result = session.run(cmd, ignore_status=True)
        if result.exit_status != 0:
            ret = False
    else:
        ret = act_to_process(session, action, service_full_name)

    cost_time = time.time() - start_time
    if ret:
        LOG.info("%s service successfully, costed %d(s)" % (action, cost_time))
    else:
        raise exceptions.TestFail("Failed to %s service %s" % (action, service_name))


def get_service_pid(session, service_name):
    cmd = "systemctl status %s" % service_name
    result = session.run(cmd, ignore_status=True)
    if result.exit_status != 0:
        return None
    LOG.info("Service info: %s" % result.stdout)
    pids = re.findall(r"Main PID: (\d+)", result.stdout)
    if len(pids) > 0:
        return pids[0]


def act_to_process(session, act, service_name):
    SIGNAL_CODE = {'SIGSTOP': 19, 'SIGKILL': 9, 'SIGTERM': 15, 'SIGCONT': 18}
    ret = False
    pid = get_service_pid(session, service_name)
    if not pid:
        LOG.error("Failed to get pid of service: %s" % service_name)
        return ret

    cmd = "kill -%s %s" % (SIGNAL_CODE[act], pid)
    LOG.info("Act to process: %s" % cmd)
    result = session.run(cmd, ignore_status=True)
    if result.exit_status != 0:
        LOG.error("Failed to send signal %s to pid '%s': %s" % (act, pid,
                                                                result.stderr))
        ret = False
    else:
        LOG.info("Successfully send signal %s to pid %s" % (act, pid))
        ret = True

    if act in 'SIGSTOP':
        LOG.info("Waiting 150 seconds")
        time.sleep(150)
        cmd = "kill -%s %s" % (SIGNAL_CODE["SIGCONT"], pid)
        result = session.run(cmd, ignore_status=True)
        if result.exit_status != 0:
            LOG.error("Failed to send signal SIGCONT to pid '%s': %s" % (pid,
                                                                         result.stderr))
        else:
            LOG.info("Successfully send signal SIGCONT to pid '%s" % pid)

    return ret


def check_ping_msg(vm, msg, ping_count):
    """
    Using for compute vm recovery time(after inject fault, how long can ping).
    the interval of ping should be 1s
    :param vm: vm object
    :param msg: get this msg after ping ping_count times
    :param ping_count: the count of ping
    """
    pat = '(\d+) received'
    msg = re.findall(pat, str(msg))
    if not len(msg):
        raise exceptions.TestFail('Msg data or pattern error, '
                                  'please check!')
    else:
        value = int(msg[0])
        if value:
            recovery_time = int(ping_count) - value
            LOG.info('After inject fault, VM %s can ping after %s s' %
                     (vm.name, str(recovery_time)))


def get_host_session(params, host_type, host_ip=None):
    user_name = ""
    password = ""
    session = None

    try:
        if host_type in "controller":
            user_name = params.get('controller_username')
            password = params.get('controller_password')
            host_ip = host_ip or params.get('controller_ip')

            if params.get("controller_ssh_login_method") in "password":
                LOG.info("Try to log into %s[%s@%s] via password" % (host_type,
                                                                     user_name,
                                                                     host_ip))
                session = remote.RemoteRunner(client='ssh', host=host_ip,
                                              username=user_name, port='22',
                                              password=password)
            else:
                LOG.info("Try to log into %s[%s@%s] via key" % (host_type,
                                                                user_name,
                                                                host_ip))
                session = remote.RemoteRunner(client='ssh', host=host_ip,
                                              username=user_name, port='22',
                                              use_key=True)
        elif host_type in "instance":
            if not host_ip:
                raise exceptions.TestError("Instance IP address is not specified")
            user_name = params.get('image_ssh_username', 'root')
            password = params.get('image_ssh_password', 'root')

            if params.get("image_ssh_auth_method") in "password":
                LOG.info("Try to log into %s[%s@%s] via password" %
                         (host_type, user_name, host_ip))
                session = remote.RemoteRunner(client='ssh', host=host_ip,
                                              username=user_name, port='22',
                                              password=password)
            else:
                LOG.info("Try to log into %s[%s@%s] via key" %
                         (host_type, user_name, host_ip))
                session = remote.RemoteRunner(client='ssh', host=host_ip,
                                              username=user_name, port='22',
                                              use_key=True)

    except Exception as e:
        LOG.error('Failed to ssh login to VM %s, capturing console log...' % host_ip)
        if host_type in "instance":
            compute_utils = Compute(params)
            _vm = compute_utils.get_vm_by_ip(host_ip)
            compute_utils.capture_vm_console_log(_vm)
        raise exceptions.TestFail('Failed to ssh login to VM: %s' % str(e))

    if not session.session.is_responsive():
        LOG.error('Failed to ssh log into VM %s, capturing console log...' % host_ip)
        if host_type in "instance":
            compute_utils = Compute(params)
            _vm = compute_utils.get_vm_by_ip(host_ip)
            compute_utils.capture_vm_console_log(_vm)
    else:
        LOG.info('Login successfully!')
    return session


def wait_for_get_instance_session(params, host_ip, step=3.0, timeout=120):
    LOG.info("Wait for get session without in %s " % timeout)

    start_time = time.time()
    end_time = start_time + float(timeout)

    while time.time() < end_time:
        session = get_host_session(params, 'instance', host_ip)

        if session is not None:
            return session

        time.sleep(step)

def check_vms_connectivity(params, net_name, vms_list, session=None,
                           floatingip=None):
    """
    Check the connectivity of given VMs in given network.

    :param session: the ssh session, if None, you must specify floatingip
    :param floatingip: the floatingip to connect to the master vm
    :param ssh_username: username to connect to master vm
    :param ssh_password: ssh password
    :param net_name: the network name to check
    :param vms_list: the list of VMs

    :return: bool object
    """
    compute_utils = Compute(params)

    if session is None:
       session = remote.RemoteRunner(host=floatingip,
                                     username=params.get('image_ssh_username'),
                                     password=params.get('image_ssh_password'))

    results = []
    for vm in vms_list:
        vm = compute_utils.find_vm_from_name(vm.name)
        if not vm.addresses:
            raise exceptions.TestFail("VM %s has no valid IP address" % vm.name)

        pri_ip = vm.addresses[net_name][0]['addr']
        LOG.info('Try to ping vm: %s' % pri_ip)
        result = session.run('ping -c 10 %s' % pri_ip, ignore_status=False)
        res = (result.exit_status == 0) and ('10 received' in result.stdout)
        LOG.info("Result of ping vm '%s': %s" % (pri_ip, res))
        LOG.info('STDOUT: %s' % result.stdout)
        results.append(res)
    if not any(results):
        return False
    LOG.info('Ping all VMs successfully')
    return True


def get_tenant_id(params, tenant_name):
    keystone_utils = Keystone(params)
    tenant = keystone_utils.get_tenant(tenant_name)
    if not tenant:
        LOG.error("Failed to get tenant id for '%s'" % tenant_name)
        return ""
    LOG.info("Got tenant ID for tenant %s: %s" % (tenant_name, tenant.id))
    return tenant.id


def generate_dpdk_shell_script(params, ip, dpdk_path, file_path,
                               dpdk_tool_path="tools"):
    """
    Enable DPDK on vm_dpdk
    :param ip: floating ip of vm_dpdk
    :param dpdk_path: /root/dpdk-stable-16.11.2
    :return:
    """
    cmd = """
cat >>%s<<EOF
export RTE_SDK=%s
export RTE_TARGET=x86_64-native-linuxapp-gcc
modprobe uio
insmod %s/x86_64-native-linuxapp-gcc/kmod/igb_uio.ko
cd %s/%s
./dpdk-devbind.py --bind=igb_uio eth1 eth2
if [ ! -d "/mnt/huge" ]; then mkdir /mnt/huge; fi
mount -t hugetlbfs nodev /mnt/huge/
echo 512 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
cd %s/examples/l2fwd/build
./l2fwd -c 7 -n 4 -- -p 0x3
EOF
    """ % (file_path, dpdk_path, dpdk_path, dpdk_path,
           dpdk_tool_path, dpdk_path)
    session = get_host_session(params, 'instance', ip)
    session.run(cmd)


def generate_pktgen_config_script(params, ip, mac_addr_eth1,
                                  mac_addr_eth2, file_path):
    """
    Using linux pktgen send data
    :param ip: floating ip of vm_pktgen
    :return:
    """
    cmd = """
cat >>%s<<EOF
modprobe pktgen
cd /proc/net/pktgen
echo rem_device_all > kpktgend_0
echo rem_device_all > kpktgend_1
echo rem_device_all > kpktgend_2
echo add_device eth1 > kpktgend_0
echo add_device eth2 > kpktgend_2
echo count 0 > eth1
echo count 0 > eth2
echo clone_skb 1000 > eth1
echo clone_skb 1000 > eth2
echo ratep 1000 > eth1
echo ratep 1000 > eth2
echo pkt_size 256 > eth1
echo pkt_size 256 > eth2
echo dst_mac %s > eth1
echo dst_mac %s > eth2
EOF
    """ % (file_path, mac_addr_eth2, mac_addr_eth1)
    session = get_host_session(params, 'instance', ip)
    session.run(cmd)


def generate_pktgen_start_script(params, ip, file_path):
    cmd = """
cat >>%s<<EOF
echo start > /proc/net/pktgen/pgctrl
EOF
    """ % file_path
    session = get_host_session(params, 'instance', ip)
    session.run(cmd)


