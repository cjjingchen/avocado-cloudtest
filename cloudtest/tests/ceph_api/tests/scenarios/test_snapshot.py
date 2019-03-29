import logging
import time

from avocado.core import test
from avocado.core import exceptions

from cloudtest import remote
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.rbd_client import RbdClient
from cloudtest.tests.ceph_api.lib.snapshots_client import SnapshotsClient
from cloudtest.tests.ceph_api.lib.iscsi_client import ISCSIClient

LOG = logging.getLogger('avocado.test')


class TestSnapshot(test.Test):
    """
    Module for testing snapshot related operations.
    """
    def __init__(self, params, env):
        self.params = params
        self.body = {}
        self.env = env
        self.rbd_client = RbdClient(params)
        self.snapshot_client = SnapshotsClient(params)
        self.iscsi_client = ISCSIClient(params)

        self.control_server_ip = self.params.get('ceph_management_url')
        self.control_server_ip = self.control_server_ip.split(':')[1].strip(
            '/')
        self.control_username = self.params.get('ceph_server_ssh_username',
                                                'root')
        self.control_password = self.params.get('ceph_server_ssh_password')
        self.initiator_username = self.params.get('ceph_node_ssh_username')
        self.initiator_password = self.params.get('ceph_node_ssh_password')

        self.rbd_id = None
        self.snapshot_id = None
        self.target_id = None
        self.lun_id = None

    def setup(self):

        if 'cluster' in self.env:
            self.cluster_id = self.env['cluster']
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')

        if self.params.get('pool_id'):
            self.pool_id = self.params.get('pool_id')
        else:
            self.pool_id = test_utils.create_pool(self.params)
            LOG.info("pool_id is %s" % self.pool_id)

        if self.params.get('initiator_ip'):
            self.initiator_ip = test_utils.get_available_host_ip(self.params)

    def _create_snapshot(self, rbd_id):
        self.body['cluster_id'] = self.cluster_id
        self.body['pool_id'] = self.pool_id
        self.body['rbd_id'] = rbd_id
        self.body['snapshot_name'] = 'cloudtest_snapshot' + \
                                     utils.utils_misc.generate_random_string(6)
        resp = self.snapshot_client.create(**self.body)
        resp = resp.body
        if resp.get('success') is False:
            raise exceptions.TestFail("Create snapshot failed: %s" % self.body)

        return resp.get('results')['id']

    def _snapshot_rollback(self, rbd_id, snapshot_id):
        self.body['to_snapshot'] = snapshot_id
        self.body['rbd_id'] = rbd_id
        resp = self.snapshot_client.rollback(**self.body)
        resp = resp.body
        if resp.get('success') is not True:
            raise exceptions.TestFail("Rollback snapshot failed: %s" %
                                      self.body)

    def _create_iscsi_target(self):
        self.iscsi_target_name = "cloudtest" + \
                                 utils.utils_misc.generate_random_string(6)
        body = {'initiator_ips': self.initiator_ip,
                'target_name': self.iscsi_target_name,
                'multipath': self.params.get('multipath', '3')}

        resp = self.iscsi_client.create(**body)
        if not resp and utils.verify_response(body, resp):
            raise exceptions.TestFail("Create target failed: %s" % body)

        return resp.body['target_id']

    def _create_iscsi_lun(self, target_id, rbd_id):
        body = {'target_id': target_id,
                'pool_id': self.pool_id,
                'rbd_id': rbd_id}
        resp = self.iscsi_client.add_lun(**body)

        return resp.body['lun_id']

    def _delete_iscsi_lun(self, target_id, lun_id):
        body = {
            'target_id': target_id,
            'lun_id': lun_id}

        resp = self.iscsi_client.delete_lun(**body)

    def _delete_target(self, target_id):
        """
        Test that deletion of delete target
        """
        self.iscsi_client.delete_iscsitarget(target_id)
        resp = self.iscsi_client.query()
        for i in range(len(resp)):
            if resp[i]['target_id'] == target_id:
                raise exceptions.TestFail("Delete target failed")

    def _delete_snapshot(self, snapshot_id):
        """
        Test that deletion of specified snapshot.
        """
        resp = self.snapshot_client.delete_snapshot(self.snapshot_id)
        resp = resp.body
        if resp.get('success') is not True:
            raise exceptions.TestFail("Delete snapshot failed!")

    def _delete_rbd(self, pool_id, rbd_id):
        """
        Test that deletion of specified rdb
        """
        # delete the rbd created in the right pool
        resp = self.rbd_client.delete_rbd(self.pool_id, rbd_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("Delete rbd failed")

    def test(self):
        # Create rbd in the pool
        self.rbd_id = test_utils.create_rbd(self.pool_id, self.params)

        # Create iscsi
        self.target_id = self._create_iscsi_target()
        # Bind iscsi to rbd
        self.lun_id = self._create_iscsi_lun(self.target_id, self.rbd_id)

        mount_point = self.params.get('mount_point', '/mnt')
        file_name = self.params.get('file_name', 'testfile.txt')
        self.target_ip = test_utils.get_specified_targetip(self.params,
                                                           self.target_id, 0)
        need_mk = True
        create_data = True
        find = test_utils.operate_iscsi(self.control_server_ip,
                                         self.control_username,
                                         self.control_password,
                                         self.initiator_ip,
                                         self.initiator_username,
                                         self.initiator_password,
                                         self.iscsi_target_name,
                                         self.target_ip, mount_point,
                                         file_name, need_mk, create_data)
        if find:
            LOG.info("Find %s under %s!" % (file_name, mount_point))
        else:
            LOG.error("%s not found under %s" % (file_name, mount_point))
        # Unbind iscsi from the rbd
        self._delete_iscsi_lun(self.target_id, self.lun_id)

        time.sleep(30)
        # Create snapshot with the rbd
        self.snapshot_id = self._create_snapshot(self.rbd_id)
        need_mk = False
        create_data = True
        file_name_2 = self.params.get('file_name_2', 'testfile2.txt')
        find = test_utils.operate_iscsi(self.control_server_ip,
                                        self.control_username,
                                        self.control_password,
                                        self.initiator_ip,
                                        self.initiator_username,
                                        self.initiator_password,
                                        self.iscsi_target_name,
                                        self.target_ip, mount_point,
                                        file_name_2, need_mk, create_data)
        if find:
            LOG.info("Find %s under %s!" % (file_name_2, mount_point))
        else:
            LOG.error("%s not found under %s" % (file_name_2, mount_point))

        time.sleep(30)
        # Rollback  snapshot to this rbd
        self._snapshot_rollback(self.rbd_id, self.snapshot_id)

        # Bind iscsi to the rbd
        self.lun_id = self._create_iscsi_lun(self.target_id, self.rbd_id)

        time.sleep(30)
        need_mk = False
        create_data = False
        find = test_utils.operate_iscsi(self.control_server_ip,
                                         self.control_username,
                                         self.control_password,
                                         self.initiator_ip,
                                         self.initiator_username,
                                         self.initiator_password,
                                         self.iscsi_target_name,
                                         self.target_ip, mount_point,
                                         file_name_2, need_mk, create_data)
        if find:
            LOG.error("Find %s under %s!" % (file_name_2, mount_point))
        else:
            LOG.info("%s not found under %s is expected!" % (file_name_2,
                                                             mount_point))

    def teardown(self):
        if self.lun_id is not None:
            self._delete_iscsi_lun(self.target_id, self.lun_id)
        if self.target_id is not None:
            self._delete_target(self.target_id)
        if self.snapshot_id is not None:
            self._delete_snapshot(self.snapshot_id)
        if self.rbd_id is not None:
            try:
                self._delete_rbd(self.pool_id, self.rbd_id)
            except exceptions.UnexpectedResponseCode, e:
                pass
