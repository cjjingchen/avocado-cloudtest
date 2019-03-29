# Copyright: Lenovo Inc. 2016~2017
# Author: Yingfu Zhou <zhouyf6@lenovo.com>


import random
import logging
import requests

from avocado.utils import process
from cloudtest import utils_env
from cloudtest import remote
from cloudtest.openstack import cloud_node

LOG = logging.getLogger('avocado.test')


class CloudManager(object):
    """
    The module for Cloud management.
    """
    def __init__(self, params, env):
        self.params = params
        self.env = env
        self._nodes = self.discover_nodes()

    @property
    def nodes(self):
        return sorted(self._nodes)

    def __len__(self):
        return len(self._nodes)

    def get_host_list(self):
        auth_url = self.params.get('OS_AUTH_URL')
        nova_endpoint_v1 = ':'.join(auth_url.split(':')[:-1]) + ':9080' \
                           + '/v1/server/list_hosts'
        r = requests.get(nova_endpoint_v1, verify=True)
        response = r.json()
        try:
            return_code = response[u'return_code']
        except KeyError as e:
            LOG.error("Exception during get host list : %s" % e)
            return []

        if return_code != 0:
            LOG.error("Failed to get host list!")
            return []
        LOG.debug("Successfully get host list: %s " % response[u'return_data'])
        return response[u'return_data']

    def __parse_role_names(self, host):
        role_names = []
        mask = host.get('roles', 0)
        if mask & 256 != 0:
            role_names.append('controller')
        if mask & 512 != 0:
            role_names.append('compute')
        if mask & 1024 != 0:
            role_names.append('cinder')
        if mask & 2048 != 0:
            role_names.append('ceph-osd')
        if mask & 4096 != 0:
            role_names.append('mongo')
        if mask & 8192 != 0:
            role_names.append('storage')
        return role_names

    def discover_nodes(self):
        LOG.info("Discovering nodes...")
        return_data = self.get_host_list()
        node_list = []
        for datum in return_data:
            host_datum = datum.get('IMM')
            host_roles = self.__parse_role_names(host_datum)
            host_ip = host_datum['hostip']
            host_name = host_datum['hostname']
            host_status = 'down'
            if host_datum['power'] == 'on':
                host_status = 'ready'
            node = self.env.get_cloud_node(host_name)
            if node:
                node_list.append(node)
            else:
                node = cloud_node.CloudNode(host_name, host_roles,
                                            host_status, host_ip)
                LOG.info("Discovered node: %s" % node.__dict__)
                self.env.register_cloud_node(node)
                node_list.append(node)

        return node_list

    def random_select(self, source, count=1):
        if count > len(source):
            raise Exception("Select count out of range")
        return random.sample(source, count)

    def filter_by_service_name(self, nodes, service_name):
        affected_nodes = []
        if service_name is not None:
            for node in nodes:
                for s in node.cloud_services:
                    if service_name in s.get('name'):
                        # match server_name in the node
                        affected_nodes.append(node)
        else:
            affected_nodes = nodes
        return affected_nodes

    def filter_by_role(self, nodes, role=None):
        affected_nodes = []
        if role is not None:
            for node in nodes:
                if role in node.role:
                    affected_nodes.append(node)
        else:
            affected_nodes = nodes
        return affected_nodes

    def filter_by_status(self, nodes, status=None):
        affected_nodes = []
        if status is not None:
            for node in nodes:
                if status in node.status:
                    affected_nodes.append(node)
        else:
            affected_nodes = nodes
        return affected_nodes

    def filter_nodes(self, nodes, **kwargs):
        affected_nodes = nodes
        for k in kwargs:
            fun = "self.filter_by_%s" % k
            affected_nodes = eval(fun)(affected_nodes, kwargs[k])
        return affected_nodes

    def get_nodes(self, node_role=None, service_name=None, select_policy=None,
                 node_status=None):
        """
        Get node according to specified condition.

        :param node_role: the type of node, could be 'compute' or 'controller'
        :param service_name: the service name to be selected
        :param select_policy: how to select a node, could be 'random', 'all'
        :param node_status: the status of node, could be 'ready' or 'error'

        :return: node hostname or IP
        """
        affected_nodes = []
        affected_nodes = self.filter_nodes(nodes=self.nodes, status=node_status,
                                           role=node_role, service_name=service_name)

        if not select_policy is None:
            if select_policy in 'random' and len(affected_nodes) > 1:
                return self.random_select(affected_nodes, 1)
        return affected_nodes

    def act_to_service(self, act, service_name, select='random', count=1):
        """
        Take action on a service via 'systemctl' command in the cloud.

        :param act: the systemctl action
        :param service_name: the name of the service
        """
        rets = []
        target_nodes = self.get_nodes(service_name=service_name)
        if select in 'random':
            nodes = self.random_select(target_nodes, count)
        for node in nodes:
            rets.append(node.act_to_service(act, service_name))
        return all(rets), nodes

    def act_to_net(self, interface_name, action,
                   act=None, select='random', count=1):
        """
        Take action on node.
        :param interface_name:
        :param action: when act is None action value down/up else add/change/del
        :param act: fault_action
        :return:
        """
        rets = []
        nodes = self.filter_by_role(self.nodes, role='controller')
        # if select in 'random':
        #     nodes = self.random_select(self.nodes, count)
        if act is None:
            rets.append(nodes[0].act_to_network(interface_name, action))
        else:
            rets.append(nodes[0].traffic_control(act, interface_name, action))
        return all(rets), nodes

    def act_to_process(self, act, service_name, fault_scale='random', select='random', count=1):
        """
        Take action on pids of the specified service
        :param act: the signal action to pid
        :param service_name: the name of the service
        :param fault_scale: the scale of fault, include random, primary, all-except-one
        :return:
        """
        rets = []
        nodes_service_infos = self.get_nodes_service_info(service_name, select, count)
        for node_service_info in nodes_service_infos:
            pids = []
            node = node_service_info['node']
            service_info = node_service_info['service_info']
            child_pcount = len(service_info["child_pids"])
            if fault_scale in 'random':
                if child_pcount > 1:
                    pid_count = random.randint(1, child_pcount - 1)
                    pids = self.random_select(service_info["child_pids"], pid_count)
                elif child_pcount == 1:
                    pids = service_info["child_pids"]
                elif child_pcount == 0:
                    pids.append(service_info["main_pid"])
            elif fault_scale in 'primary':
                pids.append(service_info["main_pid"])
            else:
                pids = service_info["child_pids"]
            rets.append(node.act_to_process(act, pids))

        return all(rets)

    def get_nodes_service_info(self, service_name, select='random', count=1):
        all_nodes = self.get_nodes(service_name=service_name)
        nodes_service_infos = []
        if select in 'random':
            target_nodes = self.random_select(all_nodes, count)
        else:
            target_nodes = all_nodes
        for node in target_nodes:
            service_info = node.get_service_info(service_name=service_name)
            node_service_info = {'node': node, 'service_info': service_info}
            nodes_service_infos.append(node_service_info)

        return nodes_service_infos

    def act_to_iptables(self, act, service_name, select='random', count=1):
        """
        Take action on iptables

        :param act: the iptables action, it's a dict
        :param service_name: the name of the service
        """
        rets = []
        target_nodes = self.get_nodes(service_name=service_name)
        if select in 'random':
            nodes = self.random_select(target_nodes, count)
        for node in nodes:
            rets.append(node.act_to_iptables(act))
        return all(rets), nodes

    def get_compute_node(self, select_policy='random'):
        return self.get_nodes(node_role='compute', service_name=None,
                              select_policy=select_policy, node_status='ready')

    def get_controller_node(self, select_policy='random'):
        return self.get_nodes(node_role='controller', service_name=None,
                              select_policy=select_policy, node_status='ready')

if __name__ == '__main__':
    params = {'service_name': 'openstack-keystone', 'fault_injection_type': 'random',
              'OS_AUTH_URL': 'http://192.168.50.2:5000/v2.0/'}
    try:
        env = utils_env.Env(filename='/tmp/cloud_env')
        cm = CloudManager(params, env)
        role = params.get("fault_node_type")
        select_policy = params.get("fault_injection_type")
        service_name = params.get("service_name")
        injection_nodes = cm.get_nodes(role, service_name, select_policy)
        print "injection_nodes:%s" % injection_nodes[0].__dict__
        # cm.restart_service('openstack-nova-api')
    finally:
        env.save()
