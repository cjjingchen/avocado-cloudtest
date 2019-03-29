import json
import logging
import time

from avocado.core import test
from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest.tests.ceph_api.lib.monitors_client import MonitorsClient

LOG = logging.getLogger('avocado.test')


class TestMonitors(test.Test):
    def __init__(self, params, env):
        self.params = params
        self.client = MonitorsClient(params)
        self.body = {}
        self.env = env

    def setup(self):
        if self.env.get('cluster'):
            self.cluster_id = self.env.get('cluster')
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')
        else:
            raise exceptions.TestSetupFail(
                'Please set cluster_id in config first')

        if self.env.get('server'):
            self.server_id = self.env.get('server')
        elif self.params.get('server_id'):
            self.server_id = self.params.get('server_id')
        else:
            raise exceptions.TestSetupFail(
                'Please set server_id in config first')

        self.monitor_ops = self.params.get('monitor_operation')

    def test_create(self):
        if self.env.get('server_temp'):
            self.server_id = self.env.get('server_temp')
            del self.env['server_temp']
        resp = self.client.create(self.cluster_id, self.server_id)
        resp = resp.body
        self.env['monitor'] = resp.get('id')

    def test_query(self):
        query_type = self.params.get('query_type')
        if query_type in 'all':
            resp = self.client.query(self.cluster_id)
            if not len(resp) > 0:
                raise exceptions.TestFail(
                    "No monitor found, query all monitors of cluster failed")
            LOG.info('Query monitors data %s' % resp)
        elif query_type in 'single':
            resp = self.client.query(self.cluster_id, self.server_id)
            if not len(resp) > 0:
                raise exceptions.TestFail(
                    "No monitor found, query all monitors of cluster failed")
            LOG.info('Query monitor data %s' % resp)

    def test_delete(self):
        if self.env.get('monitor'):
            monitor_id = self.env.get('monitor')
        else:
            temp_resp = self.client.query(self.cluster_id)
            if not len(temp_resp) > 0:
                raise exceptions.TestFail(
                    "No monitor found, delete monitor failed!")
            else:
                length = len(temp_resp)
                for i in range(0, length):
                    if 'follower' in temp_resp[i].get('role'):
                        monitor_id = temp_resp[i].get('id')
                        server_id = temp_resp[i].get('server_id')
                        self.env['server_temp'] = server_id
                        break
        self.client.delete_monitor(self.cluster_id,
                                   server_id, monitor_id)
        status = self.__wait_for_monitor_delete(self.cluster_id, server_id)
        if not status:
            raise exceptions.TestFail('Failed deleted server %s monitor.' %
                                      server_id)
        LOG.info('Successfully deleted server %s monitor.' % server_id)

    def __wait_for_monitor_delete(self, cluster_id, server_id, timeout=30):
        def is_monitor_delete():
            resp_query = self.client.query(self.cluster_id, server_id)
            if len(resp_query) == 0:
                return True
            return False

        return utils_misc.wait_for(is_monitor_delete, timeout, first=0, step=5,
                               text='Waiting for server %s monitor delete' %
                                    server_id)

    def test_operation(self):
        if self.env.get('monitor'):
            monitor_id = self.env.get('monitor')
        else:
            temp_resp = self.client.query(self.cluster_id)
            if not len(temp_resp) > 0:
                raise exceptions.TestFail(
                    "No monitor found, delete monitor failed!")
            else:
                length = len(temp_resp)
                for i in range(0, length):
                    if 'follower' in temp_resp[i].get('role'):
                        monitor_id = temp_resp[i].get('id')
                        server_id = temp_resp[i].get('server_id')
                        break
        self.body['operation'] = self.monitor_ops
        self.client.operate_monitor(
            self.cluster_id, server_id, monitor_id, **self.body)
        resp_query = self.client.query(self.cluster_id, server_id)
        is_start = (self.monitor_ops in 'start' and len(resp_query) > 0
                and resp_query[0].get('state') in 'active')
        is_stop = (self.monitor_ops in 'stop' and len(resp_query) > 0 and
                   'inactive' in resp_query[0].get('state'))
        if is_start or is_stop:
            LOG.info('Successfully %s monitor of server %s' % (
                self.monitor_ops, server_id))
        else:
            raise exceptions.TestFail(
                'Failed %s monitor of server %s' % (
                    self.monitor_ops, server_id))

    def teardown(self):
        pass
