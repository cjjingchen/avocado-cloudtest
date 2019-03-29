import logging
import time
import re

from avocado.core import test
from avocado.core import exceptions
from cloudtest import remote
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib.servers_client import ServersClient
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.node_info_client import NodeInfoClient

LOG = logging.getLogger('avocado.test')


class TestServers(test.Test):
    """
    Servers related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.body = {}
        self.env = env
        self.cluster_id = ""
        self.controller_username = self.params.get('ceph_server_ssh_username')
        self.controller_password = self.params.get('ceph_server_ssh_password')
        self.timeout = int(self.params.get('server_operation_timeout', 900))

    def setup(self):
        """
        Set up before executing test
        """
        if 'cluster' in self.env:
            self.cluster_id = self.env.get('cluster')
        elif self.params.get('cluster_id'):
            self.cluster_id = int(self.params.get('cluster_id'))
        else:
            raise exceptions.TestSetupFail(
                'Please set cluster_id in config first')

        self.params['cluster_id'] = self.cluster_id
        self.client = ServersClient(self.params)
        self.ipv6 = self.params.get('IPV6', False)
        if self.ipv6 == False:
            self.controller_ip = self.params.get('ceph_management_url').split(':')[1].strip('/')
        else:
            self.controller_ip = re.findall(r"[http|https]://\[(.*)\].*", self.params.get('ceph_management_url'), flags=0)[0]

        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

    def _query_servers(self):
        servers = self.client.query(**self.body)
        if not len(servers) > 0:
            raise exceptions.TestFail("No servers found, "
                                      "query all servers failed")
        for server in servers:
            if self.env.get('server_name') is not None:
                if self.env['server_name'] == server['servername']:
                    self.env['tmp_server_id'] = server['id']
                    break

    def test_query(self):
        # Test query all servers
        self._query_servers()

    def test_create(self):
        """
        Execute the test of creating a Server
        """
        # if there is not enough resource to create server, skip it
        if not (self.body.get('servername') and self.body.get('publicip')
                and self.body.get('clusterip') and self.body.get('username')
                and self.body.get('password')):
            raise exceptions.TestSkipError("There is not enough resource"
                                           " to create server!")

        if not self.body.get('parent_bucket'):
            group_id, parent_id = \
                test_utils.get_available_group_bucket(self.params)
            self.body.update({'parent_bucket': parent_id})
        resp_body = self.client.create(**self.body)
        body = resp_body.body
        if not resp_body and utils.verify_response(self.body, resp_body):
            raise exceptions.TestFail("Create server failed: %s"
                                      % self.body)

        status = test_utils.wait_for_server_in_status(
            'servername', self.body['servername'], self.client, 'added',
            1, int(self.params.get('add_host_timeout', 600)))
        if not status:
            raise exceptions.TestFail("Failed to add server %s"
                                      % self.body['servername'])
        LOG.info('Create server %s successfully!'
                 % body['properties'].get('name'))

        self.env['server_name'] = body['properties'].get('name')
        self._query_servers()

    def __get_server_ip(self, server_id):
        query_server = {'marker': 0, 'pagesize': 100}
        servers = self.client.query(**query_server)
        if not len(servers) > 0:
            LOG.error("No available server found!")
            return None
        for server in servers:
            if len(server['mons']) == 0:
                continue
            if server['id'] == server_id:
                return server['publicip']

        return None

    def __wait_for_server_in_status(self, host_ip, reachable=True):
        end_time = time.time() + float(self.timeout)

        while time.time() < end_time:
            output = remote.ping_host(self.controller_ip, self.controller_username,
                                      self.controller_password, host_ip, reachable, ipv6=self.ipv6)
            if output:
                return output

            time.sleep(3)

        return None

    def __check_vm_server_restart(self, server_id):
        server_ip = self.__get_server_ip(server_id)
        LOG.info("Server ip: %s" % server_ip)
        if not server_ip:
            raise exceptions.TestFail("Cannot get server ip by server id %s!"
                                      % server_id)

        # wait for host unreachable
        self.__wait_for_server_in_status(server_ip, False)

        # wait for host reachable
        self.__wait_for_server_in_status(server_ip, True)

    def test_server_operation(self):
        server_ops = self.params.get('server_operation')
        server_id = test_utils.get_available_server(self.params)
        if not server_id:
            raise exceptions.TestSetupFail('No available server found!')

        if server_ops == 'stop_maintenance':
            server_id = self.env.get('maintenance_server_id')
            if not server_id:
                raise exceptions.TestSkipError("No host needs "
                                               "to stop maintenance!")
        LOG.info("Try to %s server '%s' on cluster %s"
                 % (server_ops, server_id, self.cluster_id))
        state = None
        _status = 1
        if server_ops == 'start':
            state = 'active'
            _status = 1
            self.client.start_server(server_id)

        if server_ops == 'stop':
            state = 'active'
            _status = 0
            self.client.stop_server(server_id)

        if server_ops == 'restart':
            state = 'active'
            _status = 0
            self.client.restart_server(server_id)

        if server_ops in 'start_maintenance':
            state = 'maintenance'
            _status = 1
            self.client.start_maintenance(server_id)
            self.env['maintenance_server_id'] = server_id

        if server_ops == 'stop_maintenance':
            state = 'active'
            _status = 1
            self.client.stop_maintenance(server_id)

        #verify server status
        if server_ops == 'restart':
            node_info_client = NodeInfoClient(self.params)
            body_query = node_info_client.query_phydisks(self.cluster_id, server_id)
            if len(body_query) > 0:
                if body_query[0].get('location_led') == -1:
                    LOG.info("Testing on vm environment!")
                    self.__check_vm_server_restart(server_id)
                    return
                else:
                    LOG.info("Testing on physical environment!")
                    status = test_utils.wait_for_server_in_status(
                        'id', server_id, self.client, state,
                        _status, self.timeout)
                    _status = 1
                    if not status:
                        raise exceptions.TestFail("Failed to %s server %s"
                                                  % (server_ops, server_id))

        status = test_utils.wait_for_server_in_status(
            'id', server_id, self.client, state,
            _status, self.timeout)
        if not status:
            raise exceptions.TestFail("Failed to %s server %s"
                                      % (server_ops, server_id))
        time.sleep(60)

    def test_delete(self):
        """
        Test that deletion of specified server
        """
        server_id = self.env.get('tmp_server_id')
        if not server_id:
            raise exceptions.TestSkipError("There is not enough server "
                                           "can be deleted!")

        self.client.delete_server(server_id)
        del self.env['tmp_server_id']

    def test_get_server_disks(self):
        """
        Test get the disks of specified server
        """
        if self.params.get('server_id'):
            server_id = int(self.params.get('server_id'))
        else:
            server_id = test_utils.get_available_server(self.params)
        self.client.get_server_disks(server_id)

    def test_get_server_nics(self):
        """
        Test get the disks of specified server
        """
        if self.params.get('server_id'):
            server_id = int(self.params.get('server_id'))
        else:
            server_id = test_utils.get_available_server(self.params)
        self.client.get_server_nics(server_id)

    def test_add_cephed_server(self):
        """
        Execute the test of creating a Server
        """
        resp = self.client.add_cephed_server(**self.body)
        if not len(resp) > 0:
            raise exceptions.TestFail("Failed to add cephed server!")

    def test_get_server_detail(self):
        """
        Test get all the details of specified server
        """
        if self.params.get('server_id'):
            server_id = int(self.params.get('server_id'))
        else:
            server_id = test_utils.get_available_server(self.params)
        resp = self.client.get_server_detail(server_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("Failed to get server detail information.")

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        pass
