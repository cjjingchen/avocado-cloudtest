"""
Rest client for snapshots
"""

import copy
import json

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import snapshots
from cloudtest.tests.ceph_api.api_schema.response import snapshots as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody


class SnapshotsClient(CephMgmtClient):
    """
    The REST client of snapshots.
    """
    def __init__(self, params):
        self.params = params
        super(SnapshotsClient, self).__init__(params)
        self.url = '/%s/snapshots' % (params.get('version', 'v1'))

    def create(self, **kwargs):
        """
        Method to create snapshots.
        """
        body = copy.deepcopy(snapshots.create_snapshot)
        body['cluster_id'] = kwargs.get('cluster_id')
        body['pool_id'] = kwargs.get('pool_id')
        body['rbd_id'] = kwargs.get('rbd_id')
        body['snapshot_name'] = kwargs.get('snapshot_name')
        resp, body = self.post(url=self.url, body=json.dumps(body))
        body = json.loads(body)
        #self.validate_response(schema.create, resp, body.get('results'))
        return ResponseBody(resp, body)

    def query(self, *args):
        """
        Query specified or all snapshots
        """
        if len(args) > 0:
            # Snapshot ID specified
            url = self.url + '/' + str(args[0])
        else:
            url = self.url
        resp, body = self.get(url=url)
        return ResponseBody(resp, json.loads(body))

    def delete_snapshot(self, snapshot_id):
        """
        Delete the specified snapshot.
        """
        url = self.url + '/%s' % snapshot_id
        resp, body = self.delete(url=url)
        return ResponseBody(resp, json.loads(body))

    def rollback(self, **kwargs):
        """
        Rollback the specified snapshot.
        """
        body = copy.deepcopy(snapshots.rollback_snapshot)
        body['to_snapshot'] = kwargs.get('to_snapshot')
        body['rbd_id'] = kwargs.get('rbd_id')
        url = self.url + '/rollback'
        resp, body = self.post(url=url, body=json.dumps(body))
        return ResponseBody(resp, json.loads(body))

    def clone(self, snapshot_id, **kwargs):
        body = copy.deepcopy(snapshots.clone_snapshot)
        body['standalone'] = kwargs.get('standalone')
        body['dest_pool'] = kwargs.get('dest_pool')
        body['dest_rbd'] = kwargs.get('dest_rbd')
        url = self.url + '/%s/clone' % snapshot_id
        resp, body = self.post(url=url, body=json.dumps(body))
        return ResponseBody(resp, json.loads(body))

