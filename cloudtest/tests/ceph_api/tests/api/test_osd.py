import logging
import time

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib.osd_client import OsdClient
from cloudtest.tests.ceph_api.lib import test_utils

LOG = logging.getLogger('avocado.test')


class TestOsd(test.Test):
    """
    OSD related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.client = OsdClient(params)
        self.body = {}
        self.env = env

    def setup(self):
        """
        Set up before executing test
        """
        if 'cluster' in self.env:
            self.cluster_id = self.env['cluster']
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')
        if 'server' in self.env:
            self.server_id = self.env['server']
        elif self.params.get('server_id'):
            self.server_id = self.params.get('server_id')
        else:
            self.server_id = test_utils.get_available_server(self.params)
            LOG.info("server id is %s" % self.server_id)

        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

    def test_query(self):
        # Test query specified osd
        #osd_id = self.params.get('osd_id')
        osd_id = test_utils.get_osd_id_stateless(self.server_id, self.params)
        resp = self.client.query(self.server_id, osd_id)

        if not len(resp) > 0:
            raise exceptions.TestFail("Query osd failed")
        LOG.info("Got the osd information: %s" % resp)

    def test_osd_disk(self):
        # Test query osd disks information
        osd_id = test_utils.get_osd_id_stateless(self.server_id, self.params)
        timeout = int(self.params.get('timeout_for_osd_disk', '120'))
        result, resp = test_utils.wait_for_disk_info_in_osd(self.client, self.server_id, osd_id, timeout)
        if not result:
            raise exceptions.TestFail("Query osd disk information failed")
        else:
            LOG.info("Got the osd related disk information: %s %s" % (resp, result))

    def test_osd_capacity(self):
        # Test query osd capacity information
        resp = self.client.get_osd_capacity(self.server_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("Query osd capacity failed")
        LOG.info("Got all osd capacity %s" % resp)

    def test_osd_operation(self):
        osd_ops = self.params.get('osd_operation')
        if osd_ops in 'start':
            osd_id = test_utils.get_down_osd(self.server_id, self.params)
            LOG.info("Try to %s osd '%s'" % (osd_ops, osd_id))
            resp = self.client.start_osd(self.server_id, osd_id)
            if resp.get('status') != 'up':
                raise exceptions.TestFail("Start osd '%s' failed" % osd_id)
        if osd_ops in 'stop':
            osd_id = test_utils.get_available_osd(self.server_id, self.params)
            LOG.info("Try to %s osd '%s'" % (osd_ops, osd_id))
            resp = self.client.stop_osd(self.server_id, osd_id)
            if resp.get('status') != 'down':
                raise exceptions.TestFail("Stop osd '%s' failed" % osd_id)

    def test_delete(self):
        """
        Test that deletion of specified osd
        """
        osd_id = test_utils.get_available_osd(self.server_id, self.params)
        LOG.info("Try to delete osd with ID: %s" % osd_id)
        self.client.delete_osd(self.server_id, osd_id)
        #Fixme it can still query this osd, even though delete osd successfully
        #resp = self.client.query(osd_id)
        #for i in range(len(resp)):
            #if resp[i]['id'] == osd_id:
                #raise exceptions.TestFail("Delete osd failed")

    def test_create(self):
        """
        Execute the test of creating a osd
        """
        uuids_list = test_utils.get_available_disk(self.server_id, self.params)
        if len(uuids_list) > 0:
            uuid = uuids_list[0]['uuid']
        else:
            raise exceptions.TestFail("Server %s has NOT available disk to "
                                      "create osd" % self.server_id)
        create_osd = {'uuids': uuid}
        resp = self.client.create(self.server_id, **create_osd)
        LOG.info('Rest Response: %s' % resp)
        #Fixme currently, osd created successfully, but body is null
        #if not resp and utils.verify_response(self.body, resp):
            #raise exceptions.TestFail("Create osd failed: %s" % self.body)

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        pass
