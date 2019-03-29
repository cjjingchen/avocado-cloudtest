"""
Rest client for snapshots group
"""

import copy
import json
from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import snapshots_group
from cloudtest.tests.ceph_api.api_schema.response import snapshots_group as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody


class SnapshotsGroupClient(CephMgmtClient):
    """
    The REST client of snapshots group.
    """
    def __init__(self, params):
        self.params = params
        super(SnapshotsGroupClient, self).__init__(params)
        self.cluster_id = params.get('cluster_id')
        self.url = '/%s/clusters/%s/group_snapshots' \
                   % (params.get('version', 'v1'), self.cluster_id)

    def create(self, body_list):
        """
        Method to create snapshots group.
        """
        resp, body = self.post(url=self.url, body=json.dumps(body_list))
        body = json.loads(body)
        self.validate_response(schema.CREATE, resp, body)
        return ResponseBody(resp, body)

    def query(self):
        """
        Query snapshot group list
        """
        resp, body = self.get(url=self.url)
        return ResponseBody(resp, json.loads(body))

    def delete_snapshot(self, snapshots_group_id):
        """
        Delete the specified snapshot.
        """
        url = self.url + '/%s' % snapshots_group_id
        resp, body = self.delete(url=url)
        return ResponseBody(resp, json.loads(body))

    def rollback(self, snapshots_group_id):
        """
        Rollback the specified snapshots group.
        """
        body = copy.deepcopy(snapshots_group.rollback_snapshots_group)
        body["to_snapshot"] = snapshots_group_id
        url = self.url + '/%s' % snapshots_group_id
        resp, body = self.post(url=url, body=json.dumps(body))
        return ResponseBody(resp, json.loads(body))

    def modify(self, snapshots_group_id, **kwargs):
        """
        Modify the specified snapshots group.
        """
        body = copy.deepcopy(snapshots_group.modify_snapshots_group)
        body['new_groupsnap_name'] = kwargs.get('new_groupsnap_name')
        body['old_groupsnap_name'] = kwargs.get('old_groupsnap_name')
        url = self.url + '/%s' % snapshots_group_id
        resp, body = self.put(url=url, body=json.dumps(body))
        return ResponseBody(resp, json.loads(body))

