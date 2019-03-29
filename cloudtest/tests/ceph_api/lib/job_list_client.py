"""
Rest client for job list
"""
import json

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.response import job_list as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody


class JobListClient(CephMgmtClient):
    def __init__(self, params):
        self.params = params
        super(JobListClient, self).__init__(params)
        self.url = '/%s/jobs' % (params.get('version', 'v1'))

    def query_job_list(self, job_filter=None):
        url = self.url
        if job_filter:
            url = self.url + '?filter=%s' % job_filter

        resp, body = self.get(url=url)
        body = json.loads(body)
        self.validate_response(schema.QUERY_JOB_LIST, resp, body)
        if body:
            return ResponseBody(resp, body)
        return ResponseBody(resp)