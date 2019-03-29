import logging

from avocado.core import test
from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest.tests.ceph_api.lib.pools_client import PoolsClient
from cloudtest.tests.ceph_api.lib.rbd_client import RbdClient
from cloudtest.tests.ceph_api.lib.snapshots_client import SnapshotsClient
from cloudtest.tests.ceph_api.lib import test_utils

LOG = logging.getLogger('avocado.test')
RBD_CAPACITY = 1048576
CAPACITY_MODIFY = RBD_CAPACITY*5


class TestRbdClone(test.Test):
    """
    Module for test rbd clone related operations.
    """
    def __init__(self, params, env):
        self.params = params
        self.env = env
        self.pool_client = PoolsClient(params)
        self.rbd_client = RbdClient(params)
        self.snapshot_client = SnapshotsClient(params)

    def setup(self):
        self.cluster_id = self.params.get('cluster_id')

    def test(self):
        self.pool_id = test_utils.create_pool(self.params)
        self.rbd_response = test_utils.create_rbd_with_capacity(self.pool_id,
                                                         self.params,
                                                        RBD_CAPACITY)
        self.rbd_id=self.rbd_response.get('id')
        self.rbd_name=self.rbd_response.get('name')

        self.__create_snapshot()
        self.__update_rbd(self.rbd_name)
        self.snapshot_id = self.__create_snapshot()
        self.__query_snapshot()
        self.__clone_snapshot()

    def __query_snapshot(self):
        resp = self.snapshot_client.query()
        LOG.info('response  is: %s' % resp)
        body = resp.body
        count = 0
        LOG.info('response body is: %s' % body)
        #resonose body has items and not rbd_id is rbdId
        for i in range(len(body['items'])):
            #id not rbd_id
            if body['items'][i]['rbdId'] == self.rbd_id:
                count = count + 1
        if count != 2:
            raise exceptions.TestFail('Snapshot count %s is wrong !' % count)

    def __clone_snapshot(self):
        body = {}
        rbd_name = 'rbd_clone' + utils_misc.generate_random_string(6)
        body['standalone'] = self.params.get('standalone', 'true')
        body['dest_pool'] = self.params.get('dest_pool', '')
        body['dest_rbd'] = self.params.get('dest_rbd', rbd_name)
        self.snapshot_client.clone(self.snapshot_id, **body)
        status = self.__check_rbd_capacity(body.get('dest_rbd'))
        if not status:
            raise exceptions.TestFail('Clone snapshot failed because capacity'
                                      ' is wrong after clone!')

    def __check_rbd_capacity(self, rbd_name, timeout=100):
        def is_capacity_right():
            resp = self.rbd_client.query(self.pool_id)
            for i in range(len(resp)):
                if resp[i].get('name') == rbd_name:
                    if resp[i].get('capacity') == CAPACITY_MODIFY:
                        return True
            return False
        return utils_misc.wait_for(is_capacity_right,
                                   timeout=timeout, first=0, step=5,
                                   text='Waiting for rbd update!')

    def __update_rbd(self,rbd_name):
        body = {}
        LOG.info('body name is %s' % rbd_name)
        body['name'] = rbd_name
        body['object_size'] = 1
        body['capacity'] = CAPACITY_MODIFY
        self.rbd_client.update(self.pool_id, self.rbd_id, **body)
        status = self.__check_rbd_capacity(body['name'])
        if not status:
            raise exceptions.TestFail('Update rbd capacity failed !')

    def __create_snapshot(self):
        body = {}
        body['cluster_id'] = self.cluster_id
        body['pool_id'] = self.pool_id
        body['rbd_id'] = self.rbd_id
        body['snapshot_name'] = 'cloudtest_snapshot' + \
                                utils_misc.generate_random_string(6)
        resp = self.snapshot_client.create(**body)
        resp = resp.body
        if resp.get('success') is False:
            raise exceptions.TestFail("Create snapshot failed: %s" % body)

        return resp.get('results')['id']

    def teardown(self):
        pass