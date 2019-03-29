import json
import logging

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib.clustersconf_client import ClustersConfClient
# from cloudtest.tests.ceph_api.api_schema.request import clusters


LOG = logging.getLogger('avocado.test')


class TestClustersConf(test.Test):
    """
    Clusters Conf related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.client = ClustersConfClient(params)
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

        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

    def test_query(self):
        if self.cluster_id is not None:
            resp = self.client.query(self.cluster_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("Query clusters conf failed")
        LOG.info("Got all pools: %s" % resp)

    def test_set(self):
        """
        Execute the test of set cluster conf
        """
        resp = self.client.set(self.cluster_id, self.body)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Set cluster conf failed: %s" % self.body)

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        pass
