"""
Rest client for Groups management
"""
import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import groups
from cloudtest.tests.ceph_api.api_schema.response import groups as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody, ResponseBodyList


class GroupsClient(CephMgmtClient):
    """
    The REST client of groups.
    """
    def __init__(self, params):
        self.params = params
        self.cluster_id = params.get('cluster_id')
        super(GroupsClient, self).__init__(params)
        self.url = '/%s/clusters/%s/groups' \
                   % (params.get('version', 'v1'), self.cluster_id)

    def create_group(self, **kwargs):
        body = copy.deepcopy(groups.CREATE_GROUP)
        body.update(kwargs)
        resp, body = self.post(url=self.url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.NEW_GROUP, resp, body)
        return ResponseBody(resp, body)

    def list_groups(self, extra_url=None):
        url = self.url
        if extra_url is not None:
            url = self.url + '%s' % extra_url
        resp, body = self.get(url)
        body = json.loads(body)
        self.validate_response(schema.LIST_GROUPS, resp, body)
        return ResponseBodyList(resp, body)

    def rename_group(self, group_id, **kwargs):
        url = self.url + '/%s' % str(group_id)
        body = copy.deepcopy(groups.RENAME_SUMMARY)
        body.update(kwargs)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.NEW_GROUP, resp, body)
        return ResponseBody(resp, body)

    def delete_group(self, group_id):
        url = self.url + '/%s' % str(group_id)
        resp, body = self.delete(url=url)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def create_bucket(self, group_id, **kwargs):
        url = self.url + '/%s/buckets' % str(group_id)
        body = copy.deepcopy(groups.CREATE_BUCKET)
        body.update(kwargs)
        resp, body = self.post(url=url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.NEW_BUCKET, resp, body)
        return ResponseBody(resp, body)

    def rename_bucket(self, group_id, bucket_id, **kwargs):
        url = self.url + '/%s/buckets/%s' \
                         % (str(group_id), str(bucket_id))
        body = copy.deepcopy(groups.RENAME_SUMMARY)
        body.update(kwargs)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.NEW_BUCKET, resp, body)
        return ResponseBody(resp, body)

    def modify_bucket(self, group_id, bucket_id, **kwargs):
        url = self.url + '/%s/buckets/%s' \
                         % (str(group_id), str(bucket_id))
        body = copy.deepcopy(groups.MODIFY_BUCKET)
        body.update(kwargs)
        resp, body = self.patch(url=url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.NEW_BUCKET, resp, body)
        return ResponseBody(resp, body)

    def delete_bucket(self, group_id, bucket_id):
        url = self.url + '/%s/buckets/%s' \
                         % (str(group_id), str(bucket_id))
        resp, body = self.delete(url=url)
        # Fixme: add the validation when the body is not empty
        # body = json.loads(body)
        # self.validate_response(schema.DELETE_GROUP, resp, body)
        return ResponseBody(resp, body)

    def query_logic_group(self, group_id):
        url = self.url + '/%s/vgroups_select' % str(group_id)
        resp, body = self.get(url=url)
        body = json.loads(body)
        # Fixme: add the validation when the body is not empty
        # body = json.loads(body)
        # self.validate_response(schema.DELETE_GROUP, resp, body)
        return ResponseBodyList(resp, body)