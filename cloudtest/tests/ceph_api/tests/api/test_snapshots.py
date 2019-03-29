import logging

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.snapshots_client import SnapshotsClient

LOG = logging.getLogger('avocado.test')


class TestSnapshots(test.Test):
    """
    Snapshots related tests.
    """

    def __init__(self, params, env):
        self.params = params
        self.client = SnapshotsClient(params)
        self.body = {}
        self.env = env

    def setup(self):
        """
        Set up before executing test
        """
        if self.env.get('cluster'):
            self.cluster_id = self.env.get('cluster')
        elif self.params.get('cluster_id'):
            self.cluster_id = int(self.params.get('cluster_id'))
        else:
            raise exceptions.TestSetupFail(
                'Please set cluster_id in config first')

        self.pool_id = test_utils.get_pool_id(self.env, self.params)
        if self.env.get('snapshot_rbd'):
            self.rbd_id = self.env.get('snapshot_rbd')
        else:
            self.rbd_id = test_utils.create_rbd(self.pool_id, self.params)
            LOG.info("rbd_id is %s" % self.rbd_id)
            self.env['snapshot_rbd'] = self.rbd_id

        if self.params.get('snapshots_id'):
            self.snapshot_id = self.params.get('snapshots_id')

    def test_query(self):
        query_type = self.params.get('query_type')
        if query_type in 'all':
            resp = self.client.query()
            resp = resp.body
            if not len(resp) > 1 and resp.get('success') is not True:
                raise exceptions.TestFail("No snapshots found, "
                                          "query all snapshots failed")
            LOG.info('Query snapshots data %s' % str(resp))
        elif query_type in 'single':
            if self.env.get('snapshot_temp'):
                self.snapshot_id = self.env.get('snapshot_temp')
            resp = self.client.query(self.snapshot_id)
            resp = resp.body
            if resp.get('success') is not True:
                raise exceptions.TestFail("Query snapshot failed: %s" %
                                          self.snapshot_id)
            LOG.info('Query snapshot id %s data %s' % (self.snapshot_id,
                                                       str(resp)))

    def test_create(self):
        self.body['cluster_id'] = self.cluster_id
        self.body['pool_id'] = self.pool_id
        self.body['rbd_id'] = self.rbd_id
        self.body['snapshot_name'] = self.params.get('snapshot_name')
        resp = self.client.create(**self.body)
        resp = resp.body
        if resp.get('success') is not True:
            raise exceptions.TestFail("Create snapshot failed: %s" % self.body)
        self.env['snapshot_temp'] = resp.get('results')['id']

    def test_rollback(self):
        if self.env.get('snapshot_temp'):
            self.body['to_snapshot'] = self.env.get('snapshot_temp')
        else:
            self.body['to_snapshot'] = self.snapshot_id
        self.body['rbd_id'] = self.rbd_id
        resp = self.client.rollback(**self.body)
        resp = resp.body
        if resp.get('success') is not True:
            raise exceptions.TestFail("Rollback snapshot failed: %s" %
                                      self.body)
        del self.env['snapshot_rbd']

    def test_clone(self):
        if self.env.get('snapshot_temp'):
            self.snapshot_id = self.env.get('snapshot_temp')
        self.body['standalone'] = self.params.get('standalone')
        self.body['dest_pool'] = self.params.get('dest_pool')
        self.body['dest_rbd'] = self.params.get('dest_rbd')
        resp = self.client.clone(self.snapshot_id, **self.body)
        resp = resp.body
        if resp.get('success') is not True:
            raise exceptions.TestFail("Clone snapshot failed: %s" % self.body)

    def test_delete(self):
        """
        Test that deletion of specified snapshot.
        """
        if self.env.get('snapshot_temp'):
            self.snapshot_id = self.env.get('snapshot_temp')
        LOG.info("Try to delete snapshot with ID: %d" % self.snapshot_id)
        resp = self.client.delete_snapshot(self.snapshot_id)
        resp = resp.body
        if resp.get('success') is not True:
            raise exceptions.TestFail("Delete snapshot failed: %s" % self.body)

    def teardown(self):
        pass
