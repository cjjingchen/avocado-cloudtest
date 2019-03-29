import logging

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib.paging_client import PagingClient


LOG = logging.getLogger('avocado.test')


class TestPaging(test.Test):
    """
    Paging related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.client = PagingClient(params)
        self.body = {}
        self.env = env

    def setup(self):
        """
        Set up before executing test
        """
        if 'cluster' in self.env:
            self.clusters = self.env['cluster']
        else:
            self.clusters = self.params.get('cluster_id', 1)
        if 'pool' in self.env:
            self.pool_id = self.env['pool']
        else:
            self.pool_id = self.params.get('pool_id', 1)
        if 'rbd' in self.env:
            self.rbd_id = self.env['rbd']
        else:
            self.rbd_id = self.params.get('rbd_id', 1)

        self.user = self.params.get('user')
        self.category = self.params.get('category')
        self.state = self.params.get('state')
        self.starttime = self.params.get('starttime')
        self.endtime = self.params.get('endtime')
        self.filter = self.params.get('filter')
        self.preindex = self.params.get('preindex')
        self.sufindex = self.params.get('sufindex')
        self.eventster_id = self.params.get('eventster_id')
        self.groups = self.params.get('groups')
        self.validate = self.params.get('validate', True)

    def test_snapshots_paging(self):
        resp = self.client.snapshots_paging(self.rbd_id, self.pool_id,
                                            self.sufindex, self.preindex,
                                            self.filter, self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No snapshots paging found!')

    def test_logs_paging(self):
        resp = self.client.logs_paging(self.user, self.category, self.state,
                                       self.starttime, self.endtime,
                                       self.preindex, self.sufindex,
                                       self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No logs paging found!')

    def test_hosts_paging(self):
        resp = self.client.hosts_paging(self.clusters, self.filter,
                                        self.preindex, self.sufindex,
                                        self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No hosts paging found!')

    def test_alertevents_paging(self):
        resp = self.client.alertevents_paging(self.clusters, self.preindex,
                                              self.sufindex, self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No alertevents paging found!')

    def test_alerts_paging(self):
        resp = self.client.alerts_paging(self.eventster_id, self.preindex,
                                         self.sufindex, self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No alerts paging found!')

    def test_osds_paging(self):
        resp = self.client.osds_paging(self.clusters, self.filter,
                                       self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No osds paging found!')

    def test_hosts_rack_osds_paging(self):
        resp = self.client.hosts_rack_osds_paging(self.clusters, self.groups,
                                                  self.filter, self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No hosts rack osds paging found!')

    def test_logic_hosts_rack_osds_paging(self):
        resp = self.client.logic_hosts_rack_osds_paging(self.clusters,
                                                        self.groups,
                                                        self.preindex,
                                                        self.sufindex,
                                                        self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No logic hosts rack osds paging found!')

    def test_pools_paging(self):
        resp = self.client.pools_paging(self.clusters, self.preindex,
                                        self.sufindex, self.filter,
                                        self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No pools paging found!')

    def test_rbds_paging(self):
        resp = self.client.rbds_paging(self.clusters, self.pool_id,
                                       self.preindex, self.sufindex,
                                       self.filter, self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No rbds paging found!')

    def test_group_snapshots_paging(self):
        resp = self.client.group_snapshots_paging(self.clusters, self.preindex,
                                                  self.sufindex, self.filter,
                                                  self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No group snapshots paging found!')

    def test_iscsitargets_paging(self):
        resp = self.client.iscsitargets_paging(self.clusters, self.preindex,
                                               self.sufindex, self.filter,
                                               self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No iscsitargets paging found!')

    def test_iscsiluns_paging(self):
        resp = self.client.iscsiluns_paging(self.clusters, self.preindex,
                                            self.sufindex, self.filter,
                                            self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No iscsiluns paging found!')

    def test_jobs_paging(self):
        resp = self.client.jobs_paging(self.preindex, self.sufindex,
                                       self.filter, self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No jobs paging found!')

    def test_backup_rbtasks_paging(self):
        resp = self.client.backup_rbtasks_paging(self.clusters, self.preindex,
                                                 self.sufindex, self.filter,
                                                 self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No backup rbtasks paging found!')

    def test_backup_logs_paging(self):
        resp = self.client.backup_logs_paging(self.clusters, self.preindex,
                                              self.sufindex, self.filter,
                                              self.validate)
        body = resp.body
        if not len(body):
            raise exceptions.TestFail('No backup logs paging found!')

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        pass
