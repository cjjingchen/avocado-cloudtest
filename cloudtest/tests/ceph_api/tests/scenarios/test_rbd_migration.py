import logging
import time

from avocado.core import test, exceptions
from cloudtest.tests.ceph_api.lib import test_utils, utils
from cloudtest.tests.ceph_api.lib.rbd_client import RbdClient
from cloudtest.tests.ceph_api.lib.iscsi_client import ISCSIClient

LOG = logging.getLogger('avocado.test')


class TestRBDMigration(test.Test):
    """
    Module for rbd migration
    """

    def __init__(self, params, env):
        self.params = params
        self.env = env
        self.body = {}
        self.rbd_client = RbdClient(params)
        self.iscsi_client = ISCSIClient(self.params)
        self.control_server_ip = self.params.get('ceph_management_url')
        self.control_server_ip = self.control_server_ip.split(':')[1].strip(
            '/')
        self.control_username = self.params.get('ceph_server_ssh_username',
                                                'root')
        self.control_password = self.params.get('ceph_server_ssh_password')
        self.initiator_username = self.params.get('ceph_node_ssh_username')
        self.initiator_password = self.params.get('ceph_node_ssh_password')
        self.cluster_id = None
        self.pool_id = None
        self.target_pool = None
        self.rbd_id = None
        self.rbd_name = None
        self.iscsi_id = None
        self.initiator_ip = None
        self.iscsi_to_delete = []
        self.env['pool_tmp_id'] = None

    def setup(self):
        """Set up before execute test"""
        if 'cluster' in self.env:
            self.cluster_id = self.env['cluster']
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')

        if self.params.get("pool_id"):
            self.pool_id = self.params.get('pool_id')
        else:
            self.pool_id = test_utils.create_pool(self.params)
            LOG.info("pool_id id %s " % self.pool_id)

        if self.params.get('initiator_ip'):
            self.initiator_ip = self.params.get('initiator_ip')
        else:
            self.initiator_ip = test_utils.get_available_host_ip(self.params)

        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

    def _create_rbd(self):
        RBD_CAPACITY = 1024 * 1024
        self.pool_id = test_utils.create_pool(self.params)
        self.rbd_response = test_utils.create_rbd_with_capacity(self.pool_id,
                                                                self.params,
                                                                RBD_CAPACITY)
        self.rbd_id = self.rbd_response.get('id')
        self.rbd_name = self.rbd_response.get('name')

    def _write_to_rbd(self):
        """This part is common for three case, use other's method
        Write data to this rbd via ISCSI, ISCSI write data method
           1)Create iscsi > bind iscsi to the rbd   
           2)In target: tgtadm --lld iscsi --mode target --op show
           3)Initator:   iscsiadm -m discovery -t st -p 127.0.0.1 (target address)
           4)iscsiadm -m node -T iqn.2017-04.com.lenovo:devsdb6 -p 127.0.0.1(target address) --login
           5)One iscsi device (like sda) will be in the initator device list via command "lsblk"
           6)mkfs -t ext3 -c /dev/sda
           7)mount /dev/sda /mnt
           8)Create a new file(e.g. testfile.txt) in /mnt > write data to this file
           9)Umount  /mnt
           10)Iscsiadm -m node -T iqn.2017-04.com.lenovo:devsdb6 -p 127.0.0.1(target address) --logout
           11)Unbind iscsi from the rbd"""
        self._redo_some_step(create_iscsi=True, need_mk=True,
                             create_data=True)

    def __create_iscsi(self):
        self.iscsi_name = 'iscsi' + \
                          utils.utils_misc.generate_random_string(6)
        body = {'initiator_ips': self.initiator_ip,
                'target_name': self.iscsi_name,
                'multipath': self.params.get('multipath', '1')}
        LOG.info("Try to create iscsi %s" % self.iscsi_name)
        resp = self.iscsi_client.create(**body)
        # LOG.info("Try to create resp %s" % resp)
        time.sleep(30)
        if resp.response['status'] == '200':
            self.iscsi_id = resp.body['target_id']
            self.iscsi_to_delete.append(self.iscsi_id)
            LOG.info('Create iscsi target Succeed :%s!' % self.iscsi_id)
            return
        raise exceptions.TestFail("Create iscsi target failed!")

    def __bind_iscsi(self):
        LOG.info("Start  bind iscsi to rbd ! ")
        body = {'target_id': self.iscsi_id,
                'pool_id': self.pool_id,
                'rbd_id': self.rbd_id}

        resp = self.iscsi_client.add_lun(**body)
        time.sleep(20)
        # LOG.info("Add lun info resp %s" % resp)
        if resp.response['status'] != '200':
            raise exceptions.TestFail("Bind iscsi to  failed %s!" % resp)
        self.lun_id = resp.body['lun_id']
        LOG.info("Bind iscsi to rbd info success!")

    def __unbind_iscsi(self):
        LOG.info("Start  unbind iscsi to rbd ! ")
        body = {
            'target_id': self.iscsi_id,
            'lun_id': self.lun_id}
        resp = self.iscsi_client.delete_lun(**body)
        if resp.response['status'] != '200':
            raise exceptions.TestFail("Migrate rbd failed: %s" % self.body)
        LOG.info('unbind iscsi succeed!')

    def _migrate_rbd(self):
        """Migrate this rbd to target pool"""
        LOG.info("Start migrate rbd to new pool!")
        self.target_pool = test_utils.create_pool(self.params)
        move_rbd = {'target_pool': str(self.target_pool)}
        resp = self.rbd_client.migrate(self.pool_id, self.rbd_id, **move_rbd)
        # LOG.info('Rest Response: %s' % resp)
        time.sleep(60)
        if resp.response['status'] != '200':
            raise exceptions.TestFail("Migrate rbd failed: %s" % self.body)
        self.env['pool_tmp_id'] = self.target_pool
        self.pool_id, self.target_pool = self.target_pool, self.pool_id
        LOG.info("Migrate rbd to new pool success!")

    def _redo_some_step(self, create_iscsi=False, need_mk=False,
                        create_data=False):
        LOG.info("Start repeat some steps in case2,create_iscsi:%s "
                 "need_mk:%s create_data:%s " % (
                     create_iscsi, need_mk, create_data))
        if create_iscsi:
            self.__create_iscsi()
        self.__bind_iscsi()
        LOG.info("Start write data to iscsi via rbd !")
        mount_point = self.params.get('mount_point', '/mnt')
        file_name = self.params.get('file_name', 'testfile.txt')
        find = test_utils.operate_iscsi(self.control_server_ip,
                                        self.control_username,
                                        self.control_password,
                                        self.initiator_ip,
                                        self.initiator_username,
                                        self.initiator_password,
                                        self.iscsi_name,
                                        self.initiator_ip, mount_point,
                                        file_name, need_mk, create_data)
        if find:
            LOG.info("Find %s under %s!" % (file_name, mount_point))
        else:
            LOG.error("%s not found under %s" % (file_name, mount_point))
        time.sleep(20)
        self.__unbind_iscsi()
        time.sleep(20)

    def _migrate_rbd_back(self):
        self.pool_id, self.target_pool = self.target_pool, self.pool_id
        LOG.info("Start migrate rbd back to old pool!")
        rbd_id = self.rbd_id
        target_pool = self.pool_id
        pool_id = self.env['pool_tmp_id']
        move_rbd = {'target_pool': str(target_pool)}
        resp = self.rbd_client.migrate(pool_id, rbd_id, **move_rbd)
        time.sleep(60)
        # LOG.info('Rest Response: %s' % resp)
        if resp.response['status'] != '200':
            raise exceptions.TestFail("Migrate rbd failed: %s" % self.body)
        LOG.info("Migrate rbd back to old pool succeed!")

    def _check_file(self):
        pass

    def _repeat_steps(self):
        pass

    def test_rbd_migration(self):
        """
        This test basically performs following steps:
            1. Create rbd in test pool (e.g. test rbd)
            2. Write data to this rbd via ISCSI, ISCSI write data method
               Repeat step 1->11 in case2
            3. Migrate this rbd to target pool
            4. Repeat step 1->5, step7 in case2
            5. Check  testfile.txt is exists or not
            6. Migrate this rbd back to original pool
            7. Repeat step 1->5, step7 in case2
            8. Check  testfile.txt is exists or not
        """
        self._create_rbd()
        self._write_to_rbd()
        self._migrate_rbd()
        self._redo_some_step()
        self._migrate_rbd_back()
        self._redo_some_step(create_iscsi=False, need_mk=False,
                             create_data=False)

    def teardown(self):
        LOG.info('Delete the resource we create!')
        time.sleep(10)
        for iscsi_id in self.iscsi_to_delete:
            self.iscsi_client.delete_iscsitarget(iscsi_id)
            time.sleep(20)
        if self.rbd_id:
            self.rbd_client.delete_rbd(self.pool_id, self.rbd_id)
        time.sleep(30)
        if self.env['pool_tmp_id']:
            test_utils.delete_pool(self.env['pool_tmp_id'], self.params)
