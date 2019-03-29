"""
Rest client for node_info
"""
import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.response import node_info as schema
from cloudtest.tests.ceph_api.api_schema.request import node_info
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody, ResponseBodyList


class NodeInfoClient(CephMgmtClient):
    def __init__(self, params):
        self.params = params
        super(NodeInfoClient, self).__init__(params)
        self.url = '/%s/clusters' % (params.get('version', 'v1'))

    def query_phydisks(self, cluster_id, server_id):
        url = self.url + '/%s/servers/%s/phydisks' % (cluster_id, server_id)
        resp, body = self.get(url=url)
        body = json.loads(body)
        # self.validate_response(schema.QUERY_PHYDISKS, resp, body)
        # Fixme: wating for finally version of doc
        return ResponseBodyList(resp, body)

    def query_disks(self, cluster_id, server_id, osd_id):
        url = self.url + '/%s/servers/%s/osds/%s/disks' % (
            cluster_id, server_id, osd_id)
        resp, body = self.get(url=url)
        body = json.loads(body)
        # Fixme: wating for finally version of doc
        # self.validate_response(schema.QUERY_DISKS, resp, body)
        return ResponseBodyList(resp, body)

    def query_node_detail(self, cluster_id, server_id):
        url = self.url + '/%s/servers/%s/detail' % (cluster_id, server_id)
        resp, body = self.get(url=url)
        body = json.loads(body)
        # Fixme: wating for finally version of doc
        # self.validate_response(schema.QUERY_NODE_DETAIL, resp, body)
        return ResponseBody(resp, body)

    def led(self, cluster_id, server_id, **kwargs):
        url = self.url + '/%s/servers/%s/phydisks' % (cluster_id, server_id)
        body = copy.deepcopy(node_info.LED)
        body.update(kwargs)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        # Fixme: wating for finally version of doc
        return ResponseBodyList(resp, body)
