import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import rbd
from cloudtest.tests.ceph_api.api_schema.response import rbd as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody
from cloudtest.tests.ceph_api.lib.utils import get_query_body


class RbdClient(CephMgmtClient):
    """
    The REST client of clusters.
    """

    def __init__(self, params):
        self.params = params
        super(RbdClient, self).__init__(params)
        self.path = '%s/clusters' % (params.get('version', 'v1'))
        self.cluster_id = self.params.get('cluster_id')
        self.pool_id = self.params.get('pool_id')
        self.url = '/%s/clusters/%s/pools/' % (params.get('version', 'v1'),
                                               self.cluster_id)

    def create(self, pool_id, **kwargs):
        """
        Method to create clusters.
        """
        body = copy.deepcopy(rbd.CREATE_RBD)
        sub_body = {}
        sub_body['name'] = kwargs.get('name')
        sub_body['object_size'] = int(kwargs.get('object_size'))
        sub_body['capacity'] = int(kwargs.get('capacity'))
        sub_body['num'] = int(kwargs.get('num'))
        sub_body['shared'] = int(kwargs.get('shared'))
        body['entity'] = sub_body

        url = self.url + "%s/rbds" % str(pool_id)

        resp, body = self.post(url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def query_cluster_rbds(self):
        """
        Query rbd list in a cluster
        :return: 
        """
        url = self.url.replace('pools/', 'rbds')
        resp, body = self.get(url)
        body = json.loads(body)
        self.validate_response(schema.query_list, resp, body)
        return ResponseBody(resp, body).body['items']

    def query(self, pool_id, rbd_id=None):
        """
        Query specified or all rbds in a pool
        """
        url = self.url + "%s/rbds" % pool_id
        resp, body = self.get(url)
        body = json.loads(body)
        self.validate_response(schema.query_list, resp, body)
        return ResponseBody(resp, body).body['items']

    def query_specified_rbd(self, pool_id, rbd_id=None):
        """
        Query specified or all rbds in a pool
        """
        url = self.url + "%s/rbds/%s" % (pool_id, rbd_id)
        resp, body = self.get(url)
        body = json.loads(body)
        self.validate_response(schema.query, resp, body)
        return ResponseBody(resp, body)

    def update(self, pool_id, rbd_id, **kwargs):
        """
        Method to update rbd
        """
        body = copy.deepcopy(rbd.CREATE_RBD)
        sub_body = {}
        sub_body['name'] = kwargs.get('name')
        sub_body['object_size'] = int(kwargs.get('object_size'))
        sub_body['capacity'] = int(kwargs.get('capacity'))
        body['entity'] = sub_body

        url = self.url + "%s/rbds/%s" % (pool_id, str(rbd_id))
        resp, body = self.put(url, body=json.dumps(body))
        body = json.loads(body)
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def delete_rbd(self, pool_id, rbd_id):
        """
        Delete the specified rbd
        """
        url = self.url + "%s/rbds/%s" % (pool_id, str(rbd_id))
        resp, body = self.delete(url=url)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def delay_delete_rbd(self, pool_id, rbd_id, delay_time):
        """
        Method to delay delete rbd
        """
        body = copy.deepcopy(rbd.DELAY_DELETE_RBD)
        body['delayed_time'] = delay_time
        url = self.url + "%s/rbds/%s" % (pool_id, str(rbd_id))
        resp, body = self.delete(url, body=json.dumps(body))
        body = json.loads(body)
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def delay_delete_rbd_list(self):
        """
        Method to show delay delete rbd list
        """
        url = '/%s/clusters/%s/deferredrbds' % (
            self.params.get('version', 'v1'),
            self.cluster_id)
        resp, body = self.get(url=url)
        # Fixme: this response is a rbd list
        # self.validate_response(schema.delay_delete_list, resp, body)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def cancel_delay_delete_rbd(self, pool_id, rbd_id):
        """
        Method to cancel delay rbd deletion
        """
        body = {}
        url = self.url + "%s/rbds/%s/rollback" % (pool_id,
                                                  str(rbd_id))
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def migrate(self, pool_id, rbd_id, **kwargs):
        """
        Method to migrate rbd
        """
        body = copy.deepcopy(rbd.MIGRATE_RBD)
        sub_body = {}
        sub_body['target_pool'] = kwargs.get('target_pool')
        body['entity'] = sub_body
        url = url = self.url + "%s/rbds/%s/moverbd" % (pool_id, str(rbd_id))
        resp, body = self.put(url, body=json.dumps(body))
        body = json.loads(body)
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def complete_delete_rbd(self, pool_id, rbd_id):
        """
        Completely delete the specified rbd
        """
        body = {}
        url = self.url + "%s/rbds/%s/completely_remove" % (pool_id, str(rbd_id))
        resp, body = self.put(url=url, body=json.dumps(body))
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def recycled_delete_rbd_list(self):
        """
        Method to show the rbd list in recycle bin
        """
        url = '/%s/clusters/%s/recyclebin' % (
        self.params.get('version', 'v1'),
        self.cluster_id)
        resp, body = self.get(url=url)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def cancel_delete_rbd(self, pool_id, rbd_id):
        """
        Method to cancel rbd deletion
        """
        body = {}
        url = self.url + "%s/rbds/%s/renew" % (pool_id, str(rbd_id))
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def copy_rbd(self, pool_id, rbd_id, **kwargs):
        """
        Method to copy rbd
        """
        body = copy.deepcopy(rbd.COPY_RBD)
        sub_body = {}
        sub_body['target_pool'] = kwargs.get('target_pool')
        sub_body['target_rbd_name'] = 'test_copy_rbd'
        sub_body['operation'] = 'copy'
        body['entity'] = sub_body
        url = url = self.url + "%s/rbds/%s/copyrbd" % (pool_id, str(rbd_id))
        resp, body = self.put(url, body=json.dumps(body))
        body = json.loads(body)
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)



