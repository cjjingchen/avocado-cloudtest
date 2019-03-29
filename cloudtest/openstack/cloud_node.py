# Copyright: Lenovo Inc. 2016~2017
# Author: Yingfu Zhou <zhouyf6@lenovo.com>


import re
import socket
import logging
import time
import random

from avocado.utils import process
from cloudtest.openstack import services
from cloudtest.remote import RemoteRunner


LOG = logging.getLogger('avocado.test')
SIGNAL_CODE = {'SIGSTOP': 19, 'SIGKILL': 9, 'SIGTERM': 15, 'SIGCONT': 18}


class CloudNode(object):
    """
    A base class to define a Cloud Node - controller or compute.
    """
    def __init__(self, host, role=None, status=None, ip=None):
        self.host = host
        self.services = []
        self.remote_runner = None
        setattr(self, "role", role)
        setattr(self, "status", status)
        self.ip = ip

    def __repr__(self):
        return {'host': self.host, 'services': self.cloud_services}

    @property
    def cloud_services(self):
        if self.services:
            return self.services

        # Get all cloud related services/processes running on this node
        cmd = "systemctl status -a --no-pager -H %s" % self.ip
        result = process.run(cmd, shell=True, verbose=False,
                             ignore_status=True)

        for name in services.OPENSTACK_SERVICES:
            if name in result.stdout:
                info = self.get_service_info(name)
                if info:
                    self.services.append(info)
        return self.services

    @property
    def ssh_session(self):
        if self.remote_runner:
            return self.remote_runner

        self.remote_runner = self._get_ssh_session()
        return self.remote_runner

    def get_service_info(self, service_name):
        service_info = {'name': service_name}
        cmd = "ssh root@%s " % self.ip
        cmd1 = cmd + "'systemctl status %s'" % service_name
        result = process.run(cmd1, shell=True, ignore_status=True)
        if result.exit_status != 0:
            LOG.info("Service %s is not active(running)" % service_name)
            return None

        state_regex = "Active: (.*)"
        match = re.findall(state_regex, result.stdout)
        if match:
            service_info['state'] = match[0]

        pid = re.findall(r"Main PID: (\d+)", result.stdout)
        if pid:
            service_info['main_pid'] = pid[0]

        # Get child processes
        cmd2 = cmd + "'ps --ppid=%s -o pid='" % service_info['main_pid']
        child_pids = process.run(cmd2, shell=True, ignore_status=True,
                                 verbose=False)
        service_info['child_pids'] = [p.strip() for p in
                                      child_pids.stdout.split('\n') if p] or []
        return service_info

    def _systemctl_action(self, action):
        cmd = "systemctl -H %s %s" % (self.ip, action)
        result = process.run(cmd, shell=True)
        if result.exit_status != 0:
            LOG.error("Failed to %s node: %s" % (action, self.ip))
        LOG.info("Successfully %s node: %s" % (action, self.ip))

    def soft_reboot(self):
        cmd = "systemctl -H %s reboot" % self.ip
        try:
            process.run(cmd, shell=True, verbose=False, ignore_status=True)
        except Exception, e:
            LOG.error("%s" % e)

    def hard_reboot(self):
        raise NotImplementedError

    def poweroff(self):
        self._systemctl_action('poweroff')

    def panic(self):
        cmd1 = "ssh root@%s \"cat /proc/sys/kernel/sysrq\"" % self.ip
        cmd2 = "ssh root@%s \"echo c | tee /proc/sysrq-trigger\"" % self.ip
        result1 = process.run(cmd1, shell=True, verbose=False, 
                              ignore_status=True)
        if int(result1.stdout) > 0:
            try:
                process.run(cmd2, shell=True, verbose=False,
                            ignore_status=True)
            except Exception, e:
                LOG.error("%s" % e)
        else:
            LOG.info("Kernel does not support sysrq.")

    def act_to_service(self, act, service_name):
        if act == 'start':
            cmd = "systemctl -H %s is-active %s" % (self.ip, service_name)
            state = process.run(cmd, shell=True, ignore_status=True).stdout
            if 'inactive' in state:
                self.__act_to_service_partial(act, service_name)
        else:
            self.__act_to_service_partial(act, service_name)
        if act == 'restart':
            cmd = "systemctl -H %s is-active %s" % (self.ip, service_name)
            state = process.run(cmd, shell=True, ignore_status=True).stdout
            if 'inactive' in state:
                return False
        return True

    def __act_to_service_partial(self, act, service_name):
        cmd = "systemctl -H %s %s %s" % (self.ip, act, service_name)
        result = process.run(cmd, shell=True)
        if result.exit_status != 0:
            LOG.error("Failed to %s service '%s': %s" % (act, service_name,
                                                         result.stderr))
            return False
        LOG.info("Successfully %s service '%s' on '%s'" % (act, service_name,
                                                           self.ip))

    def traffic_control(self, act, br_name, action):
        """
        Using for inject network fault.
        :param act:fault_action
        :param interface_name: 
        :param action: add/change/del
        :return: 
        """
        interface_name = self.get_interface(br_name)
        if act == 'del':
            cmd = "ssh root@%s tc qdisc %s dev %s root" % (self.ip, action, interface_name)
        else:
            cmd = "ssh root@%s tc qdisc %s dev %s root netem %s" \
                % (self.ip, action, interface_name, act)
        result = process.run(cmd, shell=True)
        if result.exit_status != 0:
            LOG.error("Failed to run %s on %s ! : %s"
                      % (act, interface_name, result.stderr))
            return False
        LOG.info("Successfully run %s on %s !"
                 % (act, interface_name))
        return True

    def act_to_network(self, br_name, action):
        """
        Using for inject network fault.
        :param interface_name: 
        :param action: down/up
        :return: 
        """
        interface_name = self.get_interface(br_name)
        cmd_down = "ssh root@%s ip link set %s %s" % (
            self.ip, interface_name, action)
        result = process.run(cmd_down, shell=True)
        if result.exit_status != 0:
            LOG.error("%s network failed on %s! : %s"
                      % (action, interface_name, result.stderr))
            return False
        LOG.info("%s network success on %s!" % (action, interface_name))
        return True

    def get_interface(self, br_name):
        cmd1 = 'ovs-vsctl list-ports %s|grep ^%s' % (br_name, br_name)
        result = self.run_command(cmd1)
        cmd2 = "ovs-vsctl get interface %s options | tr -d '{}'" \
               % result.stdout.strip()
        result = self.run_command(cmd2)
        peer_interface = result.stdout.split('=')[1]
        cmd3 = 'ovs-vsctl port-to-br %s' % peer_interface.strip()
        result = self.run_command(cmd3)
        cmd4 = 'ovs-vsctl list-ports %s | grep ^eth' % result.stdout.strip()
        result = self.run_command(cmd4)
        interface_name = result.stdout
        LOG.info("interface name: %s" % interface_name)
        return interface_name
    
    def act_to_process(self, act, pids):
        rets = []
        for pid in pids:
            cmd = "ssh root@%s 'kill -%s %s' " % (self.ip, SIGNAL_CODE[act], pid)
            result = process.run(cmd, shell=True)
            if result.exit_status != 0:
                LOG.error("Failed to send signal %s to pid '%s': %s" % (act, pid,
                                                                        result.stderr))
                rets.append(False)
            else:
                LOG.info("Successfully send signal %s to pid '%s" % (act, pid))
                rets.append(True)

        if act in 'SIGSTOP':
            LOG.info("Waiting 150 seconds")
            time.sleep(150)
            for pid in pids:
                cmd = "ssh root@%s 'kill -%s %s' " % (self.ip, SIGNAL_CODE["SIGCONT"], pid)
                result = process.run(cmd, shell=True)
                if result.exit_status != 0:
                    LOG.error("Failed to send signal SIGCONT to pid '%s': %s" % (pid,
                                                                                 result.stderr))
                else:
                    LOG.info("Successfully send signal SIGCONT to pid '%s" % pid)

        return all(rets)

    def _iptables_ports_partition(self, act):
        rets = []
        for p in act['port']:
            cmd = "ssh root@%s 'iptables -%s INPUT -s %s -p tcp -m tcp --dport %s -j DROP'" \
                  % (self.host, act['action'], self.host, p)
            result = process.run(cmd, shell=True)
            if result.exit_status != 0:
                LOG.error("Failed to use iptables rule to INPUT chain: %s" % result.stderr)
                rets.append(False)
            else:
                LOG.info("Successfully use iptables rule to INPUT chain!")
                rets.append(True)

            cmd = "ssh root@%s 'iptables -%s OUTPUT -d %s -p tcp -m tcp --sport %s -j DROP'" \
                  % (self.host, act['action'], self.host, p)
            result = process.run(cmd, shell=True)
            if result.exit_status != 0:
                LOG.error("Failed to use iptables rule to OUTPUT chain: %s" % result.stderr)
                rets.append(False)
            else:
                LOG.info("Successfully use iptables rule to OUTPUT chain!")
                rets.append(True)
        return all(rets)

    def act_to_iptables(self, act):
        return self._iptables_ports_partition(act)

    def _get_ssh_session(self):
        return RemoteRunner(host=self.ip, use_key=True)

    def run_command(self, cmd, timeout=10, ignore_status=False):
        """
        Run specified command on this node remotely

        :param cmd: the command to execute
        """
        return self.remote_runner.run(cmd, timeout=timeout,
                                      ignore_status=ignore_status)
   
    def find_pci_devices(self, search_string=None):
        """
        List PCI devices according to search string and return its bus info

        :param search_string: the string for filter
        """
        cmd = 'lspci'
        if search_string:
            cmd += ' | grep -v "virtual" | grep %s' % search_string
        cmd += ' | cut -d " " -f1'
        result = self.run_command(cmd)
        if result.stdout:
            return result.stdout.splitlines()
        return []

    def is_pci_support_sriov(self, pci_id):
        result = self.run_command("lspci -vv -s %s | grep SR-IOV" % pci_id)
        return result.exit_code and result.stdout

    def get_all_physical_nics(self):
        cmd = 'ip link show | grep -E " eth[0-9]" | cut -d":" -f2'
        return [x.strip() for x in self.run_command(cmd).stdout.splitlines()]

    def find_sriov_nic(self, select_policy='first'):
        """
        Find pci NICs which support SR-IOV and return a NIC name
        according to select policy ('auto', 'first')

        :param select_policy: the policy to select, 'auto', 'first'
        """
        sr_iov_devs = []
        pci_id = None

        pci_devs = self.find_pci_devices('Ethernet Controller')
        for dev in pci_devs:
            if self.is_pci_support_sriov(dev):
                sr_iov_devs.append(dev)
        if select_policy == 'first':
            pci_id = sr_iov_devs[0]
        elif select_policy == 'auto':
            pci_id = sr_iov_devs[random.randomrange(len(sr_iov_devs))]
        else:
            LOG.error("Invalid select policy")

        if pci_id is not None:
            all_nics = self.get_all_physical_nics()
            for nic in all_nics:
                output = self.run_command('ethtool -i %s' % nic).stdout
                if pci_id in output:
                    LOG.info("Found device: %s => %s" % (pci_id, nic))
                    return (pci_id, nic)
        LOG.error("Failed to find SR-IOV nic")

    def setup_srvio(self, vf_num):
        """
        Set up SR-IOV on compute node.

        :param vf_num: the number of VFs to create
        """
        nic = self.find_sriov_nic()
        bus_number = nic[0].split(':')[0]
        cmd = 'echo %d > /sys/class/net/%s/device/sriov_numvfs' % (
                                                  vf_num, nic[1])
        self.run_command(cmd)

        find_vf_cmd = "lspci | grep '%s:' | grep 'Virtual Function'" % (
                                                             bus_number)
        result = self.run_command(find_vf_cmd)
        if result.exit_code != 0 or not result.stdout:
            LOG.error("Failed to setup SR-IOV dev: %s" % nic)
            return False
        LOG.info("Successfully setted up SR-IOV dev: %s" % nic)
        

if __name__ == '__main__':
    node = CloudNode('10.20.0.5')
    print node.ip
    for s in node.cloud_services:
        print '=== service info ==='
        for k, v in s.iteritems():
            print "%s : %s" % (k, v)
