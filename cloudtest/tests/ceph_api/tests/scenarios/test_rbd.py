import os
import logging
import time

from avocado.core import test
from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest import remote
from cloudtest import data_dir
from cloudtest.tests.ceph_api.lib.clusters_client import ClustersClient
from cloudtest.tests.ceph_api.lib.pools_client import PoolsClient
from cloudtest.tests.ceph_api.lib.rbd_client import RbdClient
from cloudtest.tests.ceph_api.lib.servers_client import ServersClient
from cloudtest.tests.ceph_api.lib import test_utils

LOG = logging.getLogger('avocado.test')


class TestRbd(test.Test):
    """
    Module for test rbd related operations.
    """

    def __init__(self, params, env):
        self.params = params
        self.env = env
        self.cluster_client = ClustersClient(params)
        self.pool_client = PoolsClient(params)
        self.rbd_client = RbdClient(params)
        self.server_client = ServersClient(params)
        self.pool_id_before = None
        self.pool_name_before = None
        self.rbd_name_before = None
        self.pool_id_after = None
        self.pool_name_after = None
        self.rbd_name_after = None
        self.dstpath = '/root'
        self.workload_path = data_dir.COMMON_TEST_DIR
        LOG.info('******************%s' % self.workload_path)
        self.fio_version = self.params.get('fio_version')
        self.fio_working_path = None

        self.target_pool = None
        self.rbd_id = None
        self.server_name = None
        self.server_id = None

    def setup(self):
        ceph_server_ip = self.params.get('ceph_management_url')
        self.mid_host_ip = ceph_server_ip.split(':')[1].strip('/')
        self.cluster_id = self.params.get('cluster_id')
        self.mid_host_user = self.params.get('ceph_server_ssh_username')
        self.mid_host_password = self.params.get('ceph_server_ssh_password')
        self.end_host_user = self.params.get('ceph_node_ssh_username')
        self.end_host_password = self.params.get('ceph_node_ssh_password')
        self.ioengine = self.params.get('ioengine', 'rbd')
        self.clientname = self.params.get('clientname', 'admin')
        self.rw = self.params.get('rw', 'write')
        self.bs = self.params.get('bs', '1M')
        self.iodepth = self.params.get('iodepth', 1024)
        self.numjobs = self.params.get('numjobs', 1)
        self.direct = self.params.get('direct', 1)
        self.size = self.params.get('size', '2M')

        #self.pool_id = self.params.get('pool_id', 1)

        self.end_host_ip = test_utils.get_available_host_ip(self.params)

    def test_image_write_read(self):
        RBD_CAPACITY = 10485760

        self.fio_working_path = \
            self.fio_version[0:len(self.fio_version) - len('.tar.gz')]
        LOG.info('Copy file %s from local to %s' % (self.fio_version,
                                                    self.mid_host_ip))
        remote.scp_to_remote(host=self.mid_host_ip,
                             port=22,
                             username=self.mid_host_user,
                             password=self.mid_host_password,
                             local_path=os.path.join(self.workload_path,
                                                     self.fio_version),
                             remote_path=self.dstpath)
        LOG.info('Copy file %s from %s to %s' % (self.fio_version,
                                                 self.mid_host_ip,
                                                 self.end_host_ip))
        remote.scp_between_remotes(src=self.mid_host_ip,
                                   dst=self.end_host_ip,
                                   port=22,
                                   s_passwd=self.mid_host_password,
                                   d_passwd=self.end_host_password,
                                   s_name=self.mid_host_user,
                                   d_name=self.end_host_user,
                                   s_path=os.path.join(self.dstpath,
                                                       self.fio_version),
                                   d_path=self.dstpath)

        self.pool_response_before = test_utils.create_pool(self.params, flag=True)
        self.pool_name_before = self.pool_response_before.get('name')
        self.pool_id_before = self.pool_response_before.get('id')
        self.rbd_response_before = test_utils.create_rbd_with_capacity(self.pool_id_before,
                                                                self.params,
                                                                RBD_CAPACITY)
        self.rbd_id_before = self.rbd_response_before.get('id')
        self.rbd_name_before = self.rbd_response_before.get('name')

        self.__write_rbd(self.pool_name_before, self.rbd_name_before, flag=True)
        self.__check_rbd_write(self.pool_id_before, self.rbd_name_before)

        self.server_name = test_utils.add_server(self.server_client,
                                                 self.params.get('rest_arg_servername'),
                                                 self.params.get('rest_arg_username'),
                                                 self.params.get('rest_arg_password'),
                                                 self.params.get('rest_arg_publicip'),
                                                 self.params.get('rest_arg_clusterip'),
                                                 self.params.get('rest_arg_managerip'),
                                                 self.params.get('rest_arg_parent_bucket'))
        LOG.info("added server name is %s" % self.server_name)
        test_utils.expand_cluster(self.cluster_client, self.server_client,
                                  self.cluster_id, self.server_name)

        self.pool_response_after = test_utils.create_pool(self.params,
                                                           flag=True)
        self.pool_name_after = self.pool_response_after.get('name')
        self.pool_id_after = self.pool_response_after.get('id')
        self.rbd_response_after = test_utils.create_rbd_with_capacity(
            self.pool_id_after,
            self.params,
            RBD_CAPACITY)
        self.rbd_id_after = self.rbd_response_after.get('id')
        self.rbd_name_after = self.rbd_response_after.get('name')
        self.__write_rbd(self.pool_name_before, self.rbd_name_before)

        self.__check_rbd_write(self.pool_id_before, self.rbd_name_before)

        self.__write_rbd(self.pool_name_after, self.rbd_name_after)
        self.__check_rbd_write(self.pool_id_after, self.rbd_name_after)

    def test_resize_migrage_delaydel(self):
        # Create rbd in the pool
        capacity = 1024 * 1024 * 1
        self.pool_id = test_utils.create_pool(self.params)
        self.rbd_id = test_utils.create_rbd_with_capacity(self.pool_id,
                                                          self.params,
                                                          capacity,
                                                          False)
        self._check_specified_rbd_size(self.rbd_id, capacity)

        new_name = 'cloudtest_new' + utils_misc.generate_random_string(6)
        updated_capacity = 1024 * 1024 * 2
        self._update_rdb_capacity(self.rbd_id, new_name, updated_capacity)

        self.target_pool = self._migrate_rbd(self.rbd_id)
        time.sleep(120)
        self._check_rbd_pool(self.rbd_id, self.target_pool)
        self._delay_delete_rbd(self.target_pool, self.rbd_id)
        self._check_delay_delete_rbd_list()

    def _check_specified_rbd_size(self, rbd_id, size):
        # Test query a specified rdb in a pool
        resp = self.rbd_client.query_specified_rbd(self.pool_id, rbd_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("No specified rbd found in the pool")
        if int(resp['size']) != size:
            raise exceptions.TestFail("The capacity of rbd created is NOT "
                                      "expected")

    def _update_rdb_capacity(self, rbd_id, name, size):
        """
        Execute the test of updating a rbd
        """
        update_rbd = {'name': name,
                      'object_size': 10,
                      'capacity': size}
        resp = self.rbd_client.update(self.pool_id, rbd_id, **update_rbd)
        LOG.info('Rest Response: %s' % resp)
        if not resp:
            raise exceptions.TestFail("Update rbd failed")

    def _migrate_rbd(self, rbd_id):
        """
        Test that migration of specified rdb
        """
        target_pool = test_utils.create_pool(self.params)
        move_rbd = {'target_pool': str(target_pool)}
        resp = self.rbd_client.migrate(self.pool_id, rbd_id, **move_rbd)
        LOG.info('Rest Response: %s' % resp)
        if not resp:
            raise exceptions.TestFail("Migarate rbd failed")

        return target_pool

    def _check_rbd_pool(self, rbd_id, expected_pool):
        # Test query a specified rdb in a pool
        resp = self.rbd_client.query_specified_rbd(expected_pool, rbd_id)
        LOG.info(resp)
        if not len(resp) > 0:
            raise exceptions.TestFail("No specified rbd found in the pool")
        if int(resp['pool_id']) != expected_pool:
            raise exceptions.TestFail("rbd %s is not in the expected pool" %
                                      rbd_id)

    def _delay_delete_rbd(self, pool_id, rbd_id):
        """
        Test the delay deletion for rdb
        """
        delay_time = time.strftime("%Y-%m-%d %H:%M:%S",
                                   time.localtime(time.time() + 60 * 60))
        resp = self.rbd_client.delay_delete_rbd(pool_id, rbd_id, delay_time)
        if not len(resp) > 0:
            raise exceptions.TestFail("Failed to set up delayed delete time")

    def _check_delay_delete_rbd_list(self):
        """
        Test the delay deletion for rdb
        """
        resp = self.rbd_client.delay_delete_rbd_list()
        if not len(resp) > 0:
            raise exceptions.TestFail(
                "No delay delete rbd found in the cluster")

    def __write_rbd(self, pool_name, rbd_name, flag=False):
        cmd1 = 'cd %s;' % self.fio_working_path
        cmd2 = './fio -ioengine=%s -clientname=%s ' % (self.ioengine,
                                                       self.clientname)
        cmd3 = '-pool=%s -rw=%s -bs=%s -iodepth=%s -numjobs=%s -direct=%s ' % \
               (pool_name, self.rw, self.bs, self.iodepth,
                self.numjobs, self.direct)
        cmd4 = '-size=%s -group_reporting -rbdname=%s -name=mytest' % \
               (self.size, rbd_name)
        cmd = cmd1 + cmd2 + cmd3 + cmd4
        if flag:
            cmd = 'tar -xzvf %s;' % self.fio_version + cmd
        remote.run_cmd_between_remotes(mid_host_ip=self.mid_host_ip,
                                       mid_host_user=self.mid_host_user,
                                       mid_host_password
                                       =self.mid_host_password,
                                       end_host_ip=self.end_host_ip,
                                       end_host_user=self.end_host_user,
                                       end_host_password
                                       =self.end_host_password,
                                       cmd=cmd,
                                       timeout=1000)

    def __check_rbd_write(self, pool_id, rbd_name):
        status = self.__wait_for_write_rbd(pool_id, rbd_name)
        if not status:
            raise exceptions.TestFail('Failed to write rbd %s' % rbd_name)
        LOG.info('Write rbd %s successfully !' % rbd_name)

    def __wait_for_write_rbd(self, pool_id, rbd_name, timeout=60):
        def is_rbd_create():
            resp = self.rbd_client.query(pool_id)
            for i in range(len(resp)):
                if resp[i]['name'] == rbd_name \
                        and resp[i]['usedsize'] >= 0:
                    return True
            return False

        return utils_misc.wait_for(is_rbd_create, timeout, first=0, step=5,
                                   text='Waiting for rbd %s write.' %
                                        rbd_name)

    def teardown(self):
        if self.fio_working_path is not None:
            # delete files
            cmd_mid = 'rm -rf %s' % (os.path.join(self.dstpath,
                                                  self.fio_version))
            cmd1 = 'pkill fio || true; '
            cmd2 = 'rm -rf %s %s' % \
                   (os.path.join(self.dstpath, self.fio_version),
                    os.path.join(self.dstpath, self.fio_working_path))
            cmd = cmd1 + cmd2
            remote.run_cmd_between_remotes(mid_host_ip=self.mid_host_ip,
                                           mid_host_user=self.mid_host_user,
                                           mid_host_password
                                           =self.mid_host_password,
                                           end_host_ip=self.end_host_ip,
                                           end_host_user=self.end_host_user,
                                           end_host_password
                                           =self.end_host_password,
                                           cmd=cmd,
                                           cmd_mid=cmd_mid)

        # Delete resource for scenario case14
        if self.rbd_id is not None and self.target_pool is not None:
            try:
                test_utils.delete_rbd(self.target_pool, self.rbd_id, self.params)
            except exceptions.UnexpectedResponseCode, e:
                pass
        # To do: Currently, all rbd deletion is delay deletion. So, the pool
        # cannot be deleted.
        #if self.target_pool is not None:
            #test_utils.delete_pool(self.target_pool, self.params)

        LOG.info("added server name is %s" % self.server_name)
        if self.server_name is not None:
            self.server_id = test_utils.get_server_id_by_name(self.params,
                                                              self.server_name)
            LOG.info("server id is %s" % self.server_id)
        if self.server_id is not None:
            LOG.info('Begin to sleep 60s ...')
            time.sleep(60)
            test_utils.delete_osd(self.server_id, self.params)
            test_utils.del_server(self.server_client, self.server_id)