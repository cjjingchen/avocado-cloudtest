import logging
import time
import random
from cloudtest import utils_misc
from avocado.core import exceptions
from cloudtest.openstack import compute
from cloudtest.tests.nfv import test_utils
from cloudtest.remote import RemoteRunner
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


LOG = logging.getLogger('avocado.test')


class NicBondingTest(NFVTestBase):
    def __init__(self, params, env):
        super(NicBondingTest, self).__init__(params, env)
        self.compute_utils = compute.Compute(self.params)
        self.hypervisors_client = self.compute_utils.novaclient.hypervisors

    def setup(self):
        self.vm_1_name = 'cloudtest_' + utils_misc.generate_random_string(6)
        self.vm_2_name = 'cloudtest_' + utils_misc.generate_random_string(6)

        LOG.info("Try to get two compute nodes")
        hyors = self.compute_utils.novaclient.hypervisors.list()
        if len(hyors) < 2:
            raise exceptions.TestSetupFail("Failed to get enough compute nodes")
        hyors_index = self.get_randomindex(len(hyors), 2)
        LOG.info("Try to get compute node ip.")
        computenode_ip = self.get_computenode_ip(
            hyors[hyors_index[0]]._info["service"]["host"])
        LOG.info("Got compute node ip :%s" % computenode_ip)
        self.session_computenode = self.get_session_computenode(computenode_ip,
                                                               usekey=True)

        LOG.info("To check if it supports nic bonding")
        self.nicbonding = self.get_nic_bonding(self.session_computenode)

        if self.nicbonding is None:
            raise exceptions.TestSkipError("Did not find bonding nic, "
                                           "skip the test")
        else:
            LOG.info("Got a bonding nic %s" % self.nicbonding)
            self.vm1 = self.create_vm_with_az(self.vm_1_name,
                               hyors[hyors_index[0]]._info["service"]["host"])
            self.register_cleanup(self.vm1)
            self.vm2 = self.create_vm_with_az(self.vm_2_name,
                               hyors[hyors_index[1]]._info["service"]["host"])
            self.register_cleanup(self.vm2)
            self.compute_utils.assign_floating_ip_to_vm(self.vm1)
            self.compute_utils.assign_floating_ip_to_vm(self.vm2)
            self.ipaddr_1 = self.compute_utils.get_vm_ipaddr(self.vm_1_name)
            self.ipaddr_2 = self.compute_utils.get_vm_ipaddr(self.vm_2_name)
            time.sleep(10)
            self.session_vm = test_utils.get_host_session(self.params,
                                                          'instance',
                                                          self.ipaddr_1["floating"])
            checkpath = "/etc/sysconfig/network-scripts"
            self.nics = self.get_eths_forbonded(self.session_computenode, checkpath,
                                           self.nicbonding)
            if len(self.nics) == 0:
                raise exceptions.TestSetupFail("Failed to get bonded nic")
            LOG.info("%s bonded to be %s" % (self.nics, self.nicbonding))

    def create_vm_with_az(self, vm_name, hyor):
        host_zone = self.compute_utils.get_host_by_name(
            host_name=hyor).zone
        az = '%s:%s' % (host_zone, hyor)
        vm = self.compute_utils.create_vm(vm_name=vm_name,
                                     image_name=self.params["image_name"],
                                     flavor_name=self.params["flavor_name"],
                                     network_name=self.params["network_name"],
                                     injected_key=None, sec_group=None,
                                     availability_zone=az)
        vm_created = self.compute_utils.wait_for_vm_active(vm, 1,
                                    int(self.params["vmtobeactive_timeout"]))
        if vm_created == False:
            raise exceptions.TestSetupFail("Quit for creating vm timeout")
        return vm

    def get_randomindex(self, _range, _count):
        _ranges = range(_range)
        random.shuffle(_ranges)
        return [_ranges[0], _ranges[1]]

    def get_computenode_ip(self, computenode_name):
        hysors = self.compute_utils.get_all_hypervisors()
        for hy in hysors:
            if hy.hypervisor_hostname == computenode_name:
                return hy.host_ip

    def get_session_computenode(self, ip, usekey=False):
        session_node = RemoteRunner(client='ssh', host=ip,
                              username=self.params["openstack_ssh_username"],
                              port="22",
                              password=self.params["openstack_ssh_password"],
                              use_key=usekey,
                              timeout=int(self.params["session_timeout"]))
        return session_node

    def get_nic_bonding(self, session):
        cmd_1 = ("ifconfig | grep ^bond | awk -F: '{print $1}' ")
        run_result = session.run(cmd_1)
        if len(run_result.stdout) > 0:
            nics = run_result.stdout.split("\n")
            return nics[0]
        else:
            return None

    def get_eths_forbonded(self, session, checkpath, nicbonding):
        nics = []
        cmd_1 = ("ls %s/ifcfg-*" % checkpath)
        run_result_1 = session.run(cmd_1, ignore_status=True)
        if run_result_1.exit_status == 0 and len(run_result_1.stdout) > 0:
            ifcfgs = run_result_1.stdout.split("\n")
            for cfg in ifcfgs:
                if len(cfg) > 0:
                    cmd_2 = ("grep  MASTER=%s %s" % (nicbonding, cfg))
                    run_result_2 = session.run(cmd_2, ignore_status=True)
                    if len(run_result_2.stdout) > 0:
                        cmd_3 = ("grep DEVICE= %s | awk -F= '{print $2}'"
                                 % cfg)
                        run_result_3 = session.run(cmd_3)
                        nic = run_result_3.stdout.replace(" ","")
                        nic = nic.replace("\n","")
                        nics.append(nic)
        return nics

    def nic_down(self, session, nic):
        cmd = ("ifdown %s" % nic)
        run_result = session.run(cmd, ignore_status=True)
        return run_result.exit_status

    def nic_up(self, session, nic):
        cmd = ("ifup %s" % nic)
        run_result = session.run(cmd, ignore_status=True)
        return run_result.exit_status

    def test(self):
        if self.nic_down(self.session_computenode, self.nics[0]) != 0:
            raise exceptions.TestError("Failed to shut down %s." %
                                       self.nics[0])
        LOG.info("Shuted down %s" % self.nics[0])
        cmd = ("ping -c 10 %s" % self.ipaddr_2["fixed"])
        LOG.info("To verity if one VM can reach another VM "
                 "after shutting down the bonding nic")
        run_result = self.session_vm.run(cmd)
        if run_result.exit_status != 0:
            raise exceptions.TestFail("VM can not reach another one "
                                      "after shutting down the bonding nic")

    def teardown(self):
        if self.nic_up(self.session_computenode, self.nics[0]) != 0:
            logging.warn("Failed to activate %s" % self.nics[0])
        else:
            LOG.info("Activated %s" % self.nics[0])
        super(NicBondingTest, self).teardown()


