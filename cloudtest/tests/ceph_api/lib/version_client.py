"""
Rest client for version
"""
import json

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.response import version as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody


class VersionClient(CephMgmtClient):
    def __init__(self, params):
        self.params = params
        super(VersionClient, self).__init__(params)
        self.url = '/%s/softwareversion' % params.get('version', 'v1')

    def query_softwareversion(self):
        url = self.url

        resp, body = self.get(url=url)
        body = json.loads(body)
        self.validate_response(schema.QUERY_SOFTWARE_VERSION, resp, body)
        if body:
            return ResponseBody(resp, body)
        return ResponseBody(resp)

