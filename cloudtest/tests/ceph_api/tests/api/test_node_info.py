import logging
import random

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib.node_info_client import NodeInfoClient
from cloudtest.tests.ceph_api.lib import test_utils

LOG = logging.getLogger('avocado.test')


class TestNodeInfo(test.Test):
    def __init__(self, params, env):
        self.params = params
        self.env = env
        self.client = NodeInfoClient(params)
        self.body = {}

    def setup(self):
        if self.env.get('cluster'):
            self.cluster_id = self.env.get('cluster')
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')
        else:
            raise exceptions.TestSetupFail(
                'Please set cluster_id in config first')

        self.server_id = test_utils.get_available_server(self.params)

        self.osd_id = test_utils.get_osd_id_stateless(server_id=self.server_id,
                                                   params=self.params)

    def test_query_phydisks(self):
        body = self.client.query_phydisks(self.cluster_id, self.server_id)
        if not len(body) > 0:
            raise exceptions.TestFail(
                "No phydisks found, query phydisks of node %s failed" %
                self.server_id)

    def test_query_disks(self):
        body = self.client.query_disks(self.cluster_id,
                                       self.server_id, self.osd_id)
        if not len(body) > 0:
            raise exceptions.TestFail(
                "No disks found, query disks of osd %s failed" % self.osd_id)

    def test_query_node_detail(self):
        resp = self.client.query_node_detail(self.cluster_id, self.server_id)
        body = resp.body
        if not len(body) > 0:
            raise exceptions.TestFail(
                "Query detail of node %s failed" % self.server_id)

    def test_led(self):
        body_query = self.client.query_phydisks(self.cluster_id, self.server_id)
        if len(body_query) > 0:
            i = random.randint(0, len(body_query) - 1)
            if body_query[i].get('location_led') == -1:
                raise exceptions.TestSkipError('This case not supported on vm')
            self.body['controllerID'] = body_query[i].get('controllerID')
            self.body['enclosureID'] = body_query[i].get('enclosureID')
            self.body['slotID'] = body_query[i].get('slotID')
            self.body['location_led'] = self.params.get('location_led')
        else:
            raise exceptions.TestFail("No phydisks found")
        self.client.led(self.cluster_id, self.server_id, **self.body)

    def teardown(self):
        pass
