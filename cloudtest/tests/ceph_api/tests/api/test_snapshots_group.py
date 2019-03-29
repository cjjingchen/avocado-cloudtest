import logging
import time

from avocado.core import test
from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.snapshots_group_client import SnapshotsGroupClient

LOG = logging.getLogger('avocado.test')


class TestSnapshotsGroup(test.Test):
    """
    Snapshots group related tests.
    """

    def __init__(self, params, env):
        self.params = params
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

        self.params['cluster_id'] = self.cluster_id
        self.client = SnapshotsGroupClient(self.params)
        self.pool_count = int(self.params.get('pool_count'))
        self.rbd_count_of_per_pool = int(self.params.get('rbd_count_of_per_pool'))

    def test_create(self):
        snapshot_group_body_list = []
        snap_name = 'cloudtest_' + utils_misc.generate_random_string(6)
        for i in range(self.pool_count):
            pool_id = test_utils.create_pool(self.params)
            self.env['pool_id_%s' % i] = pool_id
            for j in range(self.rbd_count_of_per_pool):
                rbd_id = test_utils.create_rbd(pool_id=pool_id,
                                               params=self.params)
                self.env['rbd_id_%s_%s' % (i, j)] = rbd_id
                snapshot_group_body = {"pool_id": pool_id,
                                       "rbd_id": rbd_id,
                                       "snap_name": snap_name}
                snapshot_group_body_list.append(snapshot_group_body)

        resp = self.client.create(snapshot_group_body_list)
        body = resp.body
        self.env['snapshot_group_id'] = body.get('id')
        self.env['snapshot_group_name'] = body.get('name')
        LOG.info("Create snapshot_group successfully: %s" % body)

    def test_query(self):
        resp = self.client.query()
        body = resp.body
        LOG.info(body)
        if len(body.get('items')) == 0:
            raise exceptions.TestFail("No snapshot group found!")

    def test_modify(self):
        body = {}
        snapshot_group_id = self.env.get('snapshot_group_id')
        old_name = self.env.get('snapshot_group_name')
        new_name = self.params.get('snapshot_group_name')
        body['new_groupsnap_name'] = new_name
        body['old_groupsnap_name'] = old_name
        resp = self.client.modify(snapshot_group_id, **body)
        resp_body = resp.body
        if resp_body['group_snapshot_obj']['name'] != new_name:
            raise exceptions.TestFail(
                "Failed to modify snapshot group name, group name should be %s "
                "not %s" % (new_name, resp_body['group_snapshot_obj']['name']))

    def test_rollback(self):
        snapshot_group_id = self.env.get('snapshot_group_id')
        resp = self.client.rollback(snapshot_group_id)
        body = resp.body
        if body.get("status") != 0:
            raise exceptions.TestFail("Failed to rollback snapshot group,"
                                      "please check!")

    def test_delete(self):
        snapshot_group_id = self.env.get('snapshot_group_id')
        resp = self.client.delete_snapshot(snapshot_group_id)
        body = resp.body
        if body.get("status") != 0:
            raise exceptions.TestFail("Failed to delete snapshot group,"
                                      "please check!")
        query_resp = self.client.query()
        query_body = query_resp.body
        for body in query_body.get('items'):
            if body.get('id') == snapshot_group_id:
                raise exceptions.TestFail("Failed to delete snapshot group,"
                                          "please check!")
        del self.env['snapshot_group_id']

        # sleep 30s, otherwise it may cause delete rbd fail
        time.sleep(30)

    def teardown(self):
        flag = self.params.get('delete_resource').lower() == 'true'
        if flag:
            for i in range(self.pool_count):
                pool_id = self.env.get('pool_id_%s' % i)
                for j in range(self.rbd_count_of_per_pool):
                    rbd_id = self.env.get('rbd_id_%s_%s' % (i, j))
                    test_utils.delete_rbd(pool_id, rbd_id, self.params)
                    # sleep 10s, otherwise it may cause delete pool fail
                    #time.sleep(10)
                    #test_utils.delete_pool(pool_id, self.params)
                    del self.env['pool_id_%s' % i]
                    del self.env['rbd_id_%s_%s' % (i, j)]
