"""
Rest client for pools
"""
import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import pools
from cloudtest.tests.ceph_api.api_schema.response import pools as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody
from cloudtest.tests.ceph_api.lib.utils import get_query_body


class PoolsClient(CephMgmtClient):
    """
    The REST client of pools.
    """
    def __init__(self, params):
        self.params = params
        super(PoolsClient, self).__init__(params)
        self.cluster_id = self.params.get('cluster_id')
        self.url = '/%s/clusters/%s/pools' % (params.get('version', 'v1'),
                                              self.cluster_id)
        self.NO_EC = self.params.get('NO_EC', True)

    def create(self,**kwargs):
        """
        Method to create pool.

        :param cluster_id: the id of cluster
        :param name: the name of pool to create
        :param pg_num: placegroup number to create
        :param size: copy files count
        :param group_id: the id of hosts group
        """
        if self.params.get('NO_EC', "true") == "true":
            body = copy.deepcopy(pools.CREATE_POOL_NO_EC)
            body['name'] = kwargs['name']
            body['pg_num'] = kwargs['pg_num']
            body['size'] = kwargs['size']
            body['group_id'] = kwargs['group_id']
            body['vgroup_id'] = kwargs['vgroup_id']
            resp, body = self.post(self.url, body=json.dumps(body))
            body = json.loads(body)
            #Fixme response changed
            #self.validate_response(schema.create, resp, body)
            return ResponseBody(resp, body)
        else:
            body = copy.deepcopy(pools.CREATE_POOL)
            body['name'] = kwargs['name']
            body['pg_num'] = kwargs['pg_num']
            body['group_id'] = kwargs['group_id']
            body['vgroup_id'] = kwargs['vgroup_id']
            body['safe_type'] = kwargs['safe_type']
            body['data_block_num'] = kwargs['data_block_num']
            body['code_block_num'] = kwargs['code_block_num']
            body['min_size'] = kwargs['min_size']
            body['max_bytes'] = kwargs['max_bytes']
            body['write_mode'] = kwargs['write_mode']
            resp, body = self.post(self.url, body=json.dumps(body))
            body = json.loads(body)
            # Fixme response changed
            # self.validate_response(schema.create, resp, body)
            return ResponseBody(resp, body)

    def query(self, *args):
        """
        Query specified or all pools

        :param cluster_id: the id of cluster
        """

        if len(args) > 0:
            # Pool name specified, query the specific pool
            url = self.url + '/%s' % args[0]
        else:
            url = self.url

        # TCS_version point out the release is SDS or TCS

        resp, body = get_query_body(self.request, url)
        # Fixme: this response is a pool list
        # self.validate_response(schema.query, resp, body)
        if body:
            return body
        return ResponseBody(resp)

    def delete_pool(self, pool_id):
        """
        Delete the specified cluster
        """

        url = self.url + '/%s' % str(pool_id)
        resp, body = self.delete(url=url)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def update(self, pool_id, **kwargs):
        """
        Method to update pool.
l
        :param cluster_id: the id of cluster
        :param name: the name of pool to create
        :param pg_num: placegroup number to create
        :param size: copy files count
        :param group_id: the id of hosts group
        """
        if self.params.get('NO_EC', "true") == "true":
            body = copy.deepcopy(pools.UPDATE_POOL_NO_EC)
        else:
            body = copy.deepcopy(pools.UPDATE_POOL)

        body.update(kwargs)

        url = self.url + '/%s' % str(pool_id)
        resp, body = self.put(url, body=json.dumps(body))
        body = json.loads(body)
        #Fixme pool update response change again and again
        #self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def set_cache(self, pool_id, **kwargs):
        body = copy.deepcopy(pools.SET_CACHE)
        body['cache_pool_id'] = kwargs['cache_pool_id']
        body['cache_pool_name'] = kwargs['cache_pool_name']
        body['cache_size'] = kwargs['cache_size']
        body['target_dirty_radio'] = kwargs['target_dirty_radio']
        body['target_full_radio'] = kwargs['target_full_radio']
        body['option'] = kwargs['option']
        body['caching_mode'] = kwargs['caching_mode']

        url = self.url + '/%s/option' % str(pool_id)
        resp, body = self.put(url, body=json.dumps(body))
        body = json.loads(body)
        # Fixme pool update response change again and again
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def unset_cache(self, pool_id, **kwargs):
        body = copy.deepcopy(pools.UNSET_CACHE)
        body['cache_pool_id'] = kwargs['cache_pool_id']
        body['cache_pool_name'] = kwargs['cache_pool_name']
        body['option'] = kwargs['option']

        url = self.url + '/%s/option' % str(pool_id)
        resp, body = self.put(url, body=json.dumps(body))
        body = json.loads(body)
        # Fixme pool update response change again and again
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)
