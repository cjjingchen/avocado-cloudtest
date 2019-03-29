import logging
import time
import threading

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.remotebackup_client import RemoteBackupClient
from cloudtest.tests.ceph_api.lib.pools_client import PoolsClient
from cloudtest.tests.ceph_api.lib.iscsi_client import ISCSIClient
from cloudtest.tests.ceph_api.lib.clusters_client import ClustersClient
from cloudtest.tests.ceph_api.lib.servers_client import ServersClient

LOG = logging.getLogger('avocado.test')


class TestRBDRemoteBackup(test.Test):
    """
    Module for testing RBD remote backup scenarios
    """
    def __init__(self, params, env):
        self.params = params
        self.env = env
        self.body = {}
        self.create_servers_body = {}
        self.cluster_id = None
        self.pool_id = None
        self.target_id = None
        self.rbd_id = None
        self.clusters_client = ClustersClient(self.params)

    def setup(self):
        """
        Set up before executing test
        1. to check if two clusters are available
        2. create one pool: testpool
        3. configure remote backup in the testpool
        """
        # to check if two cluster are available
        clusters = test_utils.get_available_clusters(self.params)
        if len(clusters) < 1:
            raise exceptions.TestSetupFail(
                'There are not enough clusters!')
        elif len(clusters) < 2:
            LOG.info('There are not enough clusters, try to create cluster!')
            self.cluster_id = self._create_cluster()
            self.params['cluster_id'] = self.cluster_id
            self.servers_client = ServersClient(self.params)
            for k, v in self.params.items():
                if 'rest_arg_cluster2_' in k:
                    new_key = k.split('rest_arg_cluster2_')[1]
                    self.create_servers_body[new_key] = v
            self._add_three_hosts()
            self._deploy_cluster()
            clusters = test_utils.get_available_clusters(self.params)
            if len(clusters) < 2:
                raise exceptions.TestSetupFail(
                    'There are not enough clusters!')

        self.cluster_id = clusters[1]['id']
        self.params['cluster_id'] = self.cluster_id
        for cluster in clusters:
            if cluster['id'] != self.cluster_id:
                self.des_cluster_id = cluster['id']
                self.body['des_cluster_id'] = self.des_cluster_id
                break
        src_host = test_utils.get_available_server_info(self.params,
                                                        self.cluster_id)
        self.src_ip = src_host['publicip']
        self.body['src_ip'] = self.src_ip
        self.src_host_id = src_host['id']
        self.body['src_host_id'] = self.src_host_id
        des_host = test_utils.get_available_server_info(self.params,
                                                        self.des_cluster_id)
        self.des_ip = des_host['publicip']
        self.body['des_ip'] = self.des_ip
        self.des_host_id = des_host['id']
        self.body['des_host_id'] = self.des_host_id

        if self.params.get('pool_id'):
            self.pool_id = self.params.get('pool_id')
        else:
            self.pool_id = test_utils.create_pool(self.params)
            pool_client = PoolsClient(self.params)
            if not test_utils.wait_for_pool_in_state(self.pool_id, pool_client,
                                                     'ready'):
                raise exceptions.TestSetupFail("Failed to creating test pool!")
        self.params['pool_id'] = self.pool_id

        # configure remote backup in testpool
        LOG.info("Try to configure remote backup in pool %s : %s"
                 % (self.pool_id, self.body))
        self.client = RemoteBackupClient(self.params)
        self.client.configure_rbpolicy(**self.body)

        # other pre-conditions
        self.control_server_ip = self.params.get('ceph_management_url')
        self.control_server_ip = self.control_server_ip.split(':')[1].strip(
            '/')
        self.control_username = self.params.get('ceph_server_ssh_username',
                                                'root')
        self.control_password = self.params.get('ceph_server_ssh_password',
                                                'lenovo')
        self.initiator_ip = self.params.get('initiator_ip', self.src_ip)
        self.initiator_username = self.params.get('ceph_node_ssh_username',
                                                  'root')
        self.initiator_password = self.params.get('ceph_node_ssh_password',
                                                  'lenovo')
        # create iscsi client
        self.iscsi_client = ISCSIClient(self.params)

    def _create_cluster(self):
        create_cluster = {'name': self.params.get('cluster_name',
                                                  'cloudtest_cluster_2'),
                          'addr': self.params.get('cluster_addr', 'vm')}
        resp = self.clusters_client.create(**create_cluster)
        if not resp and utils.verify_response(create_cluster, resp):
            raise exceptions.TestSetupFail(
                "Create cluster failed: %s" % create_cluster)
        return resp.body.get('id')

    def _create_server(self, request_body):
        if not request_body.get('parent_bucket'):
            group_id, parent_id = \
                test_utils.get_available_group_bucket(self.params)
            request_body.update({'parent_bucket': parent_id})
        resp_body = self.servers_client.create(**request_body)
        body = resp_body.body
        status = test_utils.wait_for_server_in_status(
            'servername', request_body['servername'], self.servers_client,
            'added', 1, int(self.params.get('add_host_timeout', 600)))
        if not status:
            raise exceptions.TestFail("Failed to add server %s"
                                      % request_body['servername'])
        LOG.info('Create server %s successfully!'
                 % body['properties'].get('name'))

    def _add_three_hosts(self):
        parent_bucket = self.create_servers_body.get('parent_bucket')
        i = 1
        threads = []
        while self.create_servers_body.get('servername_%d' % i):
            tmp = 'servername_%d' % i
            servername = self.create_servers_body.get(tmp, 'cloudtest_server_%d' % i)
            tmp = 'username_%d' % i
            username = self.create_servers_body.get(tmp, 'root')
            tmp = 'password_%d' % i
            password = self.create_servers_body.get(tmp, 'lenovo')
            tmp = 'publicip_%d' % i
            publicip = self.create_servers_body.get(tmp)
            tmp = 'clusterip_%d' % i
            clusterip = self.create_servers_body.get(tmp)
            create_server_body = {'servername': servername,
                                  'username': username,
                                  'passwd': password,
                                  'publicip': publicip,
                                  'clusterip': clusterip,
                                  'parent_bucket': parent_bucket}
            t = threading.Thread(target=self._create_server,
                                 args=[create_server_body])
            threads.append(t)
            i = i + 1

        # waiting for all servers ready
        for t in threads:
            t.setDaemon(True)
            t.start()

        for i in range(0, len(threads)):
            try:
                threads[i].join(600)
            except Exception as details:
                LOG.exception('Caught exception waiting for server %d added : %s'
                              % (i, details))

    def _deploy_cluster(self):
        self.clusters_client.deploy_cluster(self.cluster_id)
        status = test_utils.wait_for_cluster_in_status(self.cluster_id,
                                                       self.clusters_client,
                                                       'deployed',
                           int(self.params.get('deploy_host_timeout', 900)))
        if not status:
            raise exceptions.TestFail("Failed to deploy cluster %d" %
                                      self.cluster_id)
        LOG.info("Deploy cluster %d successfully!" % self.cluster_id)

    def _start_rbtask(self, rbd_id):
        rbtask_body = {}
        rbtask_body['rbd_id'] = rbd_id
        resp_body = self.client.start_rbtask(**rbtask_body)
        body = resp_body.body
        LOG.info("Create remote backup %s for rbd %s"
                 % (body.get('id'), rbd_id))
        time.sleep(30)
        return body.get('id')

    def _create_iscsi_target(self):
        self.iscsi_target_name = "cloudtest" + \
                                 utils.utils_misc.generate_random_string(6)
        create_body = {'initiator_ips': self.initiator_ip,
                       'target_name': self.iscsi_target_name,
                       'multipath': self.params.get('multipath', 3)}

        resp = self.iscsi_client.create(**create_body)
        if not resp and utils.verify_response(create_body, resp):
            raise exceptions.TestFail("Create target failed: %s "
                                      % create_body)
        return resp.body['target_id']

    def _create_iscsi_lun(self, target_id, rbd_id):
        create_body = {'target_id': target_id,
                'pool_id': self.pool_id,
                'rbd_id': rbd_id}
        resp = self.iscsi_client.add_lun(**create_body)
        return resp.body['lun_id']

    def _delete_iscsi_lun(self, target_id, lun_id):
        body = {
            'target_id': target_id,
            'lun_id': lun_id}

        self.iscsi_client.delete_lun(**body)

    def _delete_target(self, target_id):
        """
        Test that deletion of delete target
        """
        self.iscsi_client.delete_iscsitarget(target_id)
        resp = self.iscsi_client.query()
        for i in range(len(resp)):
            if resp[i]['target_id'] == target_id:
                raise exceptions.TestFail("Delete target failed")

    def _create_and_bind_ISCSI_to_rbd(self, rbd_id):
        self.target_id = self._create_iscsi_target()
        self.lun_id = self._create_iscsi_lun(self.target_id, rbd_id)

    def _start_restore(self, rbd_id, timestamp):
        restore_body = {}
        restore_body['snap_time'] = timestamp
        resp_body = self.client.start_restore(rbd_id, **restore_body)
        LOG.info("Try to recover to remote backup %s!" % timestamp)
        time.sleep(30)
        body = resp_body.body
        return body.get('id')

    def _verify_task_successfully(self, rbtask_id, state):
        extra_url = '/list_rbtasks?count=1024&begin_index=0'
        rbtasks = self.client.list_rbtasks(extra_url)
        rb_record = None
        for rbtask in rbtasks:
            if rbtask['id'] == rbtask_id:
                rb_record = rbtask['properties']['timestamp']
                break
        if rb_record:
            status = test_utils.wait_for_remote_backup_or_restore_complete(rbtask_id,
                                                                          self.client,
                                                                          state,
                                                                          60)
            if status:
                LOG.info("%s successfully, the timestamp is %s"
                         % (state, rb_record))
                return rb_record

        raise exceptions.TestFail("Failed to %s!" % state)

    @staticmethod
    def _verify_file_exist(file_name, mount_point, actual, expected):
        if actual:
            LOG.info("Find %s under %s!" % (file_name, mount_point))
            if actual != expected:
                raise exceptions.TestFail("Expected not find the file %s."
                                          % file_name)
        else:
            LOG.info("%s not found under %s" % (file_name, mount_point))
            if actual != expected:
                raise exceptions.TestFail("Expected can find the file %s."
                                          % file_name)

    def test_rbd_remote_backup(self):
        """
        This test basically performs following steps:
            1. create rbd in testpool
            2. format disk
            3. create remote backup for this rbd(e.g.record1)
            4. write data to this rbd via ISCSI, include 1->11 steps
            5. create remote backup for this rbd(e.g.record2)
            6. recover rbd from record1
            7. repeat step3: sub-step 2)3)4)5)7)
            8. check testfile.txt does not exist
            9. do recover rbd from record2
            10. check testfile.txt exists
        """
        mount_point = self.params.get('mount_point', '/mnt')
        file_name = self.params.get('file_name', 'testfile.txt')
        # step1 create rbd in testpool
        self.rbd_id = test_utils.create_rbd(self.pool_id, self.params)
        LOG.info("Create rbd %s in pool %s" % (self.rbd_id, self.pool_id))
        # step2 format disk
        self._create_and_bind_ISCSI_to_rbd(self.rbd_id)
        time.sleep(60)
        need_mk = True
        create_data = False
        find = test_utils.operate_iscsi(self.control_server_ip,
                                        self.control_username,
                                        self.control_password,
                                        self.initiator_ip,
                                        self.initiator_username,
                                        self.initiator_password,
                                        self.iscsi_target_name,
                                        self.initiator_ip, mount_point,
                                        file_name, need_mk, create_data)
        self._verify_file_exist(file_name, mount_point, find, False)
        self._delete_iscsi_lun(self.target_id, self.lun_id)
        time.sleep(60)
        # step3 create remote backup for this rbd
        rbtask_id_1 = self._start_rbtask(self.rbd_id)
        rb_record_1 = self._verify_task_successfully(rbtask_id_1, 'backed_up')
        # step4 write data to this rbd via ISCSI
        self.lun_id = self._create_iscsi_lun(self.target_id, self.rbd_id)
        time.sleep(60)
        need_mk = False
        create_data = True
        # step4: sub-step 2)-10)
        find = test_utils.operate_iscsi(self.control_server_ip,
                                        self.control_username,
                                        self.control_password,
                                        self.initiator_ip,
                                        self.initiator_username,
                                        self.initiator_password,
                                        self.iscsi_target_name,
                                        self.initiator_ip, mount_point,
                                        file_name, need_mk, create_data)
        self._verify_file_exist(file_name, mount_point, find, True)
        # step4: sub-step 11)
        self._delete_iscsi_lun(self.target_id, self.lun_id)
        time.sleep(60)
        # step 5 create remote backup for this rbd
        rbtask_id_2 = self._start_rbtask(self.rbd_id)
        rb_record_2 = self._verify_task_successfully(rbtask_id_2, 'backed_up')
        # step 6 recover rbd from rb_record_1
        restore_id = self._start_restore(self.rbd_id, rb_record_1)
        self._verify_task_successfully(restore_id, 'restored')
        # step 7
        self.lun_id = self._create_iscsi_lun(self.target_id, self.rbd_id)
        time.sleep(60)
        need_mk = False
        create_data = False
        find = test_utils.operate_iscsi(self.control_server_ip,
                                        self.control_username,
                                        self.control_password,
                                        self.initiator_ip,
                                        self.initiator_username,
                                        self.initiator_password,
                                        self.iscsi_target_name,
                                        self.initiator_ip, mount_point,
                                        file_name, need_mk, create_data)
        # step 8 check testfile.txt does not exist
        self._verify_file_exist(file_name, mount_point, find, False)
        self._delete_iscsi_lun(self.target_id, self.lun_id)
        time.sleep(60)
        # step 9 do recover rbd from record2
        restore_id = self._start_restore(self.rbd_id, rb_record_2)
        self._verify_task_successfully(restore_id, 'restored')
        # step 10 verify testfile.txt exists
        self.lun_id = self._create_iscsi_lun(self.target_id, self.rbd_id)
        time.sleep(60)
        need_mk = False
        create_data = False
        find = test_utils.operate_iscsi(self.control_server_ip,
                                        self.control_username,
                                        self.control_password,
                                        self.initiator_ip,
                                        self.initiator_username,
                                        self.initiator_password,
                                        self.iscsi_target_name,
                                        self.initiator_ip, mount_point,
                                        file_name, need_mk, create_data)
        self._verify_file_exist(file_name, mount_point, find, True)
        self._delete_iscsi_lun(self.target_id, self.lun_id)

    def teardown(self):
        if self.target_id:
            self._delete_target(self.target_id)
        if self.rbd_id:
            try:
                test_utils.delete_rbd(self.pool_id, self.rbd_id, self.params)
            except exceptions.UnexpectedResponseCode, e:
                pass
