"""
Rest client for Logs management
"""
import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import log_management
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody


class LogManagementClient(CephMgmtClient):
    """
    The REST client of logs.
    """
    def __init__(self, params):
        self.params = params
        params["ceph_management_url"]= params.get("ceph_management_url").replace(":9999", ":9002")
        super(LogManagementClient, self).__init__(params)
        self.url = '/%s' % params.get('version', 'v1')

    def query_logs(self):
        url = self.url + '/log/search'
        resp, body = self.request('GET', url)
        body = json.loads(body)
        return ResponseBody(resp, body)

    def get_log_type(self):
        url = self.url + '/log/type'
        resp, body = self.request('GET', url)
        body = json.loads(body)
        return ResponseBody(resp, body)

    def export_to_local(self, search_id):
        body = {'search_id': search_id}

        url = self.url + "/log/export_to_local"

        resp, body = self.post(url, body=json.dumps(body))
        body = json.loads(body)
        return ResponseBody(resp, body)

    def regular_export(self, **kwargs):
        body = copy.deepcopy(log_management.CREATE_REGULAR_EXPORT)
        body['interval'] = kwargs['interval']
        body['interval_unit'] = kwargs['interval_unit']
        body['server_ip'] = kwargs['server_ip']
        body['server_password'] = kwargs['server_password']
        body['server_path'] = kwargs['server_path']
        body['server_port'] = kwargs['server_port']
        body['server_username'] = kwargs['server_username']
        body['type'] = kwargs['type']

        url = self.url + "/log/archive"
        resp, body = self.post(url, body=json.dumps(body))
        body = json.loads(body)
        # Fixme pool update response change again and again
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def regular_export_list(self):
        url = self.url + '/log/archive'
        resp, body = self.request('GET', url)
        body = json.loads(body)
        return ResponseBody(resp, body)

    def delete_regular_job(self, job_id):
        """
        Delete the specified regular job
        """
        url = self.url + '/log/archive/%s' % str(job_id)
        resp, body = self.delete(url=url)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def get_regular_job(self, job_id):
        url = self.url + '/log/%s/archivetask' % job_id
        resp, body = self.request('GET', url)
        body = json.loads(body)
        return ResponseBody(resp, body)

    def export_log(self, **kwargs):
        body = copy.deepcopy(log_management.EXPORT_TO_REMOTE)
        body['host'] = kwargs['host']
        body['password'] = kwargs['password']
        body['path'] = kwargs['path']
        body['port'] = kwargs['port']
        body['username'] = kwargs['username']
        body['filename'] = kwargs['filename']

        url = self.url + "/job"
        resp, body = self.post(url, body=json.dumps(body))
        body = json.loads(body)
        # Fixme pool update response change again and again
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def get_export_log(self):
        url = self.url + '/job'
        resp, body = self.request('GET', url)
        body = json.loads(body)
        return ResponseBody(resp, body)

