"""
Rest client for Logs management
"""
import json

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.response import logs as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody


class LogsClient(CephMgmtClient):
    """
    The REST client of logs.
    """
    def __init__(self, params):
        self.params = params
        super(LogsClient, self).__init__(params)
        self.url = "/%s/logs?" % params.get('version', 'v1')

    def query_operation_logs(self, extral_url):
        url = self.url + extral_url
        resp, body = self.get(url)
        self.validate_response(schema.LOGS_SUMMARY, resp, body)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)
