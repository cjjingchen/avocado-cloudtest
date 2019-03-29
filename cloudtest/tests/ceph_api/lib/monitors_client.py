"""
Rest client for monitors
"""

import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import monitors
from cloudtest.tests.ceph_api.api_schema.response import monitors as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody, ResponseBodyList


class MonitorsClient(CephMgmtClient):
    def __init__(self, params):
        self.params = params
        super(MonitorsClient, self).__init__(params)
        self.url = '/%s/clusters' % (params.get('version', 'v1'))

    def create(self, cluster_id, server_id):
        """
        Method to create monitor.
        """
        # TODO: this method have not test, because create interface block
        url = self.url + '/%s/servers/%s/mons' % (str(cluster_id),
                                                  str(server_id))
        resp, body = self.post(url=url, body=None)
        body = json.loads(body)
        self.validate_response(schema.CREATE, resp, body)
        return ResponseBody(resp, body)

    def query(self, cluster_id, server_id=None):
        """
        If server_id is None ,return all monitors of cluster
        else return the monitor of server.
        """
        if server_id:
            url = self.url + '/%s/servers/%s/mons' % (cluster_id, server_id)
        else:
            url = self.url + '/%s/mons' % cluster_id
        resp, body = self.get(url=url)
        body = json.loads(body)
        self.validate_response(schema.QUERY, resp, body)
        return ResponseBodyList(resp, body)

    def delete_monitor(self, cluster_id, server_id, monitor_id):
        url = self.url + '/%s/servers/%s/mons/%s' % (
            str(cluster_id), str(server_id), str(monitor_id))
        resp, body = self.delete(url=url)
        return ResponseBody(resp, json.loads(body))

    def operate_monitor(self, cluster_id, server_id, monitor_id, **kwargs):
        """
        Start or stop monitor .
        :param cluster_id: 
        :param server_id: 
        :param monitor_id: monitor to start/stop
        :param kwargs: start/stop
        :return: 
        """
        url = self.url + '/%s/servers/%s/mons/%s' % (
            cluster_id, server_id, monitor_id)
        body = copy.deepcopy(monitors.start_monitor)
        body['operation'] = kwargs.get('operation')
        resp, body = self.put(url=url, body=json.dumps(body))
        return ResponseBody(resp, json.loads(body))

