from avocado.core import exceptions
from cloudtest import utils_misc, remote
from cloudtest.tests.nfv import test_utils
from cloudtest import data_dir
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class CPUPinningTest(NFVTestBase):
    def __init__(self, params, env):
        super(CPUPinningTest, self).__init__(params, env)
        self.ram = self.params.get('ram', 2048)
        self.vcpus = self.params.get('vcpus', 2)
        self.disk = self.params.get('disk', 32)

        self.isolate_cpu_list = []
        self.session = None
        self.prime_name = None

    def setup(self):
        pass

    def _create_vm_and_cpuset(self, cpu_type, check_cpu_key, host=None):
        if cpu_type == "dedicated":
            extra_spec = {"hw:cpu_policy": cpu_type,
                          "hw:cpu_thread_policy": "isolate"}
        elif cpu_type == "shared":
            extra_spec = {"hw:cpu_policy": cpu_type}
        else:
            raise exceptions.TestFail("cpu_policy: %s is NOT expected." %
                                      cpu_type)
        # Create instance1 with cpu_policy and cpu_thread_policy
        if not host:
            self.log.info('Create first vm in one of the nodes.')
            vm_name = 'cloudtest_CPU_' + utils_misc.generate_random_string(6)
            self.flavor = self.compute_utils.create_flavor(
                ram=self.ram, vcpus=self.vcpus, disk=self.disk,
                extra_spec=extra_spec)

            instance = test_utils.create_vm_with_cpu_pinning_and_wait_for_login(
                self.params, vm_name, injected_key=self.pub_key, ram=self.ram,
                vcpus=self.vcpus, disk=self.disk, flavor_name=self.flavor.name,
                **extra_spec)
            host = self.compute_utils.get_server_host(vm_name).split('.')[0]
        else:
            self.log.info(
                'Create second vm in the nodes where the first vm located.')
            self.flavor = self.compute_utils.create_flavor(
                extra_spec=extra_spec)
            node = host + '.domain.tld'
            vm_name = self.compute_utils.create_vm_on_specific_node(
                node_name=node, flavor_name=self.flavor.name)
            host = u'%s' % host
            instance = self.compute_utils.find_vm_from_name(vm_name)
            if not self.compute_utils.wait_for_vm_active(instance):
                raise exceptions.TestFail("Failed to build VM: %s" % instance)
        # Get instance name via name
        self.vm_list.append(instance)
        instance_name = self.compute_utils.get_vm_domain_name(vm_name)
        self.log.info("Instance name is %s" % instance_name)
        # Get host via name
        self.log.info("Host is %s" % host)

        self.controller_session = test_utils.get_host_session(self.params,
                                                              'controller')

        if check_cpu_key == "cpu_policy":
            # Check cpu policy
            state, cpu_list = test_utils.check_cpuset(instance_name, host,
                                                      cpu_type,
                                                      self.controller_session)
            if state:
                self.isolate_cpu_list = cpu_list
                self.log.info("%s: cpu_policy is %s, cpusets are expected."
                              % (vm_name, cpu_type))
        elif check_cpu_key == "cpu_thread_policy":
            # Check cpu policy
            if test_utils.check_vm_cpu_isolation(host, self.controller_session):
                self.log.info("%s: cpu_policy is %s, cpusets are expected."
                              % (vm_name, cpu_type))
        return instance, str(host)

    def test_cpu_performacne(self, vm=None, host=None, cpu_type='dedicated'):
        if not vm:
            raise exceptions.TestFail("Fail to get the instance we create.")
        floating_ip = self.compute_utils.assign_floating_ip_to_vm(vm)
        self.prime_name = self.get_prime95_name(host)
        self.copy_prime95_to_instance(host_ip=floating_ip,
                                      prime_name=self.prime_name)

        self.record_cpu_info(host=host, controller_ip=self.controller_ip,
                             controller_password=self.controller_password)

        cpu_list_1 = self.collect_cpu_info()
        self.install_prime95(host_ip=floating_ip, prime_name=self.prime_name)
        self.record_cpu_info(host=host, controller_ip=self.controller_ip,
                             controller_password=self.controller_password)
        cpu_list_2 = self.collect_cpu_info()
        high_used_cpu_list = self.get_the_high_used_cpu(cpu_list_1, cpu_list_2)
        self.check_cpu_used_list(self.isolate_cpu_list, high_used_cpu_list,
                                 cpu_type)

    def get_prime95_name(self, node_ip=None):
        session = test_utils.get_host_session(self.params, 'controller')
        
        ssh_cmd = "ssh %s " % node_ip
        cmd = "'getconf LONG_BIT'"
        process_info = session.run(ssh_cmd + cmd).stdout
        if '64' in process_info:
            prime_name = 'prime95.linux64.tar.gz'
        else:
            prime_name = 'prime95.linux32.tar.gz'
        self.log.info('Prime name is : %s' % prime_name)
        return prime_name

    def copy_prime95_to_instance(self, host_ip=None,
                                 prime_name='prime95.linux64.tar.gz'):
        self.log.info('Prepare to copy prime95 to instance.')
        self.session = test_utils.wait_for_get_instance_session(self.params,
                                                                host_ip)

        self.log.info('-' * 20)
        self.session.run('mkdir /root/prime95')
        self.log.info('+' * 20)
        local_path = '%s/%s' % (data_dir.COMMON_TEST_DIR, prime_name)
        remote_path = '/root/prime95/'
        self.session.copy_file_to(local_path, remote_path)
        self.log.info('Success to copy prime95 to instance.')

    def install_prime95(self, host_ip=None, continue_time=60,
                        prime_name='prime95.linux64.tar.gz'):
        self.log.info('Prepare to install prime95.')
        if not self.session:
            self.session = test_utils.wait_for_get_instance_session(self.params,
                                                                    host_ip)
        cmd_result = self.session.run(
            'cd /root/prime95 && tar -xzvf %s' % prime_name)
        execute_prime = "cd /root/prime95 && ./mprime -t "
        try:
            # thread.start_new_thread(self.session.run, (execute_prime, continue_time, True))
            self.session.run(execute_prime, continue_time, True)
        except:
            self.log.info('Succeed to install and stop prime95.')

    def record_cpu_info(self, prime_log_path='/tmp/prime.log', host=None,
                        controller_ip=None,
                        controller_password=None):
        """
        
        :param prime_log_path: 
        :param host: the node host where the instance located
        :param controller_ip: 
        :param controller_password: 
        :return: 
        """
        self.log.info('Prepare to record cpu status.')

        session = test_utils.get_host_session(self.params, 'controller')

        ssh_cmd = "ssh -q %s 'yum install sysstat -y && sar -P ALL 1 20 > %s'" \
                  % (host, prime_log_path)
        session.run(ssh_cmd)
        session.run('scp %s:%s %s' % (host, prime_log_path, prime_log_path))
        remote_package = remote.Remote_Package(address=controller_ip,
                                               client='ssh', username="root",
                                               password=controller_password,
                                               port='22',
                                               remote_path=prime_log_path)
        remote_package.pull_file(local_path=prime_log_path)
        session.run('rm -rf %s' % prime_log_path)
        self.log.info("Copy prime.log back to local.")

    def collect_cpu_info(self, file_path='/tmp/prime.log'):
        self.log.info('Collect node cpu info.')
        prime_log = file(file_path, 'r')
        cpu_list = []
        for log_line in prime_log.readlines():
            if log_line.startswith('Average:'):
                if 'CPU' not in log_line and 'all' not in log_line:
                    cpu_info = log_line.split()
                    cpu_list.append([eval(cpu_info[1]), eval(cpu_info[2]),
                                     eval(cpu_info[3])])
        prime_log.close()
        return cpu_list

    def get_the_high_used_cpu(self, cpu_list_before, cpu_list_after, usage=60):
        high_used_cpu_list = []
        for cpu_info in range(len(cpu_list_before)):
            if cpu_list_after[cpu_info][1] - cpu_list_before[cpu_info][
                1] > usage:
                # or cpu_list_after[cpu_info][2] - cpu_list_before[cpu_info][2] > usage:
                high_used_cpu_list.append(cpu_list_after[cpu_info][0])
                self.log.info(
                    'High used cpu info : %s' % cpu_list_after[cpu_info])
        self.log.info('high_used_cpu_list is : %s' % high_used_cpu_list)
        return high_used_cpu_list

    def check_cpu_used_list(self, isolate_cpu_list=[], high_used_cpu_list=[],
                            cpu_type='dedicated'):
        self.log.info('Prepare to check cpu info, cpu type is %s.' % cpu_type)
        if cpu_type == "dedicated":
            try:
                for cpu in isolate_cpu_list:
                    high_used_cpu_list.remove(cpu)
            except:
                raise exceptions.TestFail(
                    'Other cpu core was influenced by prime95.')
            if len(high_used_cpu_list) > 0:
                raise exceptions.TestFail(
                    'Other cpu core was influenced by prime95.')
        elif cpu_type == "shared":
            for cpu in isolate_cpu_list:
                if high_used_cpu_list.index(cpu) >= 0:
                    raise exceptions.TestFail(
                        'Isolate cpu core was influenced by prime95.')
        else:
            raise exceptions.TestFail(
                "cpu_policy: %s is NOT expected." % cpu_type)

    def test_vm_operation_with_cpu_policy(self):
        self.log.info("Create VM with cpu_policy: dedicated, "
                      "cpu_thread_policy: isolate")
        cpu_policy_type = "dedicated"
        check_cpu_key = "cpu_policy"
        instance, host = self._create_vm_and_cpuset(cpu_policy_type,
                                                    check_cpu_key)
        self.test_cpu_performacne(instance, host, cpu_policy_type)

        self.log.info("Create VM with cpu_policy: shared")
        cpu_policy_type = "shared"
        instance, host = self._create_vm_and_cpuset(cpu_policy_type,
                                                    check_cpu_key, host)
        self.test_cpu_performacne(instance, host, cpu_policy_type)

    def test_vm_operation_with_cpu_thread_policy(self):
        self.log.info("Create the 1st VM with cpu_policy: dedicated, "
                      "cpu_thread_policy: isolate")
        cpu_policy_type = "dedicated"
        check_cpu_key = "cpu_thread_policy"
        self._create_vm_and_cpuset(cpu_policy_type, check_cpu_key)

        self.log.info("Create the 2nd VM with cpu_policy: dedicated, "
                      "cpu_thread_policy: isolate")
        cpu_policy_type = "dedicated"
        self._create_vm_and_cpuset(cpu_policy_type, check_cpu_key)

    def _get_dpdk_core(self, host_ip, controller_session):
        """
        get cpu core number of dpdk
        :param conrtller_session:
        :param host_ip: compute node ip
        :return: core list
        """
        core_list = []
        cmd = "ssh -q %s sar -P ALL | grep Average | awk '{print $2 \" \" $3}'" \
              % host_ip
        result = controller_session.run(cmd)
        result = result.stdout.strip()
        for line in result.split("\n"):
            line = line.split()
            if line[0].isdigit() and float(line[1]) > 99:
                core_list.append(line[0])
        return core_list

    def test_vm_max_count(self):
        controller_session = test_utils.get_host_session(self.params,
                                                         'controller')
        vm_domain_name_list = []
        extra_spec = {"hw:cpu_policy": "dedicated"}
        flavor = self.compute_utils.create_flavor(ram=self.ram,
                                                  vcpus=self.vcpus,
                                                  disk=self.disk,
                                                  extra_spec=extra_spec)
        self.register_cleanup(flavor)
        nodes = self.compute_utils.get_all_hypervisors()
        host_name = nodes[0].hypervisor_hostname
        host_ip = nodes[0].host_ip
        vm_num = 0
        vm_name_str = "cloudtest-" + utils_misc.generate_random_string(6)
        while True:
            vm_name = vm_name_str + "-" + str(vm_num)
            vm_num = vm_num +1
            net = test_utils.get_test_network(self.params)
            self.compute_utils.create_vm_on_specific_node(
                node_name=host_name,
                flavor_name=flavor.name,
                injected_key=self.pub_key,
                network_name=net['name'],
                vm_name=vm_name)
            vm = self.compute_utils.find_vm_from_name(vm_name)
            self.register_cleanup(vm)

            status = self.compute_utils.wait_for_vm_active(
                vm, delete_on_failure=False)
            if not status:
                break

            vm_domain_name = self.compute_utils.get_vm_domain_name(vm_name)
            vm_domain_name_list.append(vm_domain_name)

        self.log.info("Can create %s vms on node %s when set "
                      "cpu dedicated policy." % (str(vm_num - 1), host_name))
        dpdk_core_list = self._get_dpdk_core(host_ip, controller_session)
        test_utils.check_vm_cpu_isolation(host_ip, controller_session,
                                          dpdk_core_list)

    def teardown(self):
        super(CPUPinningTest, self).teardown()
