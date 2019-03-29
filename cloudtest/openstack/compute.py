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


import os
import re
import time
import json
import logging
import requests
import tempfile
import os_client_config

from avocado.core import exceptions
from avocado.utils import genio
from avocado.utils import process
from avocado.utils import network
from cloudtest import utils_misc
from cloudtest import remote
from cloudtest.openstack import network
from cloudtest.openstack import volume
from common import Common


LOG = logging.getLogger('avocado.test')


class Compute(Common):
    def __init__(self, params):
        super(Compute, self).__init__(params)
        self.novaclient = os_client_config.make_client('compute',
                                                       **self.nova_credential)
        self.network_utils = network.Network(params)
        self.image_client = self.novaclient.images
        self.server_client = self.novaclient.servers
        self.flavor_client = self.novaclient.flavors
        self.volume_client = self.novaclient.volumes
        self.volume_utils = volume.Volume(params)

        self.hosts_client = self.novaclient.hosts
        self.keypairs_client = self.novaclient.keypairs

        self.server_group_client = self.novaclient.server_groups
        self.hypervisor_client = self.novaclient.hypervisors

        self.quotas_client = self.novaclient.quotas
        self.usage_client = self.novaclient.usage
        self.limits_client = self.novaclient.limits

    def get_public_key(self, public_key_filename=None):
        cmd = 'dmidecode | awk "/UUID/ {print $2}"'
        result = process.run(cmd, shell=True, verbose=False)
        LOG.debug("Stdout of command: %s" % result.stdout)
        uuid_post = result.stdout.split('-')[-1].strip('\n')
        keyname = 'cloudtest_key_uuid_%s' % uuid_post
        LOG.debug("keyname is %s" % keyname)
        pub_keys = self.keypairs_client.findall(name=keyname)
        LOG.info('Keypair finding result: %s' % pub_keys)
        if len(pub_keys) > 0:
            LOG.info("Keypair already exists: %s" % pub_keys[0])
            return pub_keys[0]

        LOG.info('Try to create a new keypair: %s' % keyname)
        if public_key_filename is None:
            public_key_filename = '/root/.ssh/id_rsa.pub'
        public_key = [line for line in open(public_key_filename)][0]
        public_key = public_key.strip('\n')
        created_key = self.keypairs_client.create(name=keyname,
                                                  public_key=public_key)
        return created_key

    def delete_public_key(self, key_name='cloudtest_key'):
        LOG.info("Try to find %s" % key_name)
        pks = self.keypairs_client.list()
        for pk in pks:
            if pk.name == key_name:
                LOG.info("Try to delete %s" % pk)
                pk.delete()
                return True
        return False

    def assign_floating_ip_to_vm(self, vm, fip_list=None):
        """
        Assign floating ip to the specified VM

        :param vm_name: the name of VM to assign floating IP
        :param fip_list: the list of free floating ip address
        :return: assigned floating ip address
        """
        if not fip_list:
            fip_list = self.network_utils.get_free_floating_ips()
            LOG.debug('Got floating ip list: %s' % fip_list)

        assigned_ips = []
        vm = self.find_vm_from_name(vm.name)
        if vm.addresses:
            assigned_ips = [address for address in vm.addresses.values()[0]
                                if address[u'OS-EXT-IPS:type'] == u'floating']
        if len(assigned_ips) < 1:
            free_ip = fip_list[-1].get('floating_ip_address')
            vm.add_floating_ip(free_ip)
            LOG.info("Assigned floating IP '%s' to VM '%s'" % (free_ip, vm.name))
            return free_ip
        return assigned_ips[0]

    def get_private_ip(self, instance):
        if hasattr(instance, 'networks'):
            if len(instance.networks.values()) < 1:
                vm = self.find_vm_from_name(instance.name)
            fixed_ip = [ip[0] for ip in vm.networks.values()][0]
        return fixed_ip

    def get_flavor_id(self, name):
        """
        Retrieve a flavor id that specified by name
        :param name: the name of flavor to get
        :returns: the flavor id
        """
        return self.flavor_client.find(name=name).id

    def create_flavor(self, name=None, ram=2048, vcpus=2, disk=60, extra_spec=None):
        """
        Create a flavor with name specified

        :param name: the flavor name to create
        :return: Flavor object
        """
        flavor_name = name or 'cloudtest_flavor_' + utils_misc.generate_random_string(6)
        flavor = self.flavor_client.create(name=flavor_name, ram=ram,
                                           vcpus=vcpus, disk=disk)
        if extra_spec is not None:
            flavor.set_keys(extra_spec)
        return flavor

    def delete_flavor(self, name):
        """
        Delete the flavor according to name

        :param name: the name of the flavor
        """
        LOG.info('Try to delete flavor %s' % name)
        flavors = self.flavor_client.findall(name=name)
        for flavor in flavors:
            flavor.delete()
        flavors = self.flavor_client.findall(name=name)
        if len(flavors) == 0:
            return True
        else:
            return False

    def create_vm(self, vm_name=None, image_name=None, flavor_name=None,
                  network_name=None, injected_key=None, sec_group=None,
                  scheduler_hints=None, availability_zone=None,
                  nics=[], userdata=None, min_count=None, admin_pass=None):
        """
        Boot a vm
        :param vm_name: the name of vm to create
        :param image_name: the name of image for vm creation
        :param flavor_name: the name of flavor for vm creation
        :param network_name: the name of network for vm creation
        :param scheduler_hints: arbitrary key-value pairs
        such as {"group": server_group_id}
        :param availability_zone: set vm's host
        :param userdata: customization script for vm creation
        such as specify below line in test config
        create_vm_post_script = "#!/bin/bash\npasswd << EOF\nroot\nroot\nEOF\n"
        :returns: nova server instance
        """
        def get_userdatafile(userdata):
            try:
                fileobj = tempfile.mkstemp(dir="/tmp", text=True)
                filename = fileobj[1]
                with open(filename, "wb") as f:
                    f.write(userdata)
                return filename
            except (IOError, OSError) as e:
                LOG.error("Catched an error when try to make userdata.\n%s" % e)

        net = None
        server = None
        _nics = list()
        if not vm_name:
            vm_name = "cloudtest-" + utils_misc.generate_random_string(6)
        if not image_name:
            image_name = "cirros-0.3.4-x86_64-uec"
        image = self.image_client.find(name=image_name)
        if not image:
            raise exceptions.TestSetupFail("Did not find valid image")

        if not flavor_name:
            flavor_name = "2-2048-60"
        flavor = self.flavor_client.find(name=flavor_name)
        if not flavor:
            raise exceptions.TestSetupFail("Did not find specified flavor")

        if (len(nics) == 0) and (not network_name):
            network_name = "cloudtest_net"
        if network_name:
            nets = self.network_utils.list_networks(name=network_name)
            for _k in nets:
                for _v in nets[_k]:
                    if network_name == _v['name']:
                        net = _v
                        break
            if net:
                net.update({"net-id": str(net["id"])})
                _nics.append(net)
        if nics:
            for nic in nics:
                nic['port-id'] = nic['id']
                _nics.append(nic)

        if not admin_pass:
            admin_pass = self.params.get('image_ssh_password', 'root')

        key_name = None
        if self.params.get('image_ssh_auth_method') in 'key':
            if not injected_key:
                key_name = self.get_public_key().name
            else:
                key_name = injected_key.name

        if not sec_group:
            sec_group = self.network_utils.create_secgroup('cloudtest_sg')
            LOG.info('Created security group: %s' % sec_group)

        userdata_handle = None
        if not userdata is None:
            userdata = userdata.replace("\\n", "\n")
            userdata_fname = get_userdatafile(userdata)
            if userdata_fname :
                userdata_handle = open(userdata_fname, "r")
                LOG.info("Create a new instance with userdata.")

        server = self.server_client.create(name=vm_name, image=image.id,
                                           flavor=flavor.id, nics=_nics,
                                           key_name=key_name,
                                           security_groups=[sec_group],
                                           scheduler_hints=scheduler_hints,
                                           availability_zone=availability_zone,
                                           userdata=userdata_handle,
                                           min_count=min_count,
                                           admin_pass=admin_pass)
        if not userdata is None:
            userdata_handle.close()
            os.remove(userdata_fname)

        return server

    def get_host_by_name(self, host_name):
        """
        Get host zone by name.
        :param host_name: like "node-6.domain.tld"
        :return: zone
        """
        host = self.novaclient.hosts.find(host_name=host_name)
        return host

    def create_vm_on_specific_node(self, node_name,
                                   flavor_name=None,
                                   injected_key=None,
                                   nics=[],
                                   network_name=None,
                                   vm_name=None):
        network_name = network_name or self.params.get("network_name")
        host_zone = self.get_host_by_name(host_name=node_name).zone
        availability_zone_str = "%s:%s" % (host_zone, node_name)
        if not vm_name:
            vm_name = "cloudtest-" + utils_misc.generate_random_string(6)
        self.create_vm(
            vm_name=vm_name,
            image_name=self.params.get("image_name"),
            flavor_name=flavor_name,
            injected_key=injected_key,
            network_name=network_name,
            availability_zone=availability_zone_str,
            nics=nics)
        return vm_name

    def create_vms_on_specific_node(self, node_name,
                                   vm_count=1,
                                   flavor_name=None,
                                   injected_key=None,
                                   nics=[],
                                   network_name=None,
                                   vm_name_prefix=None):
        network_name = network_name or self.params.get("network_name")
        host_zone = self.get_host_by_name(host_name=node_name).zone
        availability_zone_str = "%s:%s" % (host_zone, node_name)
        name_list = []
        if vm_name_prefix is None:
            vm_name_prefix = "cloudtest-" + utils_misc.generate_random_string(6)
        for i in range(vm_count):
            vm_name = vm_name_prefix + "-" + str(i)
            name_list.append(vm_name)
            self.create_vm(
                vm_name=vm_name,
                image_name=self.params.get("image_name"),
                flavor_name=flavor_name,
                injected_key=injected_key,
                network_name=network_name,
                availability_zone=availability_zone_str,
                nics=nics)
        if vm_count == 1:
            return vm_name
        return name_list

    def find_vm_from_name(self, vm_name):
        vms = self.server_client.findall(name=vm_name)
        if not vms:
            raise exceptions.VMNotFound("Did not find VM %s" % vm_name)
        return vms[0]

    def find_vm_from_instance_id(self, instance_id):
        return self.server_client.get(instance_id)

    def wait_for_vm_active(self, vm, step=3, timeout=360,
                           delete_on_failure=True):

        end_time = time.time() + timeout

        while time.time() < end_time:
            _vm = self.find_vm_from_name(vm.name)
            if _vm.status == 'ACTIVE':
                return True

            if (_vm.status == 'ERROR'):
                LOG.error("VM (ID: %s name: %s) creation ERROR: %s" % (
                    _vm.id, _vm.name, _vm.fault['message']))
                if delete_on_failure:
                    _vm.delete()
                return False

            LOG.info("VM (ID:%s Name:%s) in status: %s" % (_vm.id, _vm.name,
                                                           _vm.status))
            time.sleep(step)
        else:
            LOG.error("Timeout to build VM: %s" % _vm.name)
            if delete_on_failure:
                _vm.delete()
            return False

    def wait_for_vm_in_status(self, vm, status, step=3, timeout=360,
                              delete_on_failure=False):

        end_time = time.time() + timeout

        while time.time() < end_time:
            _vm = self.find_vm_from_name(vm.name)
            LOG.info("VM (ID:%s Name:%s) in status: %s" % (_vm.id, _vm.name,
                                                           _vm.status))
            if _vm.status == status:
                return True

            if _vm.status == 'ERROR':
                LOG.error("VM ID: %s name: %s in status ERROR!!" % (_vm.id, _vm.name))
                if delete_on_failure:
                    _vm.delete()
                return False

            time.sleep(step)
        else:
            LOG.error("VM (ID: %s name: %s) still not in status: %s"
                      % (_vm.id, _vm.name, status))
            return False

    def get_vm_by_ip(self, vm_ip):
        vms = self.server_client.list()
        vm = None
        for _vm in vms:
            if len(self.server_client.ips(_vm).values()) < 1:
                continue
            ips = self.server_client.ips(_vm).values()[0]
            for ip in ips:
                if vm_ip in ip['addr']:
                    return _vm
        return vm

    def capture_vm_console_log(self, vm):
        file_name = "vm_console_log_%s" % vm.name
        log_file_path = os.path.join(os.environ['AVOCADO_TEST_OUTPUTDIR'],
                                     file_name)
        output = self.server_client.get_console_output(vm)
        LOG.info("Capture console log for VM: %s" % vm.name)
        genio.write_file(log_file_path, output)

    def create_vm_and_wait_for_login(self, vm_name=None, image_name=None,
                                     flavor_name=None, network_name=None,
                                     injected_key=None, sec_group=None,
                                     timeout=360, ssh_username='root'):
        """
        Boot a vm
        :param vm_name: the name of vm to create
        :param image_name: the name of image for vm creation
        :param flavor_name: the name of flavor for vm creation
        :param network_name: the name of network for vm creation
        :returns: nova server instance
        """
        vm = self.create_vm(vm_name=vm_name, image_name=image_name,
                            flavor_name=flavor_name, network_name=network_name,
                            injected_key=injected_key, sec_group=sec_group)

        if not self.wait_for_vm_active(vm):
            return False

        vm_ip = self.assign_floating_ip_to_vm(vm)
        LOG.info("Created vm %s, try to login to it via %s" % (vm, vm_ip))
        session = remote.wait_for_login(client='ssh', host=vm_ip, port='22',
                                        username=ssh_username, password="",
                                        prompt=r"[\#\$]\s*$", timeout=timeout,
                                        use_key=True)
        if session is None:
            return False
        output = session.run('whoami')
        if not ssh_username in output:
            return False
        return True

    @staticmethod
    def wait_for_vm_pingable(vm_ip, timeout=60):
        end_time = time.time() + timeout

        while time.time() < end_time:
            cmd = 'ping -c 1 -i 1 %s' % vm_ip
            stdout_msg = process.run(cmd=cmd, shell=True, ignore_status=True)
            LOG.debug(stdout_msg)
            pat = '(\d+) received'
            result = re.findall(pat, str(stdout_msg))
            if not len(result):
                raise exceptions.TestFail('Msg data or pattern error, '
                                          'please check!')
            else:
                value = int(result[0])
                if value:
                    return True
        else:
            LOG.error('Ping %s failed!' % vm_ip)
            return False

    def start_vm(self, name, timeout=60):
        """
        Start the stopped VM according to name

        :param name: the name of the VM
        :return:
        """
        _vm = self.find_vm_from_name(name)
        _vm.start()
        if self.wait_for_vm_in_status(_vm, 'ACTIVE', timeout=timeout):
            return True
        else:
            return False

    def stop_vm(self, name, timeout=60):
        """
        Stop the VM according to name

        :param name: the name of the VM
        :return:
        """
        _vm = self.find_vm_from_name(name)
        _vm.stop()
        if self.wait_for_vm_in_status(_vm, 'SHUTOFF', timeout=timeout):
            return True
        else:
            return False

    def pause_vm(self, name, timeout=6):
        """
        Pause the running VM according to name

        :param name: the name of the VM
        :return:
        """
        _vm = self.find_vm_from_name(name)
        _vm.pause()
        if self.wait_for_vm_in_status(_vm, 'PAUSED', timeout=timeout):
            return True
        else:
            return False

    def unpause_vm(self, name, timeout=6):
        """
        Unpause the paused VM according to name

        :param name: the name of the VM
        :return:
        """
        _vm = self.find_vm_from_name(name)
        _vm.unpause()
        if self.wait_for_vm_in_status(_vm, 'ACTIVE', timeout=timeout):
            return True
        else:
            return False

    def suspend_vm(self, name, timeout=6):
        """
        Suspend the running VM according to name

        :param name: the name of the VM
        :return:
        """
        _vm = self.find_vm_from_name(name)
        _vm.suspend()
        if self.wait_for_vm_in_status(_vm, 'SUSPENDED', timeout=timeout):
            return True
        else:
            return False

    def resume_vm(self, name, timeout=6):
        """
        Resume the suspended VM according to name

        :param name: the name of the VM
        :return:
        """
        _vm = self.find_vm_from_name(name)
        _vm.resume()
        if self.wait_for_vm_in_status(_vm, 'ACTIVE', timeout=timeout):
            return True
        else:
            return False

    def reboot_vm(self, name, timeout=60):
        """
        Reboot the VM according to name

        :param name: the name of the VM
        :return:
        """
        _vm = self.find_vm_from_name(name)
        _vm.reboot()
        if self.wait_for_vm_in_status(_vm, 'ACTIVE', timeout=timeout):
            return True
        else:
            return False

    def delete_vm(self, name, timeout=6):
        """
        Delete the VM according to name

        :param name: the name of the VM
        """
        LOG.info("Try to delete vm %s" % name)
        self.find_vm_from_name(name).delete()

        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                time.sleep(1)
                vm = self.find_vm_from_name(name)
            except:
                LOG.info("Successfully deleted vm: %s" % name)
                return True
        else:
            return False

    def get_flavor_count(self):
        """
        Retrieve flavor count
        """
        flavors = self.flavor_client.list()
        return len(flavors)

    def get_compute_host_count(self):
        """
        Retrieve compute host count
        """
        return len(self.hosts_client.list(zone="nova"))

    def get_host_vm_list(self, host_name):
        """
        :return: server list of specified host
        """
        search_opts = {}
        search_opts['all_tenants'] = True
        server_list = self.server_client.list(search_opts=search_opts)
        result_list = []
        for server in server_list:
            if getattr(server, 'OS-EXT-SRV-ATTR:host') == host_name:
                result_list.append(server)
        return result_list

    def get_vm_domain_name(self, name):
        instance = self.find_vm_from_name(vm_name=name)
        LOG.info("instance.name is %s" % instance.name)
        return getattr(instance, 'OS-EXT-SRV-ATTR:instance_name')

    def get_server_host(self, name):
        instance = self.find_vm_from_name(vm_name=name)
        LOG.info("instance.name is %s" % instance.name)
        return getattr(instance, 'OS-EXT-SRV-ATTR:host')

    def get_different_host_from(self, host_name):
        host_list = self.hosts_client.list()
        for host in host_list:
            if host.zone != 'internal' and host.host_name != host_name:
                    return host.host_name
        raise exceptions.TestError("No enough host for test")

    def get_host_vm_count(self):
        """
        :return: key: compute node name;value: vm count of this compute
        """
        count_dict = {}
        host_list = self.hypervisor_client.list()
        for host in host_list:
            if host.state in "up":
                count_dict[host.hypervisor_hostname] = host.running_vms
        return count_dict

    def create_server_group(self, policy=None, name=None):
        if not policy:
            policy = 'affinity'
        if not name:
            name = 'group' + utils_misc.generate_random_string(6)
        body = {'policies': [policy],
                'name': name}
        server_group = self.server_group_client.create(**body)
        LOG.info(server_group)
        return server_group

    def find_server_group_from_name(self, group_name):
        groups = self.server_group_client.findall(name=group_name)
        if not groups:
            raise exceptions.ServerGroupNotFound(
                "Did not find server group %s" % group_name)
        return groups[0]

    def delete_server_group(self, name, timeout=6):
        """
        Delete the server group according to name

        :param name: the name of the server group
        """
        self.find_server_group_from_name(name).delete()

        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                time.sleep(1)
                self.find_server_group_from_name(name)
            except exceptions.ServerGroupNotFound:
                return True
        else:
            return False

    def get_all_hypervisors(self):
        """
        Get all available compute node details.
        """
        result_list = []
        host_list = self.novaclient.hypervisors.list()
        for host in host_list:
            if host.state in 'up':
                result_list.append(host)
        return result_list

    def get_service_state(self, host, binary):
        return self.novaclient.services.list(host, binary)

    def disable_service(self, host, binary):
        """
        Disable the service specified by hostname and binary.

        :param host: the hostname
        :param binary: service name, like 'nova-compute'
        """
        result = self.novaclient.services.disable(host, binary)
        if 'disabled' in result.status:
            LOG.info("Successfully disabled '%s' on '%s'" % (binary, host))
            return True
        LOG.error("Failed to disable '%s' on '%s'" % (binary, host))
        return False

    def enable_service(self, host, binary):
        """
        Enable the service specified by hostname and binary.

        :param host: the hostname
        :param binary: service name, like 'nova-compute'
        """
        result = self.novaclient.services.enable(host, binary)
        if 'enabled' in result.status:
            LOG.info("Successfully enabled '%s' on '%s'" % (binary, host))
            return True
        LOG.error("Failed to enable '%s' on '%s'" % (binary, host))
        return False

    def change_host_state(self, host, state):
        req = {'hostname': host, 'state': state}
        auth_url = self.params.get('OS_AUTH_URL')
        nova_endpoint_v1 = ':'.join(auth_url.split(':')[:-1]) + ':9080' + \
                           '/v1/server/change_host'
        r = requests.post(nova_endpoint_v1,
                          json=req, verify=True)
        response = r.json()
        LOG.info('Result of change host state: %s' % response)
        try:
            return_code = response[u'return_code']
        except KeyError as e:
            LOG.error("Exception during changing host '%s' to '%s': %s" %
                                                        (host, state, e))
            return False

        if return_code != 0:
            LOG.error("Failed to change host '%s' to '%s'" % (host, state))
            return False
        LOG.info("Successfully changed host '%s' to '%s'" % (host, state))
        return True

    def lock_compute_node(self, host):
        LOG.info('Try to lock compute node: %s' % host)

        vm_list = self.get_host_vm_list(host_name=host)
        if len(vm_list) > 0:
            host_for_migrate = self.get_different_host_from(host)
            status = self.migrate_host(host=host,
                                       target_host=host_for_migrate)
            if status:
                polling_times = 15
                vm_in_migrating = False
                while polling_times > 0:
                    LOG.info("Waiting for vm migration.")
                    vm_list = self.get_host_vm_list(host_name=host)
                    polling_times = polling_times - 1
                    vm_list_length = len(vm_list)
                    if vm_list_length > 0:
                        for vm in vm_list:
                            if vm.status == "MIGRATING":
                                vm_in_migrating = True
                                break
                        if vm_in_migrating:
                            sleep_interval = 5 * vm_list_length
                            time.sleep(sleep_interval)
                        else:
                            break
                    else:
                        break

                vm_list = self.get_host_vm_list(host_name=host)
                if len(vm_list) == 0:
                    if not self.disable_service(host, 'nova-compute'):
                        return False
                    time.sleep(5)
                    if not self.change_host_state(host, 'Locked'):
                        return False
                else:
                    return False
        return True

    def unlock_compute_node(self, host):
        # Unlock the compute node
        LOG.info('Try to unlock compute node: %s' % host)
        if not self.enable_service(host, 'nova-compute'):
            return False

        time.sleep(7)
        if not self.change_host_state(host, 'Unlocked'):
            return False
        time.sleep(3)
        return True

    def recovery_pssr(self, physerver, dev, provider_network, mtu=None):
        req = dict()
        nic = self.pssr_mgr.pssr_get_intf_conf(physerver, dev)._info['results']
        req['physerver'] = physerver
        req['physerver_ip'] = ''
        req['name'] = nic['nic_id']
        req['provider_networks'] = [provider_network]
        req['ports'] = [nic['ports']]
        req['network_type'] = 'none'
        req['last_network_type'] = nic['network_type']
        req['type'] = 'ethernet'
        req['vfnum'] = 0
        if mtu:
            req['mtu'] = mtu

        if not self.lock_compute_node(physerver):
            return False

        res = self.pssr_mgr.pssr_conf(req)
        LOG.info('Got PSSR configuration result: \n%s' % res.__dict__)
        if type(res.results) == dict:
            if 'success' in res.results['status']:
                LOG.info("Successfully recovery '%s' on '%s'" % (dev,
                                                                 physerver))
        else:
            LOG.error("Failed to recovery '%s' on '%s'" % (dev, physerver))

        # Unlock the compute node
        if not self.unlock_compute_node(physerver):
            return False
        return True

    def setup_pssr(self, network_type, provider_network,
                   physerver=None, dev=None, vfnum=None, mtu=None):
        """
        Set up nic PCI-passthrough (SR-IOV or physical nic) on compute node.
        If no physerver is specified, we will try to find one.

        The request for pci-sriov will look like below:

        setup_req = {'physerver_ip': '192.168.20.6',
                     'name': 'eth3',
                     'provider_networks': ['physnet2'],
                     'physerver': 'node-4.domain.tld',
                     'ports': ['eth3'],
                     'vfnum': 4,
                     'network_type': 'pci-sriov'}

        :param network_type: pci-sriov, pci-passthrough
        :param physerver: compute node hostname
        :param dev: the device name, like 'eth3'
        """
        self.pssr_mgr = self.novaclient.pssr
        setup_req = {}
        supported_nic = None
        pssr_resource = {}

        if not physerver and not dev:
            LOG.info('Try to find one pssr nic to setup')
            all_computes = self.get_all_hypervisors()

            if network_type == 'pci-sriov':
                support_type = 'pci_sriov_supported'
            elif network_type == 'pci-passthrough':
                support_type = 'pci_passthrough_supported'
            else:
                LOG.error('Unsupported network type to setup PSSR')
                return pssr_resource

            for com in all_computes:
                nics = self.pssr_mgr.pssr_get_intfs(
                        com.hypervisor_hostname)._info['results']

                for nic in nics:
                    if nic[support_type] in 'yes' and \
                       nic['support_config'] in 'yes':
                        # We got one host:nic pair available
                        pssr_resource['host'] = com.hypervisor_hostname
                        pssr_resource['nic'] = nic['name']

                        setup_req['physerver'] = com.hypervisor_hostname
                        setup_req['physerver_ip'] = com.host_ip
                        setup_req['name'] = nic['nic_id']
                        setup_req['provider_networks'] = [provider_network]
                        setup_req['ports'] = [nic['ports']]
                        if network_type == 'pci-sriov':
                            setup_req['vfnum'] = int(vfnum)
                        elif network_type == 'pci-passthrough':
                            setup_req['vfnum'] = 0
                        setup_req['network_type'] = network_type
                        setup_req['last_network_type'] = nic['last_network_type']
                        if mtu:
                            setup_req['mtu'] = mtu
                        physerver = com.hypervisor_hostname
                        dev = nic['name']
                        break

            if not pssr_resource:
                LOG.error("Could not automatically find host:nic pair for pssr test")
                return pssr_resource
        else:
            # Set up the specified dev on specified physerver
            nic = self.pssr_mgr.pssr_get_intf_conf(physerver, dev)._info['results']
            setup_req['physerver'] = physerver
            setup_req['physerver_ip'] = ''
            setup_req['name'] = nic['nic_id']
            setup_req['provider_networks'] = [provider_network]
            setup_req['ports'] = [nic['ports']]
            if network_type == 'pci-sriov':
                setup_req['vfnum'] = int(vfnum)
            elif network_type == 'pci-passthrough':
                setup_req['vfnum'] = 0
            setup_req['network_type'] = network_type
            setup_req['last_network_type'] = nic['network_type']
            setup_req['mtu'] = mtu

            pssr_resource['host'] = physerver
            pssr_resource['nic'] = nic['nic_id']

        # We need to Lock the physical server:
        # 1) disable the nova-compute service
        # 2) change hypervisor to state by nova/v1/change_host REST interface
        if not self.lock_compute_node(physerver):
            return False

        # Setup nic as SR-IOV
        LOG.info("Request to configure PSSR: %s" % setup_req)
        res = self.pssr_mgr.pssr_conf(setup_req)
        LOG.info('Got PSSR configuration result: \n%s' % res.__dict__)
        if type(res.results) == dict:
            if 'success' in res.results['status']:
                LOG.info("Successfully setted up '%s' on '%s'" % (dev,
                                                                  physerver))
        elif 'config fail,network have been config' in res.results:
            LOG.info('Network have been configured')
        else:
            LOG.error("Failed to setup '%s' on '%s'" % (dev, physerver))
            return False

        if not self.unlock_compute_node(physerver):
            return False

        return pssr_resource

    def attach_volume(self, server_id, volume_id, device=None):
        self.volume_client.create_server_volume(server_id, volume_id, device)

        if self.volume_utils.wait_for_volume_status(volume_id, 'in-use'):
            return True
        else:
            return False

    def detach_volume(self, server_id, volume_id):
        self.volume_client.delete_server_volume(server_id, volume_id)

        if self.volume_utils.wait_for_volume_status(volume_id, 'available'):
            return True
        else:
            return False

    def live_migrate(self, server_id, target_host, block_migration=None):
        if block_migration is None:
            block_migration = False
            disk_over_commit = False
        else:
            disk_over_commit = True

        self.server_client.live_migrate(server=server_id, host=target_host,
                                        block_migration=block_migration,
                                        disk_over_commit=disk_over_commit)

    def cold_migrate(self, server, revert=False):
        self.server_client.migrate(server.id)

        if not self.wait_for_vm_in_status(server, 'VERIFY_RESIZE'):
            raise exceptions.TestFail('After cold migrate, '
                                      'the status of instance %s is not '
                                      'VERIFY_RESIZE.')

        if revert:
            self.server_client.revert_resize(server.id)
        else:
            self.server_client.confirm_resize(server.id)

        if not self.wait_for_vm_active(server):
            raise exceptions.TestFail('After resize, '
                                      'the status of instance %s is not '
                                      'ACTIVE.')

    def migrate_host(self, host, target_host):
        """
        Migrate all the vm on host.
        """
        hypervisors = self.hypervisor_client.search(host, True)
        for hyper in hypervisors:
            for server in getattr(hyper, 'servers', []):
                # server = {"uuid": "", "name": "instance-"}
                try:
                    instance = self.find_vm_from_instance_id(server['uuid'])
                    if instance.status in ('ACTIVE', 'PAUSED'):
                        self.live_migrate(server['uuid'], target_host=target_host)
                    else:
                        self.cold_migrate(instance)
                except exceptions.RestClientException:
                    return False

        return True

    def get_host_from(self, filter_key=None, filter_value=None):
        """
        Get host object according to key-value filter.

        :param filter_key: could be 'zone', 'service', 'host_name', etc
        :param filter_value: string value
        """
        hosts = self.novaclient.hosts.list()
        if not filter_key and not filter_value:
            return hosts
        for host in hosts:
            if getattr(host, filter_key) in filter_value:
                return host
        LOG.error('Did not find host according to (%s:%s)' % (
                                    filter_key, filter_value))

    def get_quotas(self, tenant_id):
        return self.quotas_client.get(tenant_id)

    def get_quota_values(self, quota_list):
        if not quota_list:
            return
        curr_quotas = {}
        cmd = 'openstack quota show -f json'
        quotas = process.run(cmd).stdout
        quotas = json.loads(quotas)
        for k in quota_list:
            curr_quotas[k] = quotas[k]
        return curr_quotas

    def update_quotas(self, expected_quota):
        cmd = 'openstack quota set --{0} {1} admin'
        for k, v in expected_quota.iteritems():
            process.run(cmd.format(k, v))

    def get_usage(self, tenant_id, start, end):
        return self.usage_client.get(tenant_id, start, end)

    def get_limits(self, tenant_id):
        return self.limits_client.get(tenant_id=tenant_id)

    def create_snapshot(self, vm, image_name=None, metadata=None):
        _vm = self.find_vm_from_name(vm.name)
        if not _vm:
            LOG.error("Cannot find vm %d to create snapshot!" % vm.name)
            return None
        if not image_name:
            image_name = "cloudtest_" + utils_misc.generate_random_string(6)

        image_id = self.server_client.create_image(_vm, image_name, metadata)
        image = self.image_client.get(image_id)
        if self.wait_for_image_in_status(image, 'ACTIVE'):
            LOG.info("Created snapshot successfully: %s" % image)
            return image

    def wait_for_image_in_status(self, image, status, step=3, timeout=360):

        end_time = time.time() + timeout

        while time.time() < end_time:
            _image = self.image_client.find(name=image.name)
            LOG.info("Image (ID:%s Name:%s) in status: %s" % (_image.id, _image.name, _image.status))
            if _image.status == status:
                return True

            time.sleep(step)
        else:
            LOG.error("Image (ID: %s name: %s) failed to in status %s!!"
                      % (_image.id, _image.name, status))
            return False

    def get_hypervisor_statistics(self):
        """
        Get hypervisor statistics over all compute nodes.
        :return:
        """
        stats = self.hypervisor_client.statistics()
        LOG.info("Hypervisor statistics over all compute nodes: %s"
                 % stats.__dict__)
        return stats

    def get_vm_ipaddr(self, vmname):
        vm = self.find_vm_from_name(vmname)
        _nics = vm.addresses[self.params["network_name"]]
        vm_local_addr = None
        vm_fip_addr = None
        for _nic in _nics:
           if _nic["OS-EXT-IPS:type"] == "fixed":
              vm_local_addr = _nic.get("addr", None)
           if _nic["OS-EXT-IPS:type"] == "floating":
              vm_fip_addr = _nic.get("addr", None)
        if vm_local_addr is not None:
            ipaddr = {"fixed": vm_local_addr}
        if vm_fip_addr is not None:
            ipaddr.update({"floating": vm_fip_addr})
        return ipaddr

if __name__ == '__main__' :
#    params = {
#        "OS_PASSWORD" : "123qweasd",
#        "OS_TENANT_NAME" : "tempest_proj",
#        "OS_USERNAME" : "tempest_user",
#        "OS_AUTH_URL" : "http://192.168.0.2:5000/v2.0"
#        #"OS_AUTH_URL" : "http://192.168.0.2/identity_admin"
#    }
    params = {
        "OS_PASSWORD" : "123456",
        "OS_TENANT_NAME" : "pk_3_proj",
        "OS_USERNAME" : "pk_3_admin",
        "OS_AUTH_URL" : "http://10.100.3.61:5000/v2.0"
        #"OS_AUTH_URL" : "http://192.168.0.2/identity_admin"
    }
    client = Compute(params)
    client.get_compute_host_count()
