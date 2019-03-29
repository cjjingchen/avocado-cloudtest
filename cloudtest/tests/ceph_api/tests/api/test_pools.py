import logging
import time

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib.pools_client import PoolsClient
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest import utils_misc


LOG = logging.getLogger('avocado.test')


class TestPools(test.Test):
    """
    Pools related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.client = PoolsClient(params)
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

    def test_create(self):
        """
        Execute the test of creating a pool
        """
        test_utils.update_env_vgroup(self.params, self.env)
        pool_name = 'cloudtest_' + utils_misc.generate_random_string(6)
        if self.params.get('NO_EC', "true") == "true":
            LOG.info("Try to create NO_EC pool")
            create_pool = {'name': pool_name,
                           'size': self.params.get('rest_arg_size', 3),
                           'group_id': self.params.get('rest_arg_group_id', 1),
                           'pg_num': self.params.get('rest_arg_pg_num', 448),
                           'vgroup_id': self.env.get('vgroup_id', 1)}
        else:
            LOG.info("Try to create EC pool")
            create_pool = {'name': pool_name,
                           'group_id': self.params.get('rest_arg_group_id', 1),
                           'pg_num': self.params.get('rest_arg_pg_num', 448),
                           'vgroup_id': self.env.get('vgroup_id', 1),
                           'safe_type': self.params.get('safe_type', 0),
                           'data_block_num': self.params.get('data_block_num', 3),
                           'code_block_num': self.params.get('code_block_num', 0),
                           'min_size': self.params.get('min_size', 1),
                           'max_bytes': self.params.get("max_bytes", 486547056640),
                           'write_mode': self.params.get("write_mode", "writeback"),
                           }
        resp = self.client.create(**create_pool)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Create pool failed: %s" % self.body)
        self.env['pool_tmp_id'] = resp.body['properties']['context']['pool_id']

        status = test_utils.wait_for_pool_created(self.client, pool_name)
        if not status:
            raise exceptions.TestFail('Failed to create pool %s' % pool_name)
        LOG.info('Create pool %s successfully !' % pool_name)

    def test_query(self):
        # Test query pools in a specified cluster
        resp = self.client.query()
        if not len(resp) > 0:
            raise exceptions.TestFail("Query pools failed" )
        LOG.info("Got all pools: %s" % resp)

    def test_set_ec_pool_cache(self):
        """
        Set up cache for EC pool
        """
        pool_id = self.env.get('pool_tmp_id')
        vgroup_id = self.env.get('vgroup_id', 1)
        cache_pool = test_utils.create_pool(self.params, flag=True,
                                             vgroup_id=vgroup_id)
        self.env['cache_pool_id'] = cache_pool.get('pool_id')
        self.env['cache_pool_name'] = cache_pool.get('name')

        if self.params.get('NO_EC', "true") == "true":
            raise exceptions.TestSkipError("There is not EC pool")
        else:
            set_cache = {'cache_pool_id': cache_pool.get('pool_id'),
                         'cache_pool_name': cache_pool.get('name'),
                         'cache_size': 107374182400,
                         'target_dirty_radio': 30,
                         'target_full_radio': 70,
                         'option': 'set_cache',
                         'caching_mode': 'writeback',
                           }

        resp = self.client.set_cache(pool_id, **set_cache)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Set up EC pool cache failed: %s" %
                                      self.body)

    def test_unset_ec_pool_cache(self):
        """
        Unset cache for EC pool
        """
        pool_id = self.env.get('pool_tmp_id')

        if self.params.get('NO_EC', "true") == "true":
            raise exceptions.TestSkipError("There is not EC pool")
        else:
            unset_cache = {'cache_pool_id': self.env['cache_pool_id'],
                           'cache_pool_name': self.env['cache_pool_name'],
                           'option': 'unset_cache',
                         }

        resp = self.client.unset_cache(pool_id, **unset_cache)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Unset up EC pool cache failed: %s" %
                                      self.body)

    def test_update(self):
        """
        Execute the test of updating a pool
        """
        pool_id = self.env.get('pool_tmp_id')
        pool_name = 'cloudtest_' + utils_misc.generate_random_string(6)
        if self.params.get('NO_EC', "true") == "true":
            update_pool = {'name': pool_name,
                           'size': self.params.get('rest_arg_size', 3),
                           'group_id': self.params.get('rest_arg_group_id', 1),
                           'pg_num': self.params.get('rest_arg_pg_num', 600),
                           'vgroup_id': self.env.get('vgroup_id', 1)}
        else:
            update_pool = {'name': pool_name,
                           'group_id': self.params.get('rest_arg_group_id', 1),
                           'pg_num': self.params.get('rest_arg_pg_num', 448),
                           'vgroup_id': self.env.get('vgroup_id', 1),
                           'safe_type': self.params.get('safe_type', 0),
                           'data_block_num': self.params.get('data_block_num', 3),
                           'code_block_num': self.params.get('code_block_num', 0),
                           'min_size': self.params.get('min_size', 1),
                           'max_bytes': self.params.get("max_bytes", 1073741824),
                           'write_mode': self.params.get("write_mode", "writeback"),
                           }
        resp = self.client.update(pool_id, **update_pool)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Update pool failed: %s" % self.body)

    def test_delete(self):
        """
        Test that deletion of specified cluster
        """
        # sleep 60s, otherwise it may raise error about "the pool is not ready"
        time.sleep(120)
        pool_id = self.env.get('pool_tmp_id')
        LOG.info("Try to delete pool with ID: %s" % pool_id)
        self.client.delete_pool(pool_id)
        resp = self.client.query()
        for i in range(len(resp)):
            if resp[i]['id'] == pool_id:
                raise exceptions.TestFail("Delete pools failed")

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        pass