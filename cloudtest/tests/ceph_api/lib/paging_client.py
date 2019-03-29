"""
Rest client for paging
"""

import json
import logging

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.response import paging as schema
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody

LOG = logging.getLogger('avocado.test')

class PagingClient(CephMgmtClient):
    """
    The REST client of paging
    """
    def __init__(self, params):
        self.params = params
        super(PagingClient, self).__init__(params)
        self.url = '/%s/' % (params.get('version', 'v1'))

    def snapshots_paging(self, rbd_id, pool_id, sufindex, preindex, filter,
                       validate):
        url = self.url + ("snapshots?rbd_id=%s&pool_id=%s"
                         "&sufindex=%s&preindex=%s&filter=%s" %
                          (rbd_id, pool_id, sufindex, preindex, filter))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.snapshots
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def logs_paging(self, user, category, state, starttime, endtime, preindex,
                 sufindex, validate):
        url = self.url + ("logs?user=%s&category=%s&state=%s&starttime=%s"
                          "\&endtime=%s&preindex=%s&sufindex=%s" %
                          (user, category, state, starttime, endtime,
                           preindex, sufindex))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.logs
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def hosts_paging(self, clusters, filter, preindex, sufindex, validate):
        url = self.url + ("clusters/%s/servers?filter=%s&"
                         "sufindex=%s&preindex=%s" %
                          (clusters, filter, sufindex, preindex))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.hosts
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def alertevents_paging(self, cluster_id, preindex, sufindex, validate):
        url = self.url + ("alertevents?cluster_id=%s&"
                         "preindex=%s&sufindex=%s" %
                          (cluster_id, preindex, sufindex))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.alertevents
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def alerts_paging(self, eventster_id, preindex, sufindex, validate):
        url = self.url + ("alerts?eventster_id=%s&"
                         "preindex=%s&sufindex=%s" %
                          (eventster_id, preindex, sufindex))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.alerts
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def osds_paging(self, clusters, filter, validate):
        url = self.url + ("clusters/%s/osds?filter=%s" %
                          (clusters, filter))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.osds
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def hosts_rack_osds_paging(self, clusters, groups, filter, validate):
        url = self.url + ("clusters/%s/groups/%s/hosts_rack_osds?filter=%s" %
                          (clusters, groups, filter))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.hosts_rack_osds
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def logic_hosts_rack_osds_paging(self, clusters, groups, preindex, sufindex,
                                   validate):
        url = self.url + ("clusters/%s/groups/%s/logic_hosts_rack_osds?"
                          "preindex=%s&sufindex=%s" %
                          (clusters, groups, preindex, sufindex))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.logic_hosts_rack_osds
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def pools_paging(self, clusters, preindex, sufindex, filter, validate):
        url = self.url + ("clusters/%s/pools?preindex=%s&sufindex=%s&filter=%s"
                          % (clusters, preindex, sufindex, filter))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.pools
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def rbds_paging(self, clusters, pool_id, preindex, sufindex, filter,
                  validate):
        url = (self.url +
        ("clusters/%s/rbds?pool_id=%s&preindex=%s&sufindex=%s&filter=%s"
                          % (clusters, pool_id, preindex, sufindex, filter)))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.rbds
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def group_snapshots_paging(self, clusters, preindex, sufindex, filter, validate):
        url = (self.url +
        ("clusters/%s/group_snapshots?preindex=%s&sufindex=%s&filter=%s"
                          % (clusters, preindex, sufindex, filter)))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.group_snapshots
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def iscsitargets_paging(self, clusters, preindex, sufindex, filter, validate):
        url = (self.url +
        ("clusters/%s/iscsitargets?preindex=%s&sufindex=%s&filter=%s"
                          % (clusters, preindex, sufindex, filter)))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.iscsitargets
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def iscsiluns_paging(self, clusters, preindex, sufindex, filter, validate):
        url = (self.url +
        ("clusters/%s/iscsiluns?preindex=%s&sufindex=%s&filter=%s"
                          % (clusters, preindex, sufindex, filter)))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.iscsiluns
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def jobs_paging(self, preindex, sufindex, filter, validate):
        url = (self.url + ("jobs/?preindex=%s&sufindex=%s&filter=%s"
                          % (preindex, sufindex, filter)))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.jobs
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def backup_rbtasks_paging(self, clusters, preindex, sufindex, filter,
                            validate):
        url = (self.url +
              ("clusters/%s/backup/rbtasks?filter=%s&preindex=%s&sufindex=%s"
                          % (clusters, filter, preindex, sufindex)))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.backup_rbtasks
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

    def backup_logs_paging(self, clusters, preindex, sufindex, filter, validate):
        url = (self.url +
              ("clusters/%s/backup/logs?filter=%s&preindex=%s&sufindex=%s"
                          % (clusters, filter, preindex, sufindex)))
        resp, body = self.get(url = url)
        body = json.loads(body)
        if validate:
            query_schema = schema.backup_logs
            self.validate_response(query_schema, resp, body)
        return ResponseBody(resp, body)

