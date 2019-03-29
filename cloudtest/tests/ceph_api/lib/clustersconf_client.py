"""
Rest client for clusters conf
"""

import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import clustersconf
from cloudtest.tests.ceph_api.api_schema.response import clustersconf as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody


class ClustersConfClient(CephMgmtClient):
    """
    The REST client of clusters.
    """
    def __init__(self, params):
        self.params = params
        super(ClustersConfClient, self).__init__(params)
        self.url = '/%s/clusters' % (params.get('version', 'v1'))

    def query(self, cluster_id=None):
        """
        Query clusters conf
        """
        url = self.url + '/' + str(cluster_id) + '/config'
        #return self.get(url=url)
        resp, body = self.get(url=url)
        body = json.loads(body)
        #FIXME need to add a schema for response
        self.validate_response(schema.query, resp, body)
        return ResponseBody(resp, body)
        #if body:
        #    return json.loads(body)
        #return ResponseBody(resp) 
            
    def set(self, cluster_id, body):

        """
        Set cluster conf

        :param cluster_id: the id of the cluster to set
        """
        url = self.url + '/' + str(cluster_id) + '/config'
        _body = copy.deepcopy(clustersconf.SET_CLUSTERSCONF)
        _body["zabbix_server_ip"] = body.get("zabbix_server_ip", "192.168.0.13")
        _body["zabbix_user"] = body.get("zabbix_user", "Admin")
        _body["zabbix_password"] = body.get("zabbix_password", "zabbix")
        _body["ntp_server_ip"] = body.get("ntp_server_ip", "192.168.0.13")
        _body["max_mdx_count"] = body.get("max_mdx_count", 3)
        _body["max_mon_count"] = body.get("max_mon_count", 3)
        _body["daylight_begin"] = body.get("daylight_begin", "6:00")
        _body["daylight_end"] = body.get("daylight_end", "23:00")
        _body["day_recover_bw"] = body.get("day_recover_bw", 104857600)
        _body["night_recover_bw"] = body.get("night_recover_bw", 524288000)
        resp, body = self.put(url=url, body=json.dumps(_body))
        body = json.loads(body)
        self.validate_response(schema.set, resp, body)
        return ResponseBody(resp, body)

