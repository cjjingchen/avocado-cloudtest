import logging
import time

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib.gateway_client import GatewayClient
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest import utils_misc


LOG = logging.getLogger('avocado.test')


class TestGateway(test.Test):
    """
    Pools related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.client = GatewayClient(params)
        self.body = {}
        self.env = env

    def setup(self):
        """
        Set up before executing test
        """
        if 'cluster' in self.env:
            self.cluster_id = self.env['cluster']
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')

    def test_create(self):
        """
        Execute the test of creating a gateway
        """
        gateway_name = 'cloudtest_gw_' + utils_misc.generate_random_string(6)
        create_gateway = {'name': gateway_name,
                          'services': self.params.get('services', 'iSCSI'),
                          'public_ip': self.params.get('public_ip',
                                                       "192.168.1.21/24")}
        node_list = []
        server_id = test_utils.get_available_server(self.params)
        sub_node = {"id": server_id,
                    "interface": self.params.get('create_node_interface',
                                                 'eth0')}
        node_list.append(sub_node)

        resp = self.client.create(node_list, **create_gateway)

        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Create gateway failed: %s" % self.body)
        self.env['gateway_name'] = resp.body['properties']['name']

    def test_query(self):
        """
        Test query all the gateways
        """
        # wait to make sure gateway created!
        test_utils.wait_for_gateway_created(self.client, self.env.get('gateway_name'))

        resp = self.client.query("gateway")
        LOG.info("Got all gateways: %s" % resp['items'])
        if not len(resp) > 0:
            raise exceptions.TestFail("No gateway in the cluster" )

        for gateway in resp['items']:
            if gateway['name'] == self.env.get('gateway_name'):
                self.env['gateway_id'] = gateway['id']
                break

    def test_query_specified_gateway(self):
        """
        Test query a specified gateway
        """
        gateway_id = self.env.get('gateway_id')
        resp = self.client.query("gateway", gateway_id)
        LOG.info('Rest Response: %s' % resp)

        if not len(resp) > 0:
            raise exceptions.TestFail("No specified gateway found in the cluster")

    def test_query_nodes(self):
        """
        Test query all the nodes can be added to a gateway
        """
        gateway_id = self.env.get('gateway_id')
        resp = self.client.query("node", gateway_id)
        LOG.info('Rest Response: %s' % resp)
        if not len(resp) > 0:
            raise exceptions.TestFail(
                "No available nodes can be added to a gateway")
        self.env["expand_node_id"] = resp["items"][0]["id"]
        self.env["expand_node_interface_id"] = resp["items"][0]["interfaces"][0]["id"]

    def test_update_ip(self):
        """
        Execute the test of update public_ip
        """
        gateway_id = self.env.get('gateway_id')
        new_public_ip = '192.168.1.211/24'
        update_gateway = {'operation': self.params.get('operation', 'modify_ip'),
                          'public_ip': self.params.get('public_ip', new_public_ip)}

        resp = self.client.update_gateway_ip(gateway_id, **update_gateway)
        resp = self.client.query("gateway", gateway_id)
        LOG.info('Rest Response: %s' % resp)
        if resp['public_ips'] not in new_public_ip:
            raise exceptions.TestFail("Update public ip failed, "
                                      "the public_ips is %s" %
                                      resp['public_ips'])

    def test_expand_nodes(self):
        """
        Execute the test of expand nodes for a gateway
        """
        gateway_id = self.env.get('gateway_id')
        added_ips = '192.168.1.216/24'
        update_gateway = {'add_ips': added_ips}

        node_list = []
        sub_node = {"id": self.env.get('expand_node_id', 2),
                    "interface_id":
                        self.env.get('expand_node_interface_id', "1")}
        node_list.append(sub_node)

        resp = self.client.query("gateway", gateway_id)
        node_count_before = len(resp['nodes'])
        resp = self.client.expand_gateway_nodes(gateway_id, node_list,
                                                **update_gateway)
        resp = self.client.query("gateway", gateway_id)
        if added_ips not in resp['public_ips'] or \
                                node_count_before + 1 != len(resp['nodes']):
            raise exceptions.TestFail("Expand nodes failed: %s" % resp)

    def test_delete_nodes(self):
        """
        Test that deletion of nodes
        """
        gateway_id = self.env.get('gateway_id')
        node_id = self.env.get('expand_node_id', 2)
        LOG.info("Try to delete nodes: %s in the gateway %s." %
                 (node_id, gateway_id))

        resp = self.client.query("gateway", gateway_id)
        node_count_before = len(resp['nodes'])
        time.sleep(120)
        self.client.delete_gateway_node(gateway_id, node_id)
        resp = self.client.query("gateway", gateway_id)

        if node_count_before - 1 != len(resp['nodes']):
            raise exceptions.TestFail("Delete nodes failed: %s" % resp)

    def test_delete(self):
        """
        Test that deletion of specified gateway
        """
        gateway_id = self.env.get('gateway_id')
        LOG.info("Try to delete gateway with ID: %s" % gateway_id)
        self.client.delete_gateway(gateway_id)
        resp = self.client.query("gateway", gateway_id)
        for i in range(len(resp)):
            if resp[i]['id'] == gateway_id:
                raise exceptions.TestFail("Delete gateway %s failed" %
                                          gateway_id)

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        pass