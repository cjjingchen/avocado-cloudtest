"""
Rest client for iSCSI management
"""
import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import iscsi
from cloudtest.tests.ceph_api.api_schema.response import iscsi as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody


class ISCSIClient(CephMgmtClient):
    """
    The REST client of iscsi.
    """
    def __init__(self, params):
        self.params = params
        self.cluster_id = params.get('cluster_id')
        super(ISCSIClient, self).__init__(params)
        self.url = '/%s/clusters/%s' % (params.get('version', 'v1'),
                                        self.cluster_id)

    def create(self, **kwargs):
        """
        Method to create iscsi.
        """
        body = {}
        sub_body = copy.deepcopy(iscsi.CREATE_TARGET)
        sub_body['initiator_ips'] = kwargs.get('initiator_ips')
        sub_body['multipath'] = int(kwargs.get('multipath'))
        sub_body['target_name'] = kwargs.get('target_name')
        sub_body['gateway_id'] = kwargs.get('gateway_id')
        body['entity'] = sub_body

        url = self.url + '/iscsitargets'
        resp, body = self.post(url, body=json.dumps(body))
        body = json.loads(body)
        #self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def query(self, target_id=None):
        """
        Query specified or all iscsi
        """

        if target_id is not None:
            url = self.url + '/iscsitargets/%s' % target_id
        else:
            url = self.url + '/iscsitargets'
        resp, body = self.get(url)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def add_lun(self, target_id, rbd_id, pool_id):
        """
        Add lun to specified iSCSI target

        :param iscsitarget_id: the id of the iscsitarget to stop
        """
        body = {}
        sub_body = copy.deepcopy(iscsi.ADD_LUN)
        sub_body['rbd_id'] = rbd_id
        sub_body['pool_id'] = pool_id
        body['entity'] = sub_body
        url = self.url + '/iscsitargets/%s/associate_lun' % target_id
        resp, body = self.put(url, body=json.dumps(body))
        body = json.loads(body)
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def delete_lun(self, target_id, lun_id):
        """
        Delete the specified lun on certain cluster
        """
        sub_body = {'lun_id': lun_id}
        body = {'entity': sub_body}
        url = self.url + '/iscsitargets/%s/disassociate_lun' % target_id
        resp, body = self.put(url, body=json.dumps(body))
        body = json.loads(body)
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def get_lun_info(self):
        """
        Get all lun of specified target
        """
        url = self.url + '/iscsiluns'
        resp, body = self.get(url)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def modify_iscsi(self, target_id, **kwargs):
        """
        Modify the iSCSI target exported host config
        """
        body = {}
        sub_body = {}
        sub_body['initiator_ips'] = kwargs.get('initiator_ips')
        sub_body['old_initiator_ip'] = kwargs.get('old_initiator_ip')
        body['entity'] = sub_body
        url = self.url + '/iscsitargets/%s' % target_id
        resp, body = self.put(url, body=json.dumps(body))
        body = json.loads(body)
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def create_account_group(self, account_name, account_pass, account_type,
                             gateway_id, account_out_name=None,
                             account_out_pass=None):
        """
        Create account group
        """
        if account_type in "single":
            body = {'entity': {
                'account_name': account_name,
                'account_pass': account_pass,
                'gateway_id': gateway_id,
                }}
        else:
            body = {'entity': {
                'account_name': account_name,
                'account_pass': account_pass,
                'account_out_name': account_out_name,
                'account_out_pass': account_out_pass,
                'gateway_id': gateway_id,
            }}
        url = self.url + '/iscsiaccounts'
        resp, body = self.post(url, body=json.dumps(body))
        body = json.loads(body)
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def query_account_group(self):
        """
        Query all accounts group
        """
        url = self.url + '/iscsiaccounts'
        resp, body = self.get(url)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def modify_account_group(self, account_id, account_name, account_pass,
                             account_name_out=None, account_pass_out=None):
        """
        Modify account group information
        """
        if account_name_out is None:
            body = {'entity': {
                'account_name': account_name,
                'account_pass': account_pass,
                'group_id': account_id,
            }}
        else:
            body = {'entity': {
                'account_name': account_name,
                'account_pass': account_pass,
                'account_out_name': account_name_out,
                'account_out_pass': account_pass_out,
                'group_id': account_id,
            }}
        url = self.url + '/iscsiaccounts/%s' % account_id
        resp, body = self.put(url, body=json.dumps(body))
        body = json.loads(body)
        return ResponseBody(resp, body)

    def bind_account(self, target_id, account_group_id):
        """
        Bind account group to a target
        :param target_id: the id of iscsi target
        :param account_group_id: the id of account group
        """
        body = {'entity': {
            'account_group_id': account_group_id,
            'bind': 'bind_iscsi_account',
        }}
        url = self.url + '/iscsitargets/%s/bind_account' % target_id
        resp, body = self.put(url=url, body=json.dumps(body))
        return ResponseBody(resp, json.loads(body))

    def unbind_account(self, target_id, account_group_id):
        """
        Unbind account group to a target
        :param target_id: the id of iscsi target
        :param account_group_id: the id of account group
        """
        body = {'entity': {
            'account_group_id': account_group_id,
            'bind': 'unbind_iscsi_account',
        }}
        url = self.url + '/iscsitargets/%s/bind_account' % target_id
        resp, body = self.put(url=url, body=json.dumps(body))
        return ResponseBody(resp, json.loads(body))

    def query_login_initiator(self):
        """
        Query login initiator
        """

        url = self.url + '/iscsitargets?action=get_all_initiators'

        resp, body = self.get(url)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def delete_account(self, account_id):
        """
        Delete an account
        """
        url = self.url + '/iscsiaccounts/%s' % account_id
        resp, body = self.delete(url=url)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def delete_iscsitarget(self, iscsitarget_id):
        """
        Delete the specified iscsitarget
        """
        url = self.url + '/iscsitargets/%s' % iscsitarget_id
        resp, body = self.delete(url=url)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)
