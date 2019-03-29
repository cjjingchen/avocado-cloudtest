"""
Rest client for clusters
"""

import json
import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import clusters
from cloudtest.tests.ceph_api.api_schema.response import clusters as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBodyList


class ClustersClient(CephMgmtClient):
    """
    The REST client of clusters.
    """
    def __init__(self, params):
        self.params = params
        super(ClustersClient, self).__init__(params)
        self.url = '/%s/clusters' % (params.get('version', 'v1'))

    def create(self, **kwargs):
        """
        Method to create clusters.
        """
        body = copy.deepcopy(clusters.CREATE_CLUSTER)
        body['name'] = kwargs.get('name')
        body['addr'] = kwargs.get('addr')
        resp, body = self.post(url=self.url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.create, resp, body)
        return ResponseBody(resp, body)

    def query(self, cluster_id=None, extra_url=None, validate=True):
        """
        Query specified or all clusters
        """
        if cluster_id is not None:
            # Cluster ID specified
            url = self.url + '/' + str(cluster_id)
        else:
            url = self.url

        if extra_url is not None:
            url += '/' + extra_url

        resp, body = self.get(url=url)
        body = json.loads(body)
        response_body = ResponseBody
        if validate:
            if cluster_id is not None:
                # Query single cluster information
                query_schema = schema.query_single
            elif extra_url:
                # Query the summary
                query_schema = schema.query_summary
            else:
                # Query all clusters
                query_schema = schema.query
                response_body = ResponseBodyList
            self.validate_response(query_schema, resp, body)
        return response_body(resp, body)

    def start_cluster(self, cluster_id):
        """
        Start the specified cluster

        :param cluster_id: the id of the cluster to start
        """
        body = copy.deepcopy(clusters.START_CLUSTER)
        url = self.url + '/%s' % str(cluster_id)
        resp, body = self.put(url=url, body=json.dumps(body))
        return ResponseBody(resp, json.loads(body))

    def restart_cluster(self, cluster_id):
        """
        Restart the specified cluster

        :param cluster_id: the id of the cluster to start
        """
        body = copy.deepcopy(clusters.RESTART_CLUSTER)
        url = self.url + '/%s' % str(cluster_id)
        resp, body = self.put(url=url, body=json.dumps(body))
        return ResponseBody(resp, json.loads(body))

    def deploy_cluster(self, cluster_id):
        """
        Deploy the specified cluster
        """
        body = copy.deepcopy(clusters.DEPLOY_CLUSTER)
        url = self.url + '/%s' % str(cluster_id)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        return ResponseBody(resp, body)

    def expand_cluster(self, cluster_id):
        """
        Expand the specified cluster

        :param cluster_id: the id of cluster to expand
        """
        body = copy.deepcopy(clusters.EXPAND_CLUSTER)
        url = self.url + '/%s' % str(cluster_id)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.expand, resp, body)
        return ResponseBody(resp, body)

    def stop_cluster(self, cluster_id):
        """
        Stop the specified cluster

        :param cluster_id: the id of the cluster to stop
        """
        body = copy.deepcopy(clusters.STOP_CLUSTER)
        url = self.url + '/%s' % str(cluster_id)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        return ResponseBody(resp, body)

    def upgrade_cluster(self, cluster_id):
        """
        Upgrade the specified cluster

        :param cluster_id: the id of the cluster to upgrade
        """
        body = copy.deepcopy(clusters.UPGRADE_CLUSTER)
        url = self.url + '/%s' % str(cluster_id)
        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        return ResponseBody(resp, body)

    def delete_cluster(self, cluster_id):
        """
        Delete the specified cluster
        """
        url = self.url + '/%s' % str(cluster_id)
        resp, body = self.delete(url=url)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)
