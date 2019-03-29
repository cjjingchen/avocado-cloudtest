"""
Rest client for osd
"""
import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import osd
from cloudtest.tests.ceph_api.api_schema.response import osd as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody


class OsdClient(CephMgmtClient):
    """
    The REST client of osd.
    """
    def __init__(self, params):
        self.params = params
        super(OsdClient, self).__init__(params)
        self.cluster_id = self.params.get('cluster_id')

        self.url = '/%s/clusters/%s/servers/' % \
                   (params.get('version', 'v1'), self.cluster_id)

    def get_osd_capacity(self, server_id):
        """
        Method to check osds capacity.
        """
        url = self.url + "%s/osds_capacity" % server_id
        resp, body = self.get(url)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def get_osd_disk(self, server_id, osd_id):
        """
        Method to check osds related disks.
        """
        url = self.url + "%s/osds/%s/disks" % (server_id, osd_id)
        resp, body = self.get(url)
        #self.validate_response(schema.osd_disk, resp, body)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def query(self, server_id, osd_id):
        """
        Query specified osd
        """
        url = self.url + "%s/osds/%s" % (server_id, osd_id)
        resp, body = self.get(url)
        #Fixme response body is not type object
        #self.validate_response(schema.query, resp, body)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def create(self, server_id, **kwargs):
        """
        Method to start or stop osd
        """
        url = self.url + "%s/osds" % server_id
        body = copy.deepcopy(osd.CREATE_OSD)
        uuid_list = kwargs.get('uuids').split(',')
        body['uuids'] = uuid_list
        resp, body = self.post(url, body=json.dumps(body))
        body = json.loads(body)
        #self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def start_osd(self, server_id, osd_id):
        """
        Start the specified osd

        :param osd_id: the id of the osd to start
        """
        body = copy.deepcopy(osd.START_OSD)
        url = self.url + '%s/osds/%s' % (server_id, str(osd_id))
        resp, body = self.put(url=url, body=json.dumps(body))
        return ResponseBody(resp, json.loads(body))

    def stop_osd(self, server_id, osd_id):
        """
        Stop the specified osd

        :param osd_id: the id of the osd to stop
        """
        body = copy.deepcopy(osd.STOP_OSD)
        url = self.url + '%s/osds/%s' % (server_id, str(osd_id))
        resp, body = self.put(url=url, body=json.dumps(body))
        return ResponseBody(resp, json.loads(body))

    def delete_osd(self, server_id, osd_id):
        """
        Delete the specified osd

        :param osd_id: the id of the osd to delete
        """
        url = self.url + '%s/osds/%s' % (server_id, str(osd_id))
        resp, body = self.delete(url=url)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

