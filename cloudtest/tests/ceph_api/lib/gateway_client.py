import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import gateway
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody
from cloudtest.tests.ceph_api.lib.utils import get_query_body


class GatewayClient(CephMgmtClient):
    """
    The REST client of gateway.
    """
    def __init__(self, params):
        self.params = params
        super(GatewayClient, self).__init__(params)
        self.path = '%s/clusters' % (params.get('version', 'v1'))
        self.cluster_id = self.params.get('cluster_id')
        self.url = '/%s/clusters/%s/gateway' % (params.get('version', 'v1'),
                                               self.cluster_id)

    def create(self, notes_list, **kwargs):
        """
        Method to create gateway.
        """
        body = copy.deepcopy(gateway.CREATE_GATEWAY)
        body['name'] = kwargs.get('name')
        body['services'] = kwargs.get('services')
        body['public_ip'] = kwargs.get('public_ip')
        body['nodes'] = notes_list

        url = self.url

        resp, body = self.post(url, body=json.dumps(body))
        body = json.loads(body)

        return ResponseBody(resp, body)

    def query(self, query_type, gateway_id=None):
        """
        Query specified or all gateway
        Query nodes of a specified gateway
        """
        url = self.url

        if query_type in "gateway":
            if gateway_id is not None:
                url += "/%s?preindex=1&sufindex=0" % gateway_id
            else:
                url += "/?preindex=1&sufindex=0"
        elif query_type in "node":
            url += "/%s/nodes?preindex=1&sufindex=0" % gateway_id

        resp, body = self.get(url)

        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def update_gateway_ip(self, gateway_id, **kwargs):
        """
        Method to update gateway ip
        """
        body = copy.deepcopy(gateway.UPDATE_GATEWAY_IP)
        body['operation'] = kwargs.get('operation')
        body['public_ip'] = kwargs.get('public_ip')

        url = self.url + "/%s" % gateway_id
        resp, body = self.put(url, body=json.dumps(body))
        body = json.loads(body)
        #self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def expand_gateway_nodes(self, gateway_id, nodes_list, **kwargs):
        """
        Method to update gateway ip
        """
        body = copy.deepcopy(gateway.EXPAND_GATEWAY_NODES)
        body['add_ips'] = kwargs.get('add_ips')
        body['nodes'] = nodes_list

        url = self.url + "/%s/nodes" % gateway_id
        resp, body = self.post(url, body=json.dumps(body))
        body = json.loads(body)
        # self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def delete_gateway(self, gateway_id):
        """
        Delete the specified gateway
        """
        url = self.url + "/%s" % gateway_id
        resp, body = self.delete(url=url)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def delete_gateway_node(self, gateway_id, node_id):
        """
        Method to delete gateway node
        """
        url = self.url + "/%s/nodes/%s" % (gateway_id, node_id)
        resp, body = self.delete(url)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)



