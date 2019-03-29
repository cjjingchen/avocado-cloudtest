import logging

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.qos_client import QosClient

LOG = logging.getLogger('avocado.test')


class TestQos(test.Test):
    """
    QOS related tests.
    """
    def __init__(self, params, env):
        self.params = params
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
        self.pools_id = test_utils.get_pool_id(self.env, self.params)
        self.params['pool_id'] = self.pools_id

        if 'rbds' in self.env:
            self.rbds_id = self.env['rbds']
        else:
            self.rbds_id = test_utils.create_rbd(self.pools_id, self.params)
            self.env['rbds'] = self.rbds_id
        self.params['rbds_id'] = self.rbds_id

        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

        self.client = QosClient(self.params)

    def test_current_qos(self):
        """
        Test query current qos information
        """
        resp = self.client.get_current_qos()
        if not len(resp) > 0:
            raise exceptions.TestFail("Query current qos failed")
        LOG.info("Got current qos %s" % resp)

    def test_qos(self):
        """
        Test query qos information
        """
        resp = self.client.get_qos()
        if not len(resp) > 0:
            raise exceptions.TestFail("Query qos failed")
        LOG.info("Got qos %s" % resp)

    def test_all_qos(self):
        """
        Test query all qos
        """
        resp = self.client.get_all_qos()
        if not len(resp) > 0:
            raise exceptions.TestFail("Query all qos failed")
        LOG.info("Got all qos %s" % resp)

    def test_enable(self):
        """
        Execute the test of enable qos 
        """
        self.client.disable()
        resp = self.client.enable(**self.body)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Enable qos failed: %s" % self.body)

    def test_update(self):
        """
        Execute the test of update qos 
        """
        self.client.disable()
        resp = self.client.update(**self.body)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Update qos failed: %s" % self.body)

    def test_disable(self):
        """
        Execute the test of disable qos 
        """
        resp = self.client.disable()
        if not len(resp) > 0:
            raise exceptions.TestFail("Disable qos failed")
        LOG.info("Got info about disable qos %s" % resp)
        test_utils.delete_rbd(self.pools_id, self.rbds_id, self.params)

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        pass
