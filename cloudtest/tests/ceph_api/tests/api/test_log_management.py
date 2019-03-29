import logging
import time

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib.log_management_client import LogManagementClient
from cloudtest.tests.ceph_api.lib import test_utils

LOG = logging.getLogger('avocado.test')


class TestLogManagement(test.Test):
    """
    Operation logs related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.body = {}
        self.env = env
        self.client= LogManagementClient(self.params)

    def setup(self):
        pass

    def test_query_logs(self):
        """
        Test search logs
        """
        resp = self.client.query_logs()
        if not len(resp) > 0:
            raise exceptions.TestFail("Query logs failed")
        LOG.info("Got logs %s" % resp)
        self.env['search_id'] = resp['search_id']

    def test_get_log_type(self):
        """
        Test get logs type
        """
        resp = self.client.get_log_type()
        if not len(resp) > 0:
            raise exceptions.TestFail("Query logs type failed")
        LOG.info("Got logs type %s" % resp)

    def test_export_to_local(self):
        """
        Test export logs to local
        """
        search_id = self.env['search_id']
        resp = self.client.export_to_local(search_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("Export logs to local failed")
        LOG.info("Export logs to local %s" % resp)

    def test_create_regular_export_job(self):
        """
        Test create job for regular export logs to remote
        """
        ceph_server_ip = self.params.get('ceph_management_url')
        controller_ip = test_utils.get_ip_from_string(ceph_server_ip)
        controller_username = self.params.get('ceph_server_ssh_username')
        controller_password = self.params.get('ceph_server_ssh_password')

        regular_export = {'interval': 1,
                          'interval_unit': 'minute',
                          'server_ip': controller_ip,
                          'server_password': controller_password,
                          'server_path': '/tmp',
                          'server_port': 22,
                          'server_username': controller_username,
                          'type': 'operation'
                         }

        resp = self.client.regular_export(**regular_export)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Create regular export to remote job "
                                      "failed: %s" % self.body)

    def test_regular_export_list(self):
        """
        Test get regular export list
        """
        resp = self.client.regular_export_list()
        if not len(resp) > 0:
            raise exceptions.TestFail("Get regular export list failed")
        LOG.info('Rest Response: %s' % resp.body['result'][0]['id'])
        self.env['job_id'] = resp.body['result'][0]['id']

    def test_delete_regular_export_job(self):
        """
        Test that deletion of specified export job
        """
        job_id = self.env['job_id']
        LOG.info("Try to delete export job with job_id: %s" % job_id)
        self.client.delete_regular_job(job_id)
        resp = self.client.regular_export_list()
        for i in range(len(resp['result'])):
            if resp['result'][i]['id'] == job_id:
                raise exceptions.TestFail("Delete regular export job failed")

    def test_get_specified_regular_job(self):
        """
        Test get specified regular job
        """
        job_id = self.env['job_id']
        resp = self.client.get_regular_job(job_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("Get specified regular export job failed")
        LOG.info("Get specified regular export job %s" % resp)

    def test_export_to_remote(self):
        """
        Test export log to remote
        """
        ceph_server_ip = self.params.get('ceph_management_url')
        controller_ip = test_utils.get_ip_from_string(ceph_server_ip)
        controller_username = self.params.get('ceph_server_ssh_username')
        controller_password = self.params.get('ceph_server_ssh_password')
        file_name = 'cjtest11.txt'

        export_log = {'host': controller_ip,
                      'password': controller_password,
                      'path': '/tmp',
                      'port': 22,
                      'username': controller_username,
                      'filename': file_name,
                    }

        resp = self.client.export_log(**export_log)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Export log to remote job failed: %s" %
                                      self.body)

    def test_export_log(self):
        """
        Test get export log
        """
        resp = self.client.get_export_log()
        if not len(resp) > 0:
            raise exceptions.TestFail("Query export log failed")
        LOG.info("Got export logs %s" % resp)

    def teardown(self):
        pass
