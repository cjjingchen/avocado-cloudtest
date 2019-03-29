"""
Rest client for warnings
"""

import copy
import json

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import warnings
from cloudtest.tests.ceph_api.api_schema.response import warnings as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody, ResponseBodyList


class WarningsClient(CephMgmtClient):
    """
    The REST client of warnings.
    """
    def __init__(self, params):
        self.params = params
        super(WarningsClient, self).__init__(params)
        self.url = '/%s' % (params.get('version', 'v1'))

    def query_waring_type(self):
        url = self.url + '/alerttypes'
        resp, body = self.get(url)
        body = json.loads(body)
        #self.validate_response(schema.warning, resp, body)
        return ResponseBodyList(response=resp, body=body)

    def modify_waring_type(self, alerttype_id, **kwargs):
        body = {}
        body.update(kwargs)
        url = self.url + '/alerttypes/%s' % alerttype_id
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        # fixme: need schema validate
        return ResponseBody(response=resp, body=body)

    def create_warning(self, **kwargs):
        body = copy.deepcopy(warnings.WARNING)
        body.update(kwargs)
        url = self.url + '/alerts'
        resp, body = self.post(url=url, body=json.dumps(body))
        body = json.loads(body)
        # fixme: need schema validate
        return ResponseBody(response=resp, body=body)

    def query_warning(self, **kwargs):
        url = self.url + '/alerts'
        if len(kwargs) == 2:
            url = url + '?entity_id=%s&entity_type=%s' % (
                kwargs.get('entity_id'), kwargs.get('entity_type'))
        elif len(kwargs) == 1:
            key = kwargs.keys()[0]
            url = url + '?%s=%s' % (key, kwargs.get(key))
        resp, body = self.get(url)
        body = json.loads(body)
        # fixme: need schema validate
        return ResponseBody(response=resp, body=body)

    def query_waring_log(self):
        url = self.url + '/alertevents'
        resp, body = self.get(url)
        body = json.loads(body)
        return ResponseBody(response=resp, body=body)

    def modify_warning(self, alert_id, **kwargs):
        body = {}
        # fixme: waiting for new doc
        # fixme: need to check user_create 3.14.4 attention
        body.update(kwargs)
        url = self.url + '/alerts/%s' % alert_id
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        return ResponseBody(response=resp, body=body)

    def delete_warning(self, alert_id):
        # fixme: waiting for new doc
        # fixme: need to check user_create 3.14.4 attention
        url = self.url + '/alerts/%s' % alert_id
        resp, body = self.delete(url=url)
        if body:
            return json.loads(body)
        return ResponseBody(response=resp)

    def create_email(self, **kwargs):
        body = copy.deepcopy(warnings.EMAIL)
        body.update(kwargs)
        url = self.url + '/notification/emails'
        resp, body = self.post(url=url, body=json.dumps(body))
        body = json.loads(body)
        # fixme: need schema validate
        return ResponseBody(response=resp, body=body)

    def query_email(self):
        url = self.url + '/notification/emails'
        resp, body = self.get(url=url)
        body = json.loads(body)
        # fixme: need schema validate
        return ResponseBodyList(response=resp, body=body)

    def modify_email(self, email_id, **kwargs):
        body = copy.deepcopy(warnings.EMAIL)
        body.update(kwargs)
        url = self.url + '/notification/emails/%s' % email_id
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        # fixme: need schema validate
        return ResponseBody(response=resp, body=body)

    def delete_email(self, email_id):
        url = self.url + '/notification/emails/%s' % email_id
        resp, body = self.delete(url=url)
        body = json.loads(body)
        return ResponseBody(response=resp, body=body)

    def query_notification_settings(self):
        url = self.url + '/notification/settings'
        resp, body = self.get(url=url)
        body = json.loads(body)
        # fixme: Need schema validate
        # self.validate_response(schema.notification, resp, body)
        return ResponseBody(response=resp, body=body)

    def modify_notification_settings(self, **kwargs):
        body = {}
        body.update(kwargs)
        url = self.url + '/notification/settings'
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        # fixme: Need schema validate
        # self.validate_response(schema.notification, resp, body)
        return ResponseBody(response=resp, body=body)

    def set_SNMP(self, **kwargs):
        url = self.url + '/snmp/config'
        body = {}
        body.update(kwargs)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        # fixme: Need schema validate
        return ResponseBody(response=resp, body=body)

    def query_SNMP(self):
        url = self.url + '/snmp/config'
        resp, body = self.get(url=url)
        body = json.loads(body)
        return ResponseBodyList(response=resp, body=body)
