"""
Rest client for servers
"""
import json
import copy
import logging

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import servers
from cloudtest.tests.ceph_api.api_schema.response import servers as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody, \
    ResponseBodyList, ResponseBodyData

LOG = logging.getLogger('avocado.test')


class ServersClient(CephMgmtClient):
    """
    The REST client of servers.
    """

    def __init__(self, params):
        self.params = params
        self.cluster_id = params.get('cluster_id')
        super(ServersClient, self).__init__(params)
        self.url = '/%s/clusters/%s/servers' % (
            params.get('version', 'v1'), self.cluster_id)

    def create(self, **kwargs):
        """
        Method to create servers.
        """
        body = copy.deepcopy(servers.CREATE_SERVER)
        body['servername'] = kwargs.get('servername', 'sce-5')
        body['publicip'] = kwargs.get('publicip', '192.168.0.26')
        body['clusterip'] = kwargs.get('clusterip', '192.168.0.26')
        body['managerip'] = kwargs.get('managerip', '192.168.0.26')
        body['username'] = kwargs.get('username', 'root')
        body['passwd'] = kwargs.get('passwd', 'lenovo')
        body['parent_bucket'] = int(kwargs.get('parent_bucket', '1'))
        body['backup_node'] = kwargs.get('backup_node', True)
        resp, body = self.post(url=self.url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.CREATE_SUMMARY, resp, body)
        return ResponseBody(resp, body)

    def query(self, **kwargs):
        """
        Query all servers
        """
        body = copy.deepcopy(servers.QUERY_SERVER)
        body['marker'] = int(kwargs.get('marker', 0))
        body['pagesize'] = int(kwargs.get('pagesize', 1024))
        resp, body = self.request('GET', self.url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.QUERY_SUMMARY, resp, body)
        # return ResponseBodyList(resp, body)
        return ResponseBodyData(resp, body).data['items']

    def delete_server(self, server_id):
        """
        Delete the specified server
        """
        url = self.url + '/%s' % str(server_id)
        resp, body = self.delete(url=url)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def start_maintenance(self, server_id):
        """
        Start the maintennace mode of specified server

        :param server_id: the id of the server
        """
        body = copy.deepcopy(servers.START_MAINTENANCE)
        url = self.url + '/%s' % str(server_id)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.SERVER_START_MAINTENANCE, resp, body)
        return ResponseBody(resp, body)

    def stop_maintenance(self, server_id):
        """
        Stop the maintennace mode of specified server
        
        :param server_id: the id of the server
        """
        body = copy.deepcopy(servers.STOP_MAINTENANCE)
        url = self.url + '/%s' % str(server_id)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.SERVER_OPERATION_SUMMARY, resp, body)
        return ResponseBody(resp, body)

    def start_server(self, server_id):
        """
        Start the specified server

        :param server_id: the id of the server
        """
        body = copy.deepcopy(servers.START_SERVER)
        url = self.url + '/%s' % str(server_id)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.SERVER_OPERATION_SUMMARY, resp, body)
        return ResponseBody(resp, body)

    def stop_server(self, server_id):
        """
        Stop the specified server

        :param server_id: the id of the server
        """
        body = copy.deepcopy(servers.STOP_SERVER)
        url = self.url + '/%s' % str(server_id)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.SERVER_OPERATION_SUMMARY, resp, body)
        return ResponseBody(resp, body)

    def restart_server(self, server_id):
        """
        Restart the specified server

        :param server_id: the id of the server
        """
        body = copy.deepcopy(servers.RESTART_SERVER)
        url = self.url + '/%s' % str(server_id)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.SERVER_OPERATION_SUMMARY, resp, body)
        return ResponseBody(resp, body)

    def get_server_disks(self, server_id):
        """
        Get disks of the specified server
        :param server_id: the id of the server
        """
        url = self.url + '/%s/availdisks' % str(server_id)
        resp, body = self.request('GET', url)
        body = json.loads(body)
        self.validate_response(schema.SERVER_DISK_SUMMARY, resp, body)
        return ResponseBodyList(resp, body)

    def get_server_nics(self, server_id):
        """
        Get networks of the specified server
        :param server_id: the id of the server
        """
        url = self.url + '/%s/networks' % str(server_id)
        resp, body = self.request('GET', url)
        body = json.loads(body)
        self.validate_response(schema.SERVER_NETWORK_SUMMARY, resp, body)
        return ResponseBodyList(resp, body)

    def add_cephed_server(self, **kwargs):
        """
        Method to add cephed server to cluster
        """
        body = copy.deepcopy(servers.ADD_CEPHED_SERVER)
        body['username'] = kwargs.get('username', 'root')
        body['passwd'] = kwargs.get('passwd', 'lenovo')
        body['publicip'] = kwargs.get('publicip', '192.168.0.36')
        body['managerip'] = kwargs.get('managerip', '192.168.0.36')
        resp, body = self.put(url=self.url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.ADD_CEPHED_SERVER_SUMMARY,
                               resp, body)
        return ResponseBody(resp, body)

    def get_server_detail(self, server_id):
        """
        Get all the details information of the specified server
        :param server_id: the id of the server
        """
        url = self.url + '/%s/detail' % str(server_id)
        resp, body = self.request('GET', url)
        body = json.loads(body)
        #self.validate_response(schema.SERVER_DISK_SUMMARY, resp, body)
        return ResponseBody(resp, body)
