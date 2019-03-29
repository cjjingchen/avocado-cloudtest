import time

import copy

from avocado.core import exceptions
from cloudtest import utils_misc, remote
from cloudtest.tests.nfv import test_utils
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class NetworkMgmtTest(NFVTestBase):
    def __init__(self, params, env):
        super(NetworkMgmtTest, self).__init__(params, env)
        self.network_list = []
        self.router_list = []
        self.vnics = []
        self.network_name_list = []
        self.vm_list = []
        self.vm_name_list = []
        self.float_ip_list = []
        self.router_name_list = []
        self.body = {}
        self.security_group_list = []

    def setup(self):
        func_name = self.params['func_name']
        if func_name in ('test_create', 'test_modify_delete'):
            self.setup_for_CMD()
        if func_name in 'test_delete_virtual_port':
            self.create_resource()
        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

    def setup_for_CMD(self):
        self.login_timeout = int(self.params.get('timeout_for_creation', '360'))

        self.net_name = 'cloudtest_net_' + utils_misc.generate_random_string(6)
        self.test_subnet = self.net_name + '_subnet'
        network_cidr = '192.168.0.0/24'

        self.test_net = self.network_utils.create_network(
            name=self.net_name, subnet=True, start_cidr=network_cidr)
        self.register_cleanup(self.network_utils.get_network(self.net_name))

        # Create a router and connect it to the created network
        self.router_name = 'cloudtest_router_' + \
                           utils_misc.generate_random_string(6)
        self.network_utils.create_router(self.router_name,
                                         external_gw=True,
                                         subnet_name=self.test_subnet)
        self.network_utils.add_interface_router(self.net_name,
                                                self.router_name)

        vms_count = int(self.params.get('vms_count_to_create', 2))
        self.created_vms = []

        for suffix in range(vms_count):
            vm_name = 'cloudtest_network_mgmt_test_' + str(suffix)
            vm = self.compute_utils.create_vm(vm_name=vm_name,
                                              image_name=self.params.get(
                                                  'image_name'),
                                              flavor_name=self.params.get(
                                                  'flavor_name'),
                                              injected_key=self.pub_key,
                                              network_name=self.net_name)

            if not self.compute_utils.wait_for_vm_active(
                    vm=vm,
                    timeout=self.login_timeout,
                    delete_on_failure=self.params.get('delete_vm_on_error',
                                                      'yes') == 'yes'):
                raise exceptions.TestFail(
                    'Failed to create vm: %s; status: %s' %
                    (vm.name, vm.status))
            self.created_vms.append(vm)

    def test_create(self):
        for vm in self.created_vms:
            self.register_cleanup(vm)

        self.vm_ip = self.compute_utils.assign_floating_ip_to_vm(
            self.created_vms[0])
        status = self.compute_utils.wait_for_vm_pingable(self.vm_ip)
        if not status:
            raise exceptions.TestFail(
                'Can not ping vm by float ip %s' % self.vm_ip)
        if not self.__vm_communicate(vm_list=self.created_vms,
                                     floating_ip=self.vm_ip,
                                     is_all_floating_ip=False):
            raise exceptions.TestFail('Ping all VMs failed')

    def test_modify_delete(self):
        msg = 'This test basically tests below 2 aspects:\n'
        msg += '  1) the connection is not affected after modified subnet\n'
        msg += '  2) only the subnet without any port or VM can be deleted\n'
        self.log.info(msg)

        self.log.info('Creating the 2nd network')
        self.test_2nd_net_name = 'cloudtest_nt_2_' + \
                                 utils_misc.generate_random_string(6)
        self.test_net = self.network_utils.create_network(
            name=self.test_2nd_net_name, subnet=True,
            start_cidr=self.params.get('network_cidr'))

        self.log.info(
            'Try to modify the name and allocation pool of 1st subnet')
        allo_start = self.params.get('allocation_start')
        allo_end = self.params.get('allocation_end')
        new_subnet_name = self.params.get('to_name')
        if new_subnet_name:
            new_subnet_name += utils_misc.generate_random_string(6)

        if allo_start or allo_end:
            router = self.network_utils.get_router(self.router_name)
            sub_net = self.network_utils.get_subnet(self.test_subnet)
            start = sub_net['allocation_pools'][0]['start']
            end = sub_net['allocation_pools'][0]['end']
            self.network_utils.router_subnet_remove(router['id'], sub_net['id'])
            if not self.network_utils.update_subnet(name=self.test_subnet,
                                                    action='unset',
                                                    allocation_start=start,
                                                    allocation_end=end):
                raise exceptions.TestFail('Failed to update:unset subnet')

        if not self.network_utils.update_subnet(name=self.test_subnet,
                                                action='set',
                                                to_name=new_subnet_name,
                                                allocation_start=allo_start,
                                                allocation_end=allo_end):
            raise exceptions.TestFail('Failed to update:set subnet')
        if allo_start or allo_end:
            self.network_utils.add_interface_router(self.net_name,
                                                    self.router_name)
        if new_subnet_name:
            self.test_subnet = new_subnet_name

        self.vm_ip = self.compute_utils.assign_floating_ip_to_vm(
            self.created_vms[0])
        status = self.compute_utils.wait_for_vm_pingable(self.vm_ip)
        if not status:
            raise exceptions.TestFail(
                'Can not ping vm by float ip %s' % self.vm_ip)
        self.log.info('Floating ip of vm is %s' % self.vm_ip)
        if not self.__vm_communicate(vm_list=self.created_vms,
                                     floating_ip=self.vm_ip):
            raise exceptions.TestFail('Ping all VMs failed')

        # Create a new vm to check it's IP should be in the new range
        self.log.info('Start to create the 3rd vm')
        vm_name = 'cloudtest_network_mgmt_test_' + \
                  utils_misc.generate_random_string(6)
        vm = self.compute_utils.create_vm(vm_name=vm_name,
                                          image_name=self.params.get(
                                              'image_name'),
                                          flavor_name=self.params.get(
                                              'flavor_name'),
                                          injected_key=self.pub_key,
                                          network_name=self.net_name)
        delete_vm = self.params.get('delete_vm_on_error', 'yes')
        if not self.compute_utils.wait_for_vm_active(
                vm=vm,
                timeout=self.login_timeout,
                delete_on_failure=(delete_vm == 'yes')):
            raise exceptions.TestError(
                'Fail to to created the 3th vm : %s' % vm.name)
        vm = self.compute_utils.find_vm_from_name(vm.name)
        self.created_vms.append(vm)
        if not vm.addresses:
            raise exceptions.TestFail("VM %s has no valid IP address after"
                                      " change subnet" % vm.name)
        pri_ip = vm.addresses[self.net_name][0]['addr']
        self.log.info('IP of the 3rd VM is %s' % pri_ip)
        if allo_start or allo_end:
            if not (int(pri_ip.split('.')[-1]) >= int(allo_start.split('.')[-1])
                    and int(pri_ip.split('.')[-1]) <= int(
                    allo_end.split('.')[-1])):
                raise exceptions.TestFail(
                    'IP of 3rd VM is not in the new range')
            self.log.info('IP of the 3rd VM is in the new range')

        # Delete the 1st network which is in use should not succeed, only after
        # deleting all resource which are using the network, it can be deleted
        self.log.info('Test that subnet in-use can not be deleted')
        try:
            self.network_utils.delete_network(self.net_name)
        except:
            self.log.info('Network can not be deleted which is expected')
        if not self.network_utils.get_network(self.net_name):
            raise exceptions.TestFail('Network not found, may be deleted '
                                      'unexpectedly')

        # Delete the 2nd network which is not in use should succeed
        self.log.info('Test that subnet not-in-use can be deleted')
        self.network_utils.delete_network(self.test_2nd_net_name)
        time.sleep(3)
        if self.network_utils.get_network(self.test_2nd_net_name):
            msg = 'Failed to delete network: %s' % self.test_2nd_net_name
            raise exceptions.TestFail(msg)
        self.log.info('Successfully deleted 2nd network: %s' %
                      self.test_2nd_net_name)

        # Delete VMs
        for vm in self.created_vms:
            self.compute_utils.delete_vm(vm.name)
        try:
            self.log.info('Subnetname is %s' % self.test_subnet)
            self.network_utils.delete_router(self.router_name, self.test_subnet)
        except:
            raise exceptions.TestError(
                'Failed to delete router' % self.router_name)
        self.network_utils.delete_network(self.net_name)
        time.sleep(3)
        if self.network_utils.get_network(self.net_name):
            raise exceptions.TestFail(
                'Network "%s" still exists' % self.net_name)
        self.log.info('Success to delete network 1st network:%s.' %
                      self.net_name)

    def network_create_query(self):
        """

        :return:
        """
        host_list = self.compute_utils.get_all_hypervisors()
        if len(host_list) < 2:
            raise exceptions.TestFail(
                'There is not enough compute node for test.')

        self.__create_network()
        self.__create_router(self.network_name_list)
        self.__create_vm(host_list[0].hypervisor_hostname,
                         self.network_name_list[0], 2)
        self.__create_vm(host_list[-1].hypervisor_hostname,
                         self.network_name_list[-1], 1)

        floating_ip = self.compute_utils.assign_floating_ip_to_vm(
            self.vm_list[0])
        status = self.compute_utils.wait_for_vm_pingable(floating_ip)
        if not status:
            raise exceptions.TestFail(
                'Can not ping vm by float ip %s' % floating_ip)

        ping_able = self.__vm_communicate(vm_list=self.vm_list,
                                          floating_ip=floating_ip)
        if not ping_able:
            raise exceptions.TestFail("The host is not ping able.")

    def test_delete_virtual_port(self):
        self.log.info('Start to test delete virtaul port.')
        self.network_utils.delete_port(self.vnics.pop(0)['id'])

        # check network info
        instance = self.compute_utils.find_vm_from_name(self.vm_list[0])
        net_info = instance.addresses
        for i in range(len(self.vnics)):
            net_name = net_info.keys()[0]
            ip_address = net_info[net_name][i]['addr']
            self.log.info(
                'Network is: %s, IP address is: %s.' % (net_name, ip_address))
        self.log.info('Success to test delete virtaul port.')

    def create_resource(self):
        network = self.network_utils.create_network(
            name_prefix='cloudtest_net_',
            subnet=True,
            start_cidr='192.168.0.0/24')
        self.network_list.append(network['network']['name'])
        for i in range(int(self.params.get('vnics', 2))):
            port_name = 'cloudtest_vm_' + utils_misc.generate_random_string(6)
            virtual_port = self.network_utils.create_port(name=port_name,
                                                          network_id=
                                                          network['network'][
                                                              'id'],
                                                          binding_vnic_type='normal')
            self.vnics.append(virtual_port)

        vm_name = 'cloudtest_vm_' + utils_misc.generate_random_string(6)
        vm = self.compute_utils.create_vm(vm_name=vm_name,
                                          image_name=self.params.get(
                                              'image_name'),
                                          flavor_name=self.params.get(
                                              'flavor_name'),
                                          injected_key=self.pub_key,
                                          sec_group=None,
                                          nics=self.vnics)

        if not self.compute_utils.wait_for_vm_active(vm):
            raise exceptions.TestFail("Failed to build VM: %s" % vm)

        self.__create_router(self.network_list)

        self.vm_list.append(vm_name)
        instance = self.compute_utils.find_vm_from_name(vm_name)
        net_info = instance.addresses

        for i in range(len(self.vnics)):
            net_name = net_info.keys()[0]
            ip_address = net_info[net_name][i]['addr']
            self.log.info(
                'Network is: %s, IP address is: %s.' % (net_name, ip_address))

    def test_vm_with_security_group(self):
        cidr_address = self.body['cidr']
        wrong_cidr_address = self.body['wrong_cidr']

        self.__create_vm_with_secgroup_cidr(cidr_address)
        self.__create_vm_with_secgroup_cidr(wrong_cidr_address)

        self.__create_vm_with_secgroup_cidr(cidr_address, ssh_able=True)

        session = \
            test_utils.wait_for_get_instance_session(self.params,
                                                     self.float_ip_list[-1])
        if not session:
            raise exceptions.TestFail(
                "Failed to get session for instance login.")

        ping_able = self.__vm_communicate(session=session,
                                          vm_list=self.vm_list[0:1],
                                          floating_ip=self.float_ip_list[-1],
                                          is_all_floating_ip=True)
        if not ping_able:
            raise exceptions.TestFail(
                "The host with correct security group is not ping able.")

        ping_able = self.__vm_communicate(session=session,
                                          vm_list=self.vm_list[1:-1],
                                          floating_ip=self.float_ip_list[-1],
                                          is_all_floating_ip=True)
        if ping_able:
            raise exceptions.TestFail(
                "The host with wrong correct security group is ping able.")

    def __create_vm_with_secgroup_cidr(self, cidr_address=None,
                                       with_floating_ip=True, ssh_able=False):

        sec_group = self.create_security_group(icmp_cidr=cidr_address,
                                               ssh_able=ssh_able)
        vm = self.compute_utils.create_vm(
            image_name=self.params.get("image_name"),
            flavor_name=self.params.get('flavor_name'),
            injected_key=self.pub_key,
            network_name=self.params.get('network_name'),
            sec_group=sec_group)
        if not self.compute_utils.wait_for_vm_active(
                vm=vm, timeout=60,
                delete_on_failure=self.params.get('delete_vm_on_error',
                                                  'yes') == 'yes'):
            raise exceptions.TestFail(
                'Failed to create vm: %s; status: %s' %
                (vm.name, vm.status))
        self.vm_list.append(vm)
        self.log.info("server is %s" % vm)
        if with_floating_ip is True:
            floating_ip = self.compute_utils.assign_floating_ip_to_vm(vm)
            self.float_ip_list.append(floating_ip)
        return vm

    def test_vm_communicate_with_fixed_ips(self):
        host_list = self.compute_utils.get_all_hypervisors()
        self.log.info('host_list is %s' % host_list)
        self.__create_network(2)
        self.__create_router(self.network_name_list)
        in_same_host = eval(self.body['in_same_host'])
        if in_same_host is True:
            for network_name in self.network_name_list:
                self.__create_vm(host=host_list[0].hypervisor_hostname,
                                 network_name=network_name, vm_count=1)
        else:
            if len(host_list) < 2:
                raise exceptions.TestFail(
                    'There is not enough compute node for test.')
            self.__create_vm(host_list[0].hypervisor_hostname,
                             self.network_name_list[0], 1)
            self.__create_vm(host_list[-1].hypervisor_hostname,
                             self.network_name_list[-1], 1)

        floating_ip = \
            self.compute_utils.assign_floating_ip_to_vm(self.vm_list[0])
        status = self.compute_utils.wait_for_vm_pingable(floating_ip)
        if not status:
            raise exceptions.TestFail('Can not ping vm by float ip %s' %
                                      floating_ip)

        ping_able = self.__vm_communicate(vm_list=self.vm_list,
                                          floating_ip=floating_ip,
                                          is_all_floating_ip=False)
        if not ping_able:
            raise exceptions.TestFail("The host is not ping able.")

    def test_vm_communicate_with_floatingip(self):
        host_list = self.compute_utils.get_all_hypervisors()
        self.log.info('host_list is %s' % host_list)
        self.__create_network(1)
        self.__create_router(self.network_name_list)
        in_same_host = eval(self.body['in_same_host'])
        if in_same_host is True:
            self.__create_vm(host=host_list[0].hypervisor_hostname,
                             network_name=self.network_name_list[0], vm_count=2)
        else:
            if len(host_list) < 2:
                raise exceptions.TestFail(
                    'There is not enough compute node for test.')
            self.__create_vm(host_list[0].hypervisor_hostname,
                             self.network_name_list[0], 1)
            self.__create_vm(host_list[-1].hypervisor_hostname,
                             self.network_name_list[0], 1)

        for instance in self.vm_list:
            floating_ip = self.compute_utils.assign_floating_ip_to_vm(instance)
            status = self.compute_utils.wait_for_vm_pingable(floating_ip)
            if not status:
                raise exceptions.TestFail(
                    'Can not ping vm by float ip %s' % floating_ip)
            self.float_ip_list.append(floating_ip)

        # for float_ip in self.float_ip_list:
        ping_able = self.__vm_communicate(vm_list=self.vm_list,
                                          floating_ip=self.float_ip_list[-1],
                                          is_all_floating_ip=True)
        if not ping_able:
            raise exceptions.TestFail("The host is not ping able.")

    def __create_router(self, networklist=[], routernum=1):
        for i in range(routernum):
            router_name = 'cloudtest_router_' + \
                          utils_misc.generate_random_string(6)
            self.network_utils.create_router(router_name,
                                             external_gw=True,
                                             subnet_name=None)
            self.router_name_list.append(router_name)
        for network in networklist:
            self.log.info('-' * 20)
            self.network_utils.add_interface_router(network, router_name)
            self.log.info(
                'Add network %s to router %s.' % (network, router_name))

    def __create_network(self, network_num=2):
        for i in range(network_num):
            network = self.network_utils.create_network(
                name_prefix='cloudtest_net_',
                subnet=True,
                start_cidr='192.168.%s.0/24' % i)
            network_name = network['network']['name']
            self.network_list.append(network)
            self.network_name_list.append(network_name)

    def __create_vm(self, host=None, network_name=None, vm_count=1):
        vm_names = self.compute_utils.create_vms_on_specific_node(
            node_name=host,
            vm_count=vm_count,
            flavor_name=None,
            network_name=network_name)
        if vm_count == 1:
            vm_names = [vm_names]
        self.log.info(
            'Start to create vm: %s in the nodes: %s.' % (vm_names, host))
        for vm_name in vm_names:
            instance = self.compute_utils.find_vm_from_name(vm_name)
            if not self.compute_utils.wait_for_vm_active(instance):
                raise exceptions.TestFail("Failed to build VM: %s" % instance)
            self.vm_list.append(instance)
            self.vm_name_list.append(vm_name)
            self.log.info(
                'Success to create vm: %s in the nodes: %s.' % (vm_name, host))
        return vm_names

    def __vm_communicate(self, session=None, vm_list=[], floating_ip=None,
                         is_all_floating_ip=False):
        """
        :param net_name: if all vm has floating ip, net_name should be None
        :param vm_list: 
        :param all_floatingip: if all vm has floating ip,this should be True
        :param floating_ips: if all vm has floating ip,this should be a list,
        otherwise it is a single ip
        :return: 
        """
        self.log.info('Start to check vm : %s communicates status.' % vm_list)
        if session is None:
            session = test_utils.wait_for_get_instance_session(self.params,
                                                               floating_ip)
            if not session:
                raise exceptions.TestFail(
                    "Failed to get session for instance login.")
        results = []
        for vm in vm_list:
            vm = self.compute_utils.find_vm_from_name(vm.name)
            if not vm.addresses:
                raise exceptions.TestFail(
                    "VM %s has no valid IP address" % vm.name)
            net_name = vm.addresses.keys()[0]
            pri_ip = vm.addresses[net_name][0]['addr']
            if is_all_floating_ip:
                pri_ip = vm.addresses[net_name][1]['addr']
            # if pri_ip == floating_ip:
            #     continue
            self.log.info('Try to ping vm: %s' % pri_ip)
            result = session.run('ping -c 10 %s' % pri_ip, ignore_status=True)
            res = (result.exit_status == 0) and ('10 received' in result.stdout)
            self.log.info("Result of ping vm '%s': %s" % (pri_ip, res))
            self.log.info('STDOUT: %s' % result.stdout)
            results.append(res)
        if not any(results):
            return False
        self.log.info('Ping all VMs successfully')
        return True

    def create_security_group(self, secgroup_name=None, icmp_cidr=None,
                              ssh_able=False):
        if secgroup_name is None:
            secgroup_name = "cloudtest_scgroup_%s" % \
                            utils_misc.generate_random_string(6)
        created_sg = self.network_utils.create_secgroup_with_no_rule(
            secgroup_name)
        if icmp_cidr is not None:
            self.network_utils.create_secgroup_rule_icmp_cidr(
                created_sg, icmp_cidr)
        if ssh_able:
            self.network_utils.create_secgroup_rule_ssh(created_sg)
        self.security_group_list.append(created_sg)
        return created_sg

    def teardown(self):
        super(NetworkMgmtTest, self).teardown()
        func_name = self.params['func_name']
        if func_name in ('test_create', 'test_modify_delete'):
            try:
                for vm in self.created_vms:
                    vm.delete()

                self.log.info('Deleting router: %s' % self.router_name)
                self.network_utils.delete_router(self.router_name,
                                                 self.test_subnet)
                self.network_utils.delete_network(self.net_name)
                self.network_utils.delete_network(self.test_2nd_net_name)
            except:
                pass
        else:
            for port in self.vnics:
                self.network_utils.delete_port(port["id"])

            for router_name in self.router_name_list:
                router = self.network_utils.get_router(router_name)
                self.network_utils.router_gateway_clear(router['id'])
                for network in self.network_name_list:
                    subnet_name = network + '_subnet'
                    self.network_utils.router_subnet_remove(router['id'],
                                                            self.network_utils.
                                                            get_subnet(
                                                                subnet_name)[
                                                                'id'])
                self.network_utils.delete_router(router_name)
            for network in self.network_name_list:
                self.network_utils.delete_network(network)
            time.sleep(10)
            for security_group_id in self.security_group_list:
                self.network_utils.del_security_group(security_group_id)
