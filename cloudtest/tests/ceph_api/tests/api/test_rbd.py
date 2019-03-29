import logging
import time

from avocado.core import test
from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest.tests.ceph_api.lib.rbd_client import RbdClient
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib import utils

LOG = logging.getLogger('avocado.test')


class TestRdb(test.Test):
    """
    Rdb related tests.
    """

    def __init__(self, params, env):
        self.params = params
        self.client = RbdClient(params)
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

        self.pool_id = test_utils.get_pool_id(self.env, self.params)

        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

    def test_create(self):
        """
        Execute the test of creating a rbd
        """
        rbd_name = self.params.get('rbd_name', 'cloudtest_' +
                                   utils_misc.generate_random_string(6))
        create_rbd = {'name': rbd_name,
                      'object_size': self.params.get('object_size', 0),
                      'capacity': self.params.get('capacity', 200),
                      'num': self.params.get('num', 1),
                      'shared': self.params.get('shared', 0)}
        resp = self.client.create(self.pool_id, **create_rbd)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Create rbd failed: %s" % self.body)
        self.env['rbd_tmp_name'] = rbd_name
        test_utils.wait_for_rbd_create(self.client, self.pool_id, rbd_name)

    def test_query(self):
        # Test query rdbs in a specified pool
        resp = self.client.query(self.pool_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("No rbds found in the pool")
        for i in range(len(resp)):
            if resp[i]['name'] == self.env.get('rbd_tmp_name'):
                self.env['rbd_tmp_id'] = resp[i]['id']
                break

    def test_query_specified_rbd(self):
        # Test query a specified rdb in a pool
        rbd_id = self.env.get('rbd_tmp_id')
        resp = self.client.query_specified_rbd(self.pool_id, rbd_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("No specified rbd found in the pool")

    def test_query_cluster_rbd(self):
        """
        Query all rbds of specified clusters
        """
        response = self.client.query_cluster_rbds()
        if not len(response) > 0:
            raise exceptions.TestFail("No rbds found in cluster:%s" % self.cluster_id)

    def test_update(self):
        """
        Execute the test of updating a rbd
        """
        rbd_id = self.env.get('rbd_tmp_id')
        # rbd_id = 11
        rbd_name = 'cloudtest_' + utils_misc.generate_random_string(6)
        update_rbd = {'name': rbd_name,
                      'object_size': self.params.get('rest_arg_object_size',
                                                     1),
                      'capacity': self.params.get('rest_arg_capacity', 200)}
        resp = self.client.update(self.pool_id, rbd_id, **update_rbd)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Update rbd failed: %s" % self.body)
        else:
            self.env['rbd_tmp_name'] = rbd_name

    def test_delete(self):
        """
        Test that deletion of specified rdb
        """
        rbd_id = self.env.get('rbd_tmp_id')
        LOG.info("Try to delete rbd with ID: %d" % rbd_id)
        if self.env.get('pool_target_id') is not None:
            self.pool_id = self.env.get('pool_target_id')
        time.sleep(120)
        # delete the rbd created in the right pool
        resp = self.client.delete_rbd(self.pool_id, rbd_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("Delete rbd failed")
        # Fixme delete rbd operation changed to asynchronous
        '''resp = self.client.query(self.pool_id)
        for i in range(len(resp)):
            if resp[i]['id'] == rbd_id:
                raise exceptions.TestFail("Delete rbd failed")'''

    def test_delay_delete(self):
        """
        Test the delay deletion for rdb
        """
        rbd_id = self.env.get('rbd_tmp_id')
        LOG.info("Try to delay delete rbd with ID: %s" % rbd_id)

        delay_time = time.strftime("%Y-%m-%d %H:%M:%S",
                                   time.localtime(time.time() + 60 * 60))
        delay_time = self.params.get('rest_arg_delayed_time', delay_time)
        LOG.info("Delay time is %s" % delay_time)
        resp = self.client.delay_delete_rbd(self.pool_id, rbd_id, delay_time)

        if not len(resp) > 0:
            raise exceptions.TestFail("Failed to set up delayed delete time")

    def test_delay_delete_rbd_list(self):
        """
        Test the delay deletion for rdb
        """
        resp = self.client.delay_delete_rbd_list()
        if not len(resp) > 0:
            raise exceptions.TestFail(
                "No delay delete rbd found in the cluster")

    def test_cancel_delay_delete(self):
        """
        Test to cancel the delay deletion for rdb
        """
        rbd_id = self.env.get('rbd_tmp_id')
        LOG.info("Try to cancel delay delete for rbd %d" % rbd_id)
        self.client.cancel_delay_delete_rbd(self.pool_id, rbd_id)
        resp = self.client.delay_delete_rbd_list()
        for i in range(len(resp)):
            if resp[i]['id'] == rbd_id:
                raise exceptions.TestFail("Cancel delay delete rbd failed")

    def test_copy(self):
        """
        Test copy rbd
        """
        rbd_id = self.env.get('rbd_tmp_id')
        copy_rbd = {'target_pool': self.pool_id}
        resp = self.client.copy_rbd(self.pool_id, rbd_id, **copy_rbd)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Copy rbd failed: %s" % self.body)
        #self.env['copy_pool_target_id'] = target_pool

    def test_migrate(self):
        """
        Test that migration of specified rdb
        """
        rbd_id = self.env.get('rbd_tmp_id')
        vgroup_id = self.env.get('vgroup_id')
        target_pool = test_utils.create_pool(self.params, vgroup_id=vgroup_id)
        time.sleep(60)
        move_rbd = {'target_pool': str(target_pool)}
        resp = self.client.migrate(self.pool_id, rbd_id, **move_rbd)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Migarate rbd failed: %s" % self.body)
        self.env['pool_target_id'] = target_pool

    def test_complete_delete(self):
        """
        Test that complete deletion of specified rdb
        """
        rbd_id = self.env.get('rbd_tmp_id')
        if self.env.get('pool_target_id') is not None:
            self.pool_id = self.env.get('pool_target_id')
        resp = self.client.delete_rbd(self.pool_id, rbd_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("Delete rbd failed")

        resp = self.client.recycled_delete_rbd_list()
        find = False
        for i in range(len(resp)):
            if resp[i]['name'] == self.env.get('rbd_tmp_name'):
                find = True
                break
        if not find:
            raise exceptions.TestFail("There isn't deleted rbd in recycle bin.")

        LOG.info("Try to completely delete rbd with ID: %d" % rbd_id)

        # completely delete the rbd created in the right pool

        resp = self.client.complete_delete_rbd(self.pool_id, rbd_id)

        # Bug: API completely delete cannot delete rbds in recycle bin.
        # Workaround: Execute API completely delete once,
        # then execute list recycle rbds twice
        time.sleep(120)

        resp = self.client.recycled_delete_rbd_list()
        resp = self.client.recycled_delete_rbd_list()
        for i in range(len(resp)):
            if resp[i]['name'] == self.env.get('rbd_tmp_name'):
                raise exceptions.TestFail("Failed to completely delete rbd %s" %
                                          self.env.get('rbd_tmp_name'))

    def test_recycled_rbd_list(self):
        """
        Test the rbd list in recycle bin
        """
        resp = self.client.recycled_delete_rbd_list()
        if not len(resp) > 0:
            raise exceptions.TestFail(
                "No delete rbd found in the recycle bin")

    def test_cancel_rdb_deletion(self):
        """
        Test to cancel the deletion for rdb
        """
        rbd_id = self.env.get('rbd_tmp_id')
        LOG.info("Try to cancel rbd %d deletion" % rbd_id)
        if self.env.get('pool_target_id') is not None:
            self.pool_id = self.env.get('pool_target_id')
        self.client.cancel_delete_rbd(self.pool_id, rbd_id)
        resp = self.client.recycled_delete_rbd_list()
        for i in range(len(resp)):
            if resp[i]['id'] == rbd_id:
                raise exceptions.TestFail("Cancel delete rbd failed")

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        pass
