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


import logging

import os_client_config

from avocado.utils import process
from cloudtest import utils_misc
from common import Common
from keystone import Keystone
from avocado.core import exceptions

LOG = logging.getLogger('avocado.test')


class Network(Common):
    SUBNET_IP_VERSION = 4

    def __init__(self, params):
        super(Network, self).__init__(params)
        self.params = params
        self.client = os_client_config.make_client(
            'network', **self.neutron_credential)
        self.keystoneclient = Keystone(params)

    def list_networks(self, **kwargs):
        """
        Get a list of all networks
        :returns: objects of all networks
        """
        return self.client.list_networks(**kwargs)

    def create_subnet(self, network, subnet_create_args=None, start_cidr=None):
        """
        Create a subnet
        :param network: where the subnet will be in
        :param subnet_create_args: detailed args for subnet in dict
        :param start_cidr: IP range
        :returns: subnet object
        """
        network_id = network["network"]["id"]
        if ((subnet_create_args is None) or
                (not subnet_create_args.get("cidr"))):
            start_cidr = start_cidr or "10.0.0.0/24"
            subnet_create_args = {
                "cidr": start_cidr
            }
        subnet_create_args["network_id"] = network_id
        subnet_create_args["name"] = network["network"]["name"] + "_subnet"
        subnet_create_args.setdefault("ip_version", self.SUBNET_IP_VERSION)
        return self.client.create_subnet(
            {"subnet": subnet_create_args})

    def get_network(self, network_name=None):
        """
        Get an object that is :class:'Network'
        :param network_name: the name of the network want to get
        :returns: the object of :class: 'Network'
        """
        if network_name is not None:
            net = self.client.list_networks(name=network_name)
            LOG.info('Found network: %s' % net)
            if net['networks']:
                return net['networks'][0]
            return {}
        else:
            LOG.error('Try to find all networks...')
            return self.client.list_networks()['networks']

    def create_network(self, name_prefix='cloudtest_', name=None,
                       subnet=None, start_cidr=None,
                       project=None,
                       provider_network_type=None,
                       provider_segmentation_id=None,
                       provider_physical_network=None,
                       shared=True):
        """
        Create a network
        if create provider network ,you need give all params of this function
        if create tenant network , you should not set provider* params
        :param name_prefix: the prefix name of the network name
        :param name: the network name. when this param has value
                     param name_prefix will not work
        :param subnet: whether or not to create subnet
        :param provider_network_type: flat, vlan, vxlan, or gre
        :param start_cidr: IP range
        :returns: object of :class: 'Network'
        """
        if not name:
            net_name = name_prefix + utils_misc.generate_random_string(6)
        else:
            net_name = name

        net_info = {'name': net_name,
                    'admin_state_up': True}

        # Check if create a network via admin
        if provider_network_type:
            net_info['provider:network_type'] = provider_network_type
        if provider_segmentation_id:
            net_info['provider:segmentation_id'] = int(provider_segmentation_id)
        if provider_physical_network:
            net_info['provider:physical_network'] = provider_physical_network

        if shared is not None:
            net_info['shared'] = shared

        req = {'network': net_info}
        LOG.info('Try to create network with request: \n%s' % req)
        response_net = self.client.create_network(body=req)

        if response_net is not None and subnet:
            subnet = self.create_subnet(network=response_net,
                                        start_cidr=start_cidr)
            response_net["subnet"] = subnet
        return response_net

    def delete_network(self, name=None, network_id=None):
        if not any([name, network_id]):
            LOG.error('Please specify name or id to delete')
            return False

        if name is not None:
            net = self.get_network(name)
            if net:
                network_id = net['id']
        LOG.info('Try to delete network: %s' % network_id)
        return self.client.delete_network(network_id)

    def delete_port(self, port_id):
        LOG.info("Try to delete port %s" % port_id)
        return self.client.delete_port(port_id)

    def create_provider_network(self, name, project=None,
                                provider_network_type='vlan',
                                provider_segmentation_id=None,
                                provider_physical_network=None,
                                shared=True,
                                subnet=None):
        """
        Create a provider network.

        :param name: the name of provider network
        :param network_type: flat, vlan, vxlan, gre
        """
        network = {'name': name,
                   'admin_state_up': True,
                   'provider:physical_network': provider_physical_network,
                   'provider:network_type': provider_network_type,
                   'shared': shared}

        if provider_segmentation_id is not None:
            network['provider:segmentation_id'] = provider_segmentation_id

        return self.client.create_network({'network': network})

    def get_network_id(self, network_name):
        """
        Get network id
        :param network_name: the name of the network want to get
        :returns: the id of the network
        """
        net_id = None
        net = self.get_network(network_name)
        if net is not None:
            net_id = net['id']
        return net_id

    def get_subnet(self, name=None):
        subnet = self.client.list_subnets(name=name)
        if subnet:
            return subnet['subnets'][0]
        return {}

    def update_subnet(self, name, action, to_name=None, allocation_start=None,
                      allocation_end=None, dns_nameserver=None):
        """
        Update the configuration of the subnet

        :param action: set or unset
        """
        subnet_id = self.get_subnet(name)['id']
        cmd = 'openstack subnet %s' % action
        if to_name:
            cmd += ' --name %s' % to_name

        if allocation_start and allocation_end:
            cmd += ' --allocation-pool start=%s,end=%s' % (allocation_start,
                                                           allocation_end)
        if dns_nameserver:
            cmd += ' --dns-nameserver %s' % dns_nameserver
        cmd += ' %s' % subnet_id

        result = process.run(cmd, shell=True, verbose=True, ignore_status=True)
        if result.exit_status != 0:
            if "object is not iterable" not in result.stderr:
                LOG.error('Failed to update subnet %s: %s' % (name,
                                                              result.stderr))
                return False
        return True

    def create_port(self, name, network_name=None, network_id=None,
                    security_group=None, binding_vnic_type=None):
        """
        Create a port(vNIC)
        :param name_prefix: the prefix name of the port name
        :param name: the port name. when this param has value
                     param name_prefix will not work
        :param network_id: network id
        :param binding_vnic_type: the type of vNIC which this port should be
                                  attached to, can be: normal, macvtap, direct,
                                  direct-physical
        :return: DictWithMeta object
        """
        if network_name is not None and network_id is None:
            net_id = self.get_network_id(network_name)
            if net_id is None:
                raise exceptions.TestError('Failed to get ID of network: %s' %
                                           network_name)
        elif network_id is not None:
            net_id = network_id

        port_info = {'name': name,
                     'admin_state_up': True,
                     'network_id': net_id}

        if security_group:
            sgs = [self.get_security_group_id(security_group)]
            port_info['security_groups'] = sgs
        else:
            sgs = [self.create_secgroup()]
            port_info['security_groups'] = sgs

        if binding_vnic_type:
            port_info['binding:vnic_type'] = binding_vnic_type

        req = {'port': port_info}
        LOG.info("Request to create port: %s" % req)
        port = self.client.create_port(body=req)
        ports = self.client.list_ports()
        for port in ports['ports']:
            if name in port['name']:
                LOG.info("Created port: %s" % port)
                return port
        LOG.error('Failed to create port: %s' % name)
        return False

    def get_router(self, router_name, project_id=None):
        """
        Get router object
        :param router_name: the name of the router to get
        :param project_id: which the project the router belongs to
        :returns: the router object
        """
        routers = self.client.list_routers(name=router_name)['routers']
        if routers:
            LOG.info('Found router: %s; ID:%s' % (routers[0]['name'],
                                                  routers[0]['id']))
            return routers[0]
        LOG.error('Did not find router: %s' % router_name)
        return ""

    def get_router_id(self, router_name, project_id=None):
        """Get the router id

        :param router_name: the name of the router to get
        :param project_id: which the project the router belongs to
        :returns: the router object
        """
        router_id = None
        router = self.get_router(router_name, project_id)
        if router is not None:
            router_id = router['id']
        return router_id

    def create_router(self, name, external_gw=False, subnet_name=None):
        """Create neutron router.

        :param router_create_args: POST /v2.0/routers request options
        :returns: neutron router dict
        """
        req = dict()
        req['name'] = name

        if external_gw:
            for network in self.client.list_networks()["networks"]:
                if network.get("router:external"):
                    LOG.info('Found external network: %s' % network['name'])
                    external_network = network
                    gw_info = {"network_id": external_network["id"],
                               "enable_snat": True}
                    if subnet_name is not None:
                        subnet = self.get_subnet(subnet_name)
                        fip = self.get_free_floating_ips()[-1].get(
                            'floating_ip_address')
                        external_fixed_ips = {'ip_address': fip,
                                              'subnet_id': subnet['id']}
                        gw_info['external_fixed_ips'] = [external_fixed_ips]

                    req.setdefault("external_gateway_info", gw_info)
        LOG.info('Try to create router with request: %s' % req)

        return self.client.create_router({"router": req})

    def router_gateway_clear(self, router_id):
        cmd = 'neutron router-gateway-clear %s' % router_id
        result = process.run(cmd, shell=True, ignore_status=True)
        return 'Removed gateway from router' in result.stdout

    def router_subnet_remove(self, router_id, subnet_id):
        """
        Remove subnet from router
        """
        LOG.info("Try to delete subnet '%s' from router: %s" % (subnet_id,
                                                                router_id))
        cmd = "openstack router remove subnet %s %s" % (router_id, subnet_id)
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status != 0:
            LOG.error('Failed to delete subnet from router %s: %s' %
                      (router_id, result.stderr))
            return False
        return True

    def delete_router(self, name, subnet_name=None):
        router = self.get_router(name)
        external_info = router['external_gateway_info']['external_fixed_ips']
        if external_info:
            self.router_gateway_clear(router['id'])
        if subnet_name:
            self.router_subnet_remove(router['id'],
                                      self.get_subnet(subnet_name)['id'])
        LOG.info('Try to delete router: %s' % name)
        return self.client.delete_router(router['id'])

    def add_interface_router(self, network_name, router_name):
        """Connect subnet to router.

        :param network_name: network name that have one subnet at least
        :param router_name: router name
        """
        LOG.info("Try to connect '%s' to router '%s'" % (network_name,
                                                         router_name))
        router = None
        router = self.get_router(router_name)
        LOG.info('Got router: %s' % router)
        net = self.get_network(network_name)
        self.client.add_interface_router(router["id"],
                                         {"subnet_id": net["subnets"][0]})

    def get_security_group_id(self, sg_name):
        sec_groups = self.client.list_security_groups()
        if not sec_groups:
            return self.create_secgroup(sg_name)
        sec_groups = sec_groups['security_groups']
        for sg in sec_groups:
            if sg.get('name') == sg_name:
                return sg.get('id')
        return ""

    def create_secgroup(self, name='cloudtest_sg'):
        """
        Create a security group

        :param name: the name for security group
        :returns: security group object
        """
        sg_new = True
        sec_groups = self.client.list_security_groups()
        if sec_groups:
            sec_groups = sec_groups['security_groups']
        for sg in sec_groups:
            if sg.get('name') == name:
                sg_new = False
                return sg.get('id')

        if sg_new:
            result = self.client.create_security_group(
                {"security_group": {"name": name,
                                    "description": "CloudTest security group"}})
            created_sg = result.get('security_group').get('id').encode()
            LOG.info("Created security group: %s" % created_sg)
            self.create_secgroup_rule_ssh(created_sg)
            self.create_secgroup_rule_icmp(created_sg)
            return created_sg

    def create_secgroup_with_no_rule(self, name='cloudtest_sg'):
        """
        Create a security group

        :param name: the name for security group
        :returns: security group object
        """
        sg_new = True
        sec_groups = self.client.list_security_groups()
        if sec_groups:
            sec_groups = sec_groups['security_groups']
        for sg in sec_groups:
            if sg.get('name') == name:
                sg_new = False
                return sg.get('id')

        if sg_new:
            result = self.client.create_security_group(
                {"security_group": {"name": name,
                                    "description": "CloudTest security group"}})
            created_sg = result.get('security_group').get('id').encode()
            LOG.info("Created security group: %s" % created_sg)
            return created_sg

    def create_secgroup_rule_icmp(self, secgroup_id):
        """
        Create security icmp rule
        :param secgroup_id: the id of security group
        :returns: security group rule objects
        """
        result_in = self.client.create_security_group_rule(
            {"security_group_rule":
                 {"direction": "ingress",
                  "protocol": "icmp",
                  "description": "",
                  "remote_ip_prefix": "0.0.0.0/0",
                  "security_group_id": secgroup_id
                  }}
        )
        result_e = self.client.create_security_group_rule(
            {"security_group_rule":
                 {"direction": "egress",
                  "protocol": "icmp",
                  "description": "",
                  "remote_ip_prefix": "0.0.0.0/0",
                  "security_group_id": secgroup_id
                  }}
        )
        return result_in, result_e

    def create_secgroup_rule_icmp_cidr(self, secgroup_id, cidr="0.0.0.0/0"):
        """
        Create security icmp rule
        :param secgroup_id: the id of security group
        :returns: security group rule objects
        """
        result_in = self.client.create_security_group_rule(
            {"security_group_rule":
                 {"direction": "ingress",
                  "protocol": "icmp",
                  "description": "",
                  "remote_ip_prefix": cidr,
                  "security_group_id": secgroup_id
                  }}
        )
        result_e = self.client.create_security_group_rule(
            {"security_group_rule":
                 {"direction": "egress",
                  "protocol": "icmp",
                  "description": "",
                  "remote_ip_prefix": cidr,
                  "security_group_id": secgroup_id
                  }}
        )
        return result_in, result_e

    def create_secgroup_rule_ssh(self, secgroup_id):
        """
        Create security ssh rule
        :param secgroup_id: the id of security group
        :returns: security group rule object
        """
        result = self.client.create_security_group_rule(
            {"security_group_rule":
                 {"direction": "ingress",
                  "protocol": "tcp",
                  "description": "",
                  "port_range_max": 22,
                  "remote_ip_prefix": "0.0.0.0/0",
                  "security_group_id": secgroup_id,
                  "port_range_min": 22
                  }}
        )
        return result

    def create_secgroup_rule_http(self, secgroup_id):
        """
        Create security http rule
        :param secgroup_id: the id of security group
        :returns: security group rule object
        """
        result = self.client.create_security_group_rule(
            {"security_group_rule":
                 {"direction": "ingress",
                  "protocol": "tcp",
                  "description": "",
                  "port_range_max": 80,
                  "remote_ip_prefix": "0.0.0.0/0",
                  "security_group_id": secgroup_id,
                  "port_range_min": 80
                  }}
        )
        return result

    def create_secgroup_rule_mysql(self, secgroup_id):
        """
        Create security mysql rule
        :param secgroup_id: the id of security group
        :returns: security group rule object
        """
        result = self.client.create_security_group_rule(
            {"security_group_rule":
                 {"direction": "ingress",
                  "protocol": "tcp",
                  "description": "",
                  "port_range_max": 3306,
                  "remote_ip_prefix": "0.0.0.0/0",
                  "security_group_id": secgroup_id,
                  "port_range_min": 3306
                  }}
        )
        return result

    def get_secgroup(self, secgroup_name):
        """
        Get an object that is security group

        :param secgroup_name: the name of the security group want to get
        :returns: the object of security group
        """
        secg = None
        secgs = self.client.list_security_groups()
        for v in secgs["security_groups"]:
            if secgroup_name == v["name"]:
                secg = v
                break
        return secg

    def del_security_group(self, security_group_id):
        self.client.delete_security_group(security_group_id)

    def create_floating_ip(self, network_id=None):
        if not network_id:
            nets = self.client.list_networks()
            for _k in nets:
                for _v in nets[_k]:
                    if 'public_net' == _v['name']:
                        net = _v
                        break
            if not net:
                raise Exception(
                    "Miss to specify network or can not to get network")
            else:
                network_id = net['id']
        req = {'floatingip': {'floating_network_id': network_id}}
        response_fip = self.client.create_floatingip(body=req)
        LOG.info("Successfully created floating ip: %s"
                 % response_fip['floatingip']['floating_ip_address'])
        return response_fip

    def delete_floating_ip(self, floatingip_id):
        LOG.info('Start to delete floating %s' % floatingip_id)
        return self.client.delete_floatingip(floatingip_id)

    def get_free_floating_ips(self, tenant_id=None):
        """
        Fetches a list of all floatingips which are free to use

        :return: a list of free floating ips
        """
        if not tenant_id:
            tenant = self.keystoneclient.get_tenant('admin')
            tenant_id = tenant.id
        fip_list = self.client.list_floatingips().get('floatingips')
        free_ips = [ip for ip in fip_list
                    if (ip.get('fixed_ip_address') == None
                        and ip.get('router_id') == None
                        and ip.get('tenant_id') == tenant_id)]
        LOG.debug("Got free floating ip list: %s" % free_ips)
        if len(free_ips) < 1:
            LOG.info("There is not enough free floating ip, try to create one")
            fip = self.create_floating_ip().get('floatingip')
            if not fip:
                raise Exception("There is not enough free floating ip!")
            else:
                free_ips.append(fip)
        return free_ips
