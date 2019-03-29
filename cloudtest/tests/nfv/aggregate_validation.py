#!/usr/bin/env python
# coding=utf-8

import logging
from cloudtest import utils_misc
from avocado.core import exceptions
from cloudtest.openstack import compute
from cloudtest.openstack import volume
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


LOG = logging.getLogger('avocado.test')


class AggregateValidation(NFVTestBase):
    def __init__(self, params, env):
        super(AggregateValidation, self).__init__(params, env)
        self.compute_utils = compute.Compute(self.params)
        self.volume_utils = volume.Volume(self.params)
        self.hypervisors_client = self.compute_utils.novaclient.hypervisors
        self.cleanup_aggregate = False
        self.cleanup_aggregate_host = False

    def setup(self):
        self.aggregate_name = "cloudtest_aggregate_" + \
                              utils_misc.generate_random_string(6)
        self.host_zone = "cloudtest_az_" + \
                              utils_misc.generate_random_string(6)
        self.flavor_name = self.params["flavor_name"]
        self.vmtobeactive_timeout = int(self.params["vmtobeactive_timeout"])
        self.computenodes_name = []
        self.availability_zone = None
        self.aggregate = None

        hypervisors = self.compute_utils.get_all_hypervisors()
        LOG.debug("hypervisors: %s" % hypervisors)
        if len(hypervisors) >= 2:
            for i in range(2):
                self.computenodes_name.append(hypervisors[i].hypervisor_hostname)
        else:
            raise exceptions.TestSetupFail(
                "No enough hypervisor to create aggregate")
        LOG.debug("Got computes :%s" % self.computenodes_name)

        self.availability_zone = self.host_zone

        aggregates = self.compute_utils.novaclient.aggregates.list()
        LOG.debug("Aggregate have had:%s" % aggregates)
        for ag in aggregates:
            LOG.debug("ag:%s" % ag)
            for host in ag.hosts:
                LOG.debug("host:%s" % host)
                for computenode_name in self.computenodes_name:
                    LOG.debug("computenode_name:%s" % computenode_name)
                    if host == computenode_name:
                        LOG.debug("host:%s belongs other aggregate" % host)
                        raise exceptions.TestSetupFail(
                            "Failed to add host %s to a new aggregate, "
                            "it already belongs to other" %
                            computenode_name)
        LOG.info("Create a new aggregate %s with availability zone %s"
                 % (self.aggregate_name, self.availability_zone))
        self.aggregate = self.compute_utils.novaclient.aggregates.create(
                                      self.aggregate_name, self.host_zone)
        self.cleanup_aggregate = True
        for computenode_name in self.computenodes_name:
            LOG.info("Add compute %s to aggregate %s" %
                    (computenode_name, self.aggregate_name))
            self.compute_utils.novaclient.aggregates.add_host(self.aggregate,
                                                       computenode_name)
        self.cleanup_aggregate_host = True

    def check_vm_az(self, vm, azone):
        LOG.info("Check VM's availability zone for aggregate validation")
        hited = 0
        azs = self.compute_utils.novaclient.availability_zones.list()
        vm_az = getattr(vm, "OS-EXT-AZ:availability_zone")
        vm_host = self.compute_utils.get_server_host(vm.name)
        if not vm_az in azone:
            raise exceptions.TestFail("VM is not on %s" % azone)
        for az in azs:
            if az.zoneName == azone:
                for host in az.hosts:
                    if vm_host == host:
                        hited = 1
                        break
        if hited == 0:
            raise exceptions.TestFail("Failed to find VM's host in %s" % azone)

    def create_vm(self):
        LOG.info("Create VM on availability zone %s" % self.availability_zone)
        vm_name = 'cloudtest_' + utils_misc.generate_random_string(6)
        vm = self.compute_utils.create_vm(vm_name=vm_name,
                                     image_name=self.params["image_name"],
                                     flavor_name=self.flavor_name,
                                     network_name=self.params["network_name"],
                                     injected_key=None, sec_group=None,
                                     availability_zone=self.availability_zone)
        vm_created = self.compute_utils.wait_for_vm_active(vm, 1,
                                                     self.vmtobeactive_timeout)
        if vm_created == False:
            raise exceptions.TestSetupFail("Failed to creating VM")
        self.register_cleanup(vm)
        return vm

    def test(self):
        vm_1=self.create_vm()
        self.check_vm_az(vm_1, self.availability_zone)

        LOG.info("Remove %s from aggregate and "
                 "create VM on availability zone %s again" %
                 (self.computenodes_name[0], self.availability_zone))
        self.compute_utils.novaclient.aggregates.remove_host(
                    self.aggregate, self.computenodes_name[0])
        self.computenodes_name.remove(self.computenodes_name[0])

        vm_2=self.create_vm()
        self.check_vm_az(vm_2, self.availability_zone)

    def teardown(self):
        if self.cleanup_aggregate_host == True:
            LOG.info("Remove the aggregate %s" % self.aggregate_name)
            for computenode_name in self.computenodes_name:
                self.compute_utils.novaclient.aggregates.remove_host(
                    self.aggregate, computenode_name)
        if self.cleanup_aggregate == True:
            self.compute_utils.novaclient.aggregates.delete(self.aggregate)
        super(AggregateValidation, self).teardown()



