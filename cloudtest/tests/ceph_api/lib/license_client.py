"""
Rest client for licenses
"""
import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import license
from cloudtest.tests.ceph_api.api_schema.response import license as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody, ResponseBodyList


class LicenseClient(CephMgmtClient):
    """
    The REST client of license
    """
    def __init__(self, params):
        self.params = params
        super(LicenseClient, self).__init__(params)
        self.url = '/%s/license/' % params.get('version', 'v1')

    def get_license(self):
        """
        Method to get license.
        """
        resp, body = self.get(self.url)
        body = json.loads(body)
        self.validate_response(schema.GET_LICENSE, resp, body)
        return ResponseBodyList(resp, body)

    def validate_license(self, **kwargs):
        """
        Method to validate license.
        """
        body = copy.deepcopy(license.VALIDATE)
        body.update(kwargs)

        resp, body = self.put(self.url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.VALIDATE, resp, body)
        return ResponseBody(resp, body)

    def update_license(self, **kwargs):
        """
        Method to update license.
        """
        body = copy.deepcopy(license.UPDATE)
        body.update(kwargs)
        resp, body = self.post(self.url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.UPDATE, resp, body)
        return ResponseBody(resp, body)
