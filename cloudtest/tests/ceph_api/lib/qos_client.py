"""
Rest client for qos
"""
import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import qos
from cloudtest.tests.ceph_api.api_schema.response import qos as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody


class QosClient(CephMgmtClient):
    """
    The REST client of qos.
    """
    def __init__(self, params):
        self.params = params
        super(QosClient, self).__init__(params)
        self.cluster_id = self.params.get('cluster_id')
        self.pools_id = self.params.get('pool_id')
        self.rbds_id = self.params.get('rbds_id')
        self.url = '/%s/clusters/%s/pools/%s/rbds/%s/qoses' % \
                   (params.get('version', 'v1'), self.cluster_id,
                    self.pools_id, self.rbds_id)

    def get_current_qos(self):
        """
        Method to check current qos
        """
        url = self.url + "?action=get_current_qos"
        resp, body = self.get(url)
        body = json.loads(body)
        self.validate_response(schema.get_current_qos, resp, body)
        return ResponseBody(resp, body)

    def get_qos(self):
        """
        Method to check qos
        """
        url = self.url + "?action=get_qos"
        resp, body = self.get(url)
        body = json.loads(body)
        self.validate_response(schema.get_qos, resp, body)
        return ResponseBody(resp, body)

    def get_all_qos(self):
        """
        Method to check all qos
        """
        url = self.url + "?action=get_all_qos"
        resp, body = self.get(url)
        body = json.loads(body)
        self.validate_response(schema.get_qos, resp, body)
        return ResponseBody(resp, body)

    def enable(self, **body):
        """
        Method to enable qos
        """
        _body = copy.deepcopy(qos.ENABLE_QOS.get('entity'))
        if body.has_key("riops"):
            _body.update({'riops': body.get("riops")})
        if body.has_key("wiops"):
            _body.update({'wiops': body.get("wiops")})
        if body.has_key("rbw"):
            _body.update({'rbw': body.get("rbw")})
        if body.has_key("wbw"):
            _body.update({'wbw': body.get("wbw")})
        if body.has_key("iops"):
            _body.update({'iops': body.get("iops")})
        if body.has_key("bw"):
            _body.update({'bw': body.get("bw")})
        _body = {'entity': _body}
        resp, body = self.post(self.url, body=json.dumps(_body))
        body = json.loads(body)
        self.validate_response(schema.enable, resp, body)
        return ResponseBody(resp, body)

    def update(self, **body):
        """
        Method to update qos
        """
        url = self.url + "?action=update"
        _body = copy.deepcopy(qos.UPDATE_QOS.get('entity'))
        if body.has_key("riops"):
            _body.update({'riops': body.get("riops")})
        if body.has_key("wiops"):
            _body.update({'wiops': body.get("wiops")})
        if body.has_key("rbw"):
            _body.update({'rbw': body.get("rbw")})
        if body.has_key("wbw"):
            _body.update({'wbw': body.get("wbw")})
        if body.has_key("iops"):
            _body.update({'iops': body.get("iops")})
        if body.has_key("bw"):
            _body.update({'bw': body.get("bw")})
        _body = {'entity': _body}
        resp, body = self.post(url, body=json.dumps(_body))
        body = json.loads(body)
        self.validate_response(schema.update, resp, body)
        return ResponseBody(resp, body)

    def disable(self):
        """
        Method to disable qos
        """
        url = self.url + "?action=disable"
        resp, body = self.delete(url)
        body = json.loads(body)
        self.validate_response(schema.disable, resp, body)
        return ResponseBody(resp, body)
