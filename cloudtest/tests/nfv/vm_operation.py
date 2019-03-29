import time

from avocado.core import exceptions
from avocado.utils import data_factory
from cloudtest import remote
from cloudtest import utils_misc
from cloudtest.tests.nfv import test_utils
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class VMOperationTest(NFVTestBase):
    def __init__(self, params, env):
        super(VMOperationTest, self).__init__(params, env)

        self.test_vms_names = []
        self.created_pssr_nics = []
        self.router_name = None
        self.pssr_host = None
        self.pssr_net = None
        self.vm_fip = None
        self.vm_name = None

    def setup(self):
        self.params['vm_name'] = 'cloudtest-' + \
            utils_misc.generate_random_string(6)
        self.vm_name = self.params['vm_name']
        flavor_name = self.params.get('flavor_name')
        if flavor_name is not None:
            self.__create_flavor(flavor_name,
                                 int(self.params.get('flavor_ram', 2048)),
                                 int(self.params.get('flavor_vcpus', 2)),
                                 int(self.params.get('flavor_disk', 20)))

        self.tenant_id = test_utils.get_tenant_id(self.params,
                                                  self.params.get('tenant_name',
                                                                  'admin'))

        self.limits_before = self.compute_utils.get_limits(self.tenant_id)
        self.log.info("The limits before creating vm: %s"
                 % self.limits_before.__dict__['_info'])

    def __create_flavor(self, flavor_name, ram, vcpus, disk):
        try:
            self.compute_utils.get_flavor_id(name=flavor_name)
        except:
            self.log.info("Failed to find flavor %s, try to create one!"
                          % flavor_name)
            self.flavor = self.compute_utils.create_flavor(name=flavor_name,
                                                           ram=ram, vcpus=vcpus,
                                                           disk=disk)

    def __wait_for_vm_responsive(self, vm_name, vm_fip):
        login_benchmark = int(self.params.get('vm_creation_benchmark', '360'))
        cmd = self.params.get('test_vm_responsive_cmd', 'hostname')
        session = test_utils.get_host_session(self.params, 'instance', vm_fip)
        expected_result = None
        if cmd in 'hostname':
            expected_result = vm_name
        elif cmd in 'whoami':
            expected_result = self.image_username
        return test_utils.wait_for_cmd_execution_within_vm(session, cmd,
                                                           expected_result,
                                                           login_benchmark)

    def __create_specified_vm_and_wait_for_login(self):
        # create ports for VM
        vnic_count = int(self.params.get('vnics_count_per_vm', 1))
        network_name = None
        vnics = []
        if vnic_count > 1:
            vnics = test_utils.create_ports(self.params)
            for vnic in vnics:
                self.register_cleanup(vnic["id"], 'port')
        else:
            net = test_utils.get_test_network(self.params)
            network_name = net['name']

        vm = self.compute_utils.create_vm(vm_name=self.vm_name,
                                          image_name=self.params.get('image_name'),
                                          flavor_name=self.params.get('flavor_name'),
                                          network_name=network_name,
                                          injected_key=self.pub_key, sec_group=None,
                                          nics=vnics)
        self.register_cleanup(vm)

        if not self.compute_utils.wait_for_vm_active(vm):
            raise exceptions.TestFail("Failed to build VM: %s" % vm)

        self.vm_fip = self.compute_utils.assign_floating_ip_to_vm(vm)
        self.log.info("Created VM '%s', try to login via %s"
                      % (vm.name, self.vm_fip))
        if not self.__wait_for_vm_responsive(vm.name, self.vm_fip):
            self.compute_utils.capture_vm_console_log(vm)
            raise exceptions.TestFail(
                "Failed to wait for VM responsive: %s" % vm.name)
        return vm

    def __create_vm(self):
        self.log.info("Test vm creation within specified time")
        start_time = time.time()
        benchmark = int(self.params.get('vm_creation_benchmark', '360'))
        self.vm = self.__create_specified_vm_and_wait_for_login()

        cost_time = time.time() - start_time
        if cost_time > benchmark:
            msg = ("Failed to created VM within %d(s)!" % benchmark)
            raise exceptions.TestFail(msg)

        self.log.info("Successfully created VM within %d(s), actually used %d(s)"
                 % (benchmark, cost_time))
        return self.vm

    def __delete_vm(self):
        self.log.info("Start VM deletion test")
        limits_before_del = self.compute_utils.get_limits(self.tenant_id)
        self.log.info("The limits before deleting vm: %s"
                 % limits_before_del.__dict__['_info'])

        benchmark = int(self.params.get('vm_deletion_benchmark', 6))
        if not self.compute_utils.delete_vm(self.vm_name, benchmark):
            raise exceptions.TestFail("Failed to delete vm '%s' within %d(s)" %
                                      (self.vm_name, benchmark))
        self.log.info("Successfully deleted VM within %d(s), "
                      "try to checking the resource release!" % benchmark)

        limits_after = self.compute_utils.get_limits(self.tenant_id)
        self.log.info("The limits after deleting vm: %s"
                 % limits_after.__dict__['_info'])
        if limits_after.__dict__['_info'] == self.limits_before.__dict__['_info']:
            self.log.info("The resource of deleted vm has been released!")
        else:
            msg = "Not all resource of the deleted vm be released"
            if self.params.get('check_resource_deleted', 'no') == 'yes':
                raise exceptions.TestFail(msg)
            self.log.error(msg)

    def __stop_vm(self):
        self.log.info("Start VM stop test")
        limits_before_stop = self.compute_utils.get_limits(self.tenant_id)
        self.log.info("The limits before stopping vm: %s"
                 % limits_before_stop.__dict__['_info'])
        benchmark = int(self.params.get('vm_stop_benchmark', 60))
        self.log.info("Try to stop vm: %s" % self.vm_name)
        if not self.compute_utils.stop_vm(self.vm_name, benchmark):
            raise exceptions.TestFail("Failed to stop vm '%s' within %d(s)" %
                                      (self.vm_name, benchmark))
        self.log.info("Successfully stopped VM within %d(s), "
                      "try to checking the resource!" % benchmark)

        limits_after = self.compute_utils.get_limits(self.tenant_id)
        self.log.info("The limits after stopping vm: %s"
                 % limits_after.__dict__['_info'])
        if limits_after.__dict__['_info'] == limits_before_stop.__dict__['_info']:
            self.log.info("The resource of stopped vm was not released!")
        else:
            raise exceptions.TestFail(
                "The resource was changed after vm stopped!")

    def __start_vm(self):
        self.log.info("Start VM startup test")
        start_time = time.time()
        benchmark = int(self.params.get('vm_start_benchmark', 60))
        self.log.info("Try to start vm: %s" % self.vm_name)
        if not self.compute_utils.start_vm(self.vm_name, benchmark):
            raise exceptions.TestFail("Failed to start vm '%s' within %d(s)" %
                                      (self.vm_name, benchmark))
        cost_time = time.time() - start_time
        self.log.info("Successfully started VM within %d(s), actually used %d(s)"
                 % (benchmark, cost_time))

    def __reboot_vm(self):
        self.log.info("Start VM soft reboot test")
        start_time = time.time()
        benchmark = int(self.params.get('vm_reboot_benchmark', 60))
        self.log.info("Try to reboot vm: %s" % self.vm_name)
        if not self.compute_utils.reboot_vm(self.vm_name, benchmark):
            raise exceptions.TestFail("Failed to reboot vm '%s' within %d(s)" %
                                      (self.vm_name, benchmark))
        cost_time = time.time() - start_time
        self.log.info("Successfully reboot VM within %d(s), actually used %d(s)"
                 % (benchmark, cost_time))

        if not self.__wait_for_vm_responsive(self.vm_name, self.vm_fip):
            self.compute_utils.capture_vm_console_log(self.vm)
            raise exceptions.TestFail(
                "Failed to wait for VM responsive: %s" % self.vm.name)

    def test_create_delete_vm(self):
        self.__create_vm()
        self.__delete_vm()

    def test_create_reboot_vm(self):
        self.__create_vm()
        self.__reboot_vm()

    def test_stop_start_vm(self):
        self.__create_vm()
        self.__stop_vm()
        self.__start_vm()
        self.__delete_vm()

    def create_vm_with_pssr_nic(self):
        pssr_type = self.params.get('passthrough_type')
        self.pssr_host = self.params.get('pssr_hostname')
        self.pssr_nic = self.params.get('pssr_nic')
        if not self.pssr_nic and not self.pssr_host:
            pssr_resource = self.compute_utils.setup_pssr(
                    pssr_type,
                    self.params.get('second_physical_network'),
                    None,
                    None,
                    self.params.get('vfnum'),
                    self.params.get('mtu'))
            if not pssr_resource:
                raise exceptions.TestSetupError(
                    'Failed to find PSSR resource to test')
            self.pssr_nic = pssr_resource['nic']
            self.pssr_host = pssr_resource['host']

        elif self.pssr_nic != "" and self.pssr_host != "":

            if not self.compute_utils.setup_pssr(pssr_type,
                        self.params.get('second_physical_network'),
                        self.pssr_host,
                        self.pssr_nic,
                        self.params.get('vfnum'),
                        self.params.get('mtu')):
                raise exceptions.TestSetupError('Failed to setup PSSR')

        pssr_az = self.compute_utils.get_host_from('host_name',
                                                   self.pssr_host).zone
        normal_az = None

        hosts = self.compute_utils.get_host_from()
        for host in hosts:
            if host.service in 'compute':
                if self.pssr_host not in host.host_name:
                    normal_az = host.zone

        if not normal_az:
            raise exceptions.TestError('Did not find a second host')

        self.log.info('Test creating VM with %s nic' % pssr_type)

        def __check_vm_responsive(vm_ip, username='root', password=None,
                                  timeout=360):
            cmd = self.params.get('test_vm_responsive_cmd', 'whoami')
            use_key = password is None
            end_time = time.time() + timeout
            responsive = False
            while time.time() < end_time:
                if responsive:
                    return True
                try:
                    session = remote.RemoteRunner(host=vm_ip, username=username,
                                                  password=password,
                                                  use_key=use_key,
                                                  timeout=20)
                    if not session:
                        continue
                    result = session.run(cmd)
                    if 'root' in result.stdout:
                        responsive = True
                except Exception, e:
                    self.log.error('Failed to login vm: %s' % e)
                    continue
            return responsive

        # Create SR-IOV provider network on specified physical network
        physical_net = self.params.get('second_physical_network')
        if not physical_net:
            raise exceptions.TestError('Please specify physical network name')

        suffix = data_factory.generate_random_string(6)

        # Create provider network based on the physical network
        self.pssr_net_name = 'pssr_net_' + suffix
        self.pssr_subnet = self.pssr_net_name + '_subnet'
        segmentation_id = self.params.get('provider_net_segmentation_id', 0)
        provider_net_type = self.params.get('provider_network_type', 'vlan')

        self.pssr_net = self.network_utils.create_network(
            name=self.pssr_net_name,
            subnet=True,
            start_cidr='192.168.%s.0/24' % segmentation_id,
            provider_network_type=provider_net_type,
            provider_segmentation_id=segmentation_id,
            provider_physical_network=physical_net)

        # Create a router and connect it to the pssr_net
        self.router_name = 'cloudtest_router_' + suffix
        self.network_utils.create_router(self.router_name,
                                         external_gw=True,
                                         subnet_name=self.pssr_subnet)
        self.network_utils.add_interface_router(self.pssr_net_name,
                                                self.router_name)

        floating_ips = []
        login_benchmark = int(self.params.get('login_benchmark', 360))

        vm_count = 2
        if pssr_type == 'pci-passthrough':
            vm_count = len(self.pssr_nic)

        # Use customization script to workaround a product bug that VM did
        # not get a private IP from dhcp server at start up
        userdata = self.params.get('create_vm_post_script')
        if userdata:
            self.log.info('Customization script after create vm: %s' % userdata)

        for i in range(vm_count):
            _suffix = suffix + '_%d' % i

            self.log.info('Try to create #%d VM...' % (i+1))

            # Create a vNic using Virtual Functions
            nic_name = 'pssr_nic_' + _suffix
            nic = self.network_utils.create_port(nic_name,
                      network_id=self.pssr_net['network']['id'],
                      binding_vnic_type='direct')
            self.log.info('Created %s nic: \n%s' % (pssr_type, nic))
            self.created_pssr_nics.append(nic)
            vm_name = 'cloudtest_pssr_' + _suffix
            vm = self.compute_utils.create_vm(vm_name=vm_name,
                         image_name=self.params.get('image_name'),
                         flavor_name=self.params.get('flavor_name'),
                         injected_key=self.pub_key,
                         availability_zone=pssr_az,
                         nics=[nic], userdata=userdata)

            self.register_cleanup(vm)
            if not self.compute_utils.wait_for_vm_active(vm=vm,
                                                         timeout=login_benchmark,
                    delete_on_failure=
                        self.params.get('delete_vm_on_error', 'yes') == 'yes'):
                raise exceptions.TestFail('Failed to create vm: %s; status: %s' %
                                                            (vm.name, vm.status))

            vm_ip = self.compute_utils.assign_floating_ip_to_vm(vm)
            floating_ips.append(vm_ip)
            self.log.info("Created VM '%s', try to login via %s" % (vm.name, vm_ip))

            if __check_vm_responsive(vm_ip,
                                     password=self.image_password,
                                     timeout=login_benchmark):
                self.log.info('Successfully created VM: %s' % vm.name)
                self.test_vms_names.append(vm_name)
                self.vm_list.append(vm)
            else:
                self.compute_utils.capture_vm_console_log(vm)
                raise exceptions.TestFail('VM is not responsive: %s' % vm_ip)

        # Create 2 VMs with virtio nic
        for i in range(2):
            _suffix = suffix + '_%d' % i

            vm_name = 'cloudtest_virtio_' + _suffix
            vm = self.compute_utils.create_vm(vm_name=vm_name,
                                              network_name=self.pssr_net_name,
                                image_name=self.params.get('image_name'),
                                injected_key=self.pub_key,
                                flavor_name=self.params.get('flavor_name'),
                                availability_zone=normal_az)

            if not self.compute_utils.wait_for_vm_active(vm=vm,
                    timeout=login_benchmark,
                    delete_on_failure=
                        self.params.get('delete_vm_on_error', 'yes') == 'yes'):
                raise exceptions.TestFail('Failed to create vm: %s; status: %s' %
                                                            (vm.name, vm.status))
            self.vm_list.append(vm)
            self.test_vms_names.append(vm_name)

        # Try to ping from vm1 to vm2, vm3, vm4
        results = []
        vm1_session = remote.RemoteRunner(host=floating_ips[0],
                                          username=self.image_username,
                                          password=self.image_password)
        for vm_name in self.test_vms_names:
            vm = self.compute_utils.find_vm_from_name(vm_name)
            if not vm.addresses:
                raise exceptions.TestFail("VM '%s' has no valid IP address" %
                                          vm_name)

            pri_ip = vm.addresses[self.pssr_net_name][0]['addr']
            self.log.info('Try to ping vm: %s' % pri_ip)
            result = vm1_session.run('ping -c 10 %s' % pri_ip,
                                     ignore_status=False)
            res = (result.exit_status == 0) and ('10 received' in result.stdout)
            self.log.info("Result of ping vm '%s': %s" % (pri_ip, res))
            self.log.info('STDOUT: %s' % result.stdout)
            results.append(res)
        if not any(results):
            raise exceptions.TestFail('Ping all VMs failed')
        self.log.info('Ping all VMs successfully')

    def teardown(self):
        super(VMOperationTest, self).teardown()

        if self.pssr_host is not None:
            self.compute_utils.unlock_compute_node(self.pssr_host)

        if self.params.get('delete_vm_on_error', 'yes') == 'yes':
            for nic in self.created_pssr_nics:
                self.network_utils.delete_port(nic['id'])

            if self.router_name:
                self.log.info('Deleting router: %s' % self.router_name)
                self.network_utils.delete_router(self.router_name,
                                                 self.pssr_subnet)
            if self.pssr_net:
                self.log.info('Deleting network: %s' % self.pssr_net_name)
                self.network_utils.delete_network(name=self.pssr_net_name)

        if self.params.get('pssr_need_recovery', 'no') == 'yes':
            self.compute_utils.recovery_pssr(self.pssr_host,
                                  self.pssr_nic,
                                  self.params.get('second_physical_network'),
                                  self.params.get('mtu'))
