import logging

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.clusters_client import ClustersClient


LOG = logging.getLogger('avocado.test')


class TestClusters(test.Test):
    """
    Clusters related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.client = ClustersClient(params)
        self.body = {}
        self.env = env
        self.resource_to_delete = []

    def setup(self):
        """
        Set up before executing test
        """
        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

    def test_create(self):
        """
        Execute the test of creating a cluster
        """
        try:
            resp = self.client.create(**self.body)
        except:
            if len(self.body['name']) > 32:
                LOG.warn('Known bug, cluster name should not exceed 32 chars')
                return
            else:
                raise
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Create cluster failed: %s" % self.body)
        cluster_id = resp.body.get('id')
        if self.params.get('resource_need_delete', 'no') in 'yes':
            self.resource_to_delete.append(cluster_id)

    def test_query(self):
        query_type = self.params.get('query_type')

        if query_type in 'all':
            # Test query all clusters
            resp = self.client.query()
            if not len(resp) > 0:
                raise exceptions.TestFail("No clusters found, "
                                          "query all clusters failed")

        elif query_type in 'single':
            # Test query single cluster
            cluster_id = self.env.get('cluster', '1')
            resp = self.client.query(cluster_id)
            if not len(resp) > 0:
                raise exceptions.TestFail("Query cluster failed: %s" %
                                          cluster_id)
        elif query_type in 'single_summary':
            cluster_id = self.env.get('cluster', '1')
            resp = self.client.query(cluster_id, extra_url='summary')
            LOG.info("Got summary of cluster '%s': %s" % (cluster_id, resp))

    def test_cluster_operation(self):
        cluster_ops = self.params.get('cluster_operation')
        cluster_id = int(self.env.get('cluster', 1))
        LOG.info("Try to %s cluster '%s'" % (cluster_ops, cluster_id))
        if cluster_ops in 'start':
            resp = self.client.start_cluster(cluster_id)
            status = test_utils.wait_for_cluster_in_status(cluster_id,
                                                           self.client,
                                                           'deployed')
            if not status:
                raise exceptions.TestFail("Failed to start cluster %d" %
                                          cluster_id)

        if cluster_ops in 'restart':
            resp = self.client.restart_cluster(cluster_id)
            status = test_utils.wait_for_cluster_in_status(cluster_id,
                                                           self.client,
                                                           'deployed')
            if not status:
                raise exceptions.TestFail("Failed to restart cluster %d" %
                                          cluster_id)

        elif cluster_ops in 'deploy':
            resp = self.client.deploy_cluster(cluster_id)
            status = test_utils.wait_for_cluster_in_status(cluster_id,
                                                           self.client,
                                                           'deployed')
            if not status:
                raise exceptions.TestFail("Failed to deploy cluster %d" %
                                          cluster_id)

        elif cluster_ops in 'expand':
            resp = self.client.query(cluster_id, extra_url='summary')
            raw_total_before = resp.body.get('rawTotal')
            resp = self.client.expand_cluster(cluster_id)
            resp = self.client.query(cluster_id, extra_url='summary')
            raw_total_after = resp.body.get('rawTotal')
            if int(raw_total_before) < int(raw_total_after):
                LOG.info("Successfully expanded cluster %d from %d to %d" %
                         (cluster_id, raw_total_before, raw_total_after))
            else:
                msg = ("Failed to expand cluster %d, before: %d; after: %d" %
                       (cluster_id, raw_total_before, raw_total_after))
                LOG.error(msg)

        elif cluster_ops in 'stop':
            resp = self.client.stop_cluster(cluster_id)
            status = test_utils.wait_for_cluster_in_status(cluster_id,
                                                           self.client,
                                                           'stopped')
            if not status:
                raise exceptions.TestFail("Failed to stop cluster %d" %
                                          cluster_id)
        elif cluster_ops in 'upgrade':
            resp = self.client.upgrade_cluster(cluster_id)
            status = test_utils.wait_for_cluster_in_status(cluster_id,
                                                           self.client,
                                                           'upgrade')
            if not status:
                raise exceptions.TestFail("Failed to upgrade cluster %d" %
                                          cluster_id)

    def test_delete(self):
        """
        Test that deletion of specified cluster
        """
        resp = self.client.create(**self.body)
        cluster_id = resp.get('id')
        LOG.info("Try to delete cluster with ID: %d" % cluster_id)
        self.client.delete_cluster(cluster_id=cluster_id)

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        if self.resource_to_delete:
            for resource_id in self.resource_to_delete:
                self.client.delete_cluster(resource_id)
