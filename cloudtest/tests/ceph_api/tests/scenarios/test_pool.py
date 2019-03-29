import os
import logging
import time

from avocado.core import test
from avocado.core import exceptions

from cloudtest import remote
from cloudtest import data_dir
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.pools_client import PoolsClient
from cloudtest.tests.ceph_api.lib.rbd_client import RbdClient


LOG = logging.getLogger('avocado.test')


class TestPool(test.Test):
    """
    Scenario for testing tool related operations.
    """
    def __init__(self, params, env):
        self.params = params
        self.body = {}
        self.env = env
        self.pool_client = PoolsClient(params)
        self.rbd_client = RbdClient(params)

        self.dstpath = '/root'
        self.workload_path = data_dir.COMMON_TEST_DIR
        LOG.info('******************%s' % self.workload_path)
        self.fio_version = self.params.get('fio_version')
        self.fio_working_path = None

    def setup(self):
        if 'cluster' in self.env:
            self.cluster_id = self.env['cluster']
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')

        ceph_server_ip = self.params.get('ceph_management_url')
        self.mid_host_ip = ceph_server_ip.split(':')[1].strip('/')
        self.mid_host_user = self.params.get('ceph_server_ssh_username')
        self.mid_host_password = self.params.get('ceph_server_ssh_password')
        self.end_host_user = self.params.get('ceph_node_ssh_username')
        self.end_host_passwprd = self.params.get('ceph_node_ssh_password')

        self.ioengine = self.params.get('ioengine', 'rbd')
        self.clientname = self.params.get('clientname', 'admin')
        self.rw = self.params.get('rw', 'write')
        self.bs = self.params.get('bs', '4k')
        self.iodepth = self.params.get('iodepth', 1024)
        self.numjobs = self.params.get('numjobs', 2)
        self.direct = self.params.get('direct', 1)
        self.size = self.params.get('size', '1M')

        self.end_host_ip = test_utils.get_available_host_ip(self.params)

    def _query_pool(self, pool_id, group_id, size, pg_num):
        # Test query pools in a specified cluster
        resp = self.pool_client.query()
        LOG.info("Got all pool %s" % resp)
        if not len(resp) > 0:
            raise exceptions.TestFail("Query pools failed" )
        for i in range(len(resp)):
            if resp[i]['id'] == pool_id:
                if resp[i]['group_id'] != group_id:
                    raise exceptions.TestFail("Group id is not expected for "
                                              "pool%s" % pool_id)
                elif resp[i]['pg_num'] != pg_num:
                    raise exceptions.TestFail("Pg_num is not expected for "
                                              "pool%s" % pool_id)
                else:
                    return resp[i]['name']

    def _update_pool(self, pool_id, size, group_id, pg_num):
        """
        Execute the test of updating a pool
        """
        # sleep 60s, otherwise it may raise error about "the pool is not ready"
        pool_name = 'cloudtest_' + utils.utils_misc.generate_random_string(6)
        vgroup_id = test_utils.get_available_vgroup(self.params)

        if self.params.get('NO_EC', "true") == "true":
            update_pool = {'name': pool_name,
                           'size': size,
                           'group_id': group_id,
                           'pg_num': pg_num,
                           'vgroup_id': vgroup_id}
        else:
            update_pool = {'name': pool_name,
                           'group_id': self.params.get('rest_arg_group_id', 1),
                           'pg_num': self.params.get('rest_arg_pg_num', 80),
                           'vgroup_id': vgroup_id,
                           'safe_type': self.params.get('safe_type', 10),
                           'data_block_num': self.params.get('data_block_num',
                                                             3),
                           'code_block_num': self.params.get('code_block_num',
                                                             0),
                           'min_size': self.params.get('min_size', 1),
                           'max_bytes': self.params.get("max_bytes",
                                                        1073741824)
                           }
        resp = self.pool_client.update(pool_id, **update_pool)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Update pool failed: %s" % self.body)

        time.sleep(240)

    def _check_specified_rbd(self, pool_id, rbd_id):
        # Test query a specified rdb in a pool
        resp = self.rbd_client.query(pool_id, rbd_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("No specified rbd found in the pool")
        return resp['name']

    def _write_rbd(self, pool_name, rbd_name, flag=False):
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

        LOG.info("===cmd is %s" % cmd)
        remote.run_cmd_between_remotes(mid_host_ip=self.mid_host_ip,
                                       mid_host_user=self.mid_host_user,
                                       mid_host_password
                                       =self.mid_host_password,
                                       end_host_ip=self.end_host_ip,
                                       end_host_user=self.end_host_user,
                                       end_host_password
                                       =self.end_host_passwprd,
                                       cmd=cmd,
                                       timeout=1000)

    def _check_rbd_write(self, pool_id, rbd_name, start, offset):
        status = self._wait_for_write_rbd(pool_id, rbd_name, start, offset)
        if not status:
            raise exceptions.TestFail('Failed to write rbd %s' % rbd_name)
        LOG.info('Write rbd %s successfully !' % rbd_name)

    def _wait_for_write_rbd(self, pool_id, rbd_name, start, offset,
                            timeout=300):
        def is_rbd_create():
            resp = self.rbd_client.query(pool_id)
            LOG.info("Check used size %s" % resp)
            for i in range(len(resp)):
                if resp[i]['name'] == rbd_name \
                        and (resp[i]['usedsize'] == 0 or
                                     resp[i]['usedsize'] == offset):
                    LOG.info("usedsize is %s" % resp[i]['usedsize'])
                    LOG.info("start is %s" % start)
                    LOG.info("offset is %s" % offset)
                    return True
            return False

        return utils.utils_misc.wait_for(is_rbd_create, timeout, first=0,
                                         step=5, text='Waiting for rbd %s write.'
                                                      % rbd_name)

    def test_edit_pool(self):
        group_id = 1
        # Creating 1M rbd
        RBD_CAPACITY = 1024 * 1024

        self.pool_response = test_utils.create_pool(self.params, flag=True)
        self.pool_name = self.pool_response.get('name')
        self.pool_id = self.pool_response.get('id')
        self.rbd_response = test_utils.create_rbd_with_capacity(
            self.pool_id,
            self.params,
            RBD_CAPACITY)
        self.rbd_id = self.rbd_response.get('id')
        self.rbd_name = self.rbd_response.get('name')

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
        remote.scp_between_remotes(src=self.mid_host_ip,
                                   dst=self.end_host_ip,
                                   port=22,
                                   s_passwd=self.mid_host_password,
                                   d_passwd=self.end_host_passwprd,
                                   s_name=self.mid_host_user,
                                   d_name=self.end_host_user,
                                   s_path=os.path.join(self.dstpath,
                                                       self.fio_version),
                                   d_path=self.dstpath)
        self._write_rbd(self.pool_name, self.rbd_name, flag=True)
        self._check_rbd_write(self.pool_id, self.rbd_name, 0, 0)

        # Update the size and pg_num to the pool
        replicate = 2
        pg_num = 80
        self._update_pool(self.pool_id, replicate, group_id, pg_num)
        self.pool_name = \
            self._query_pool(self.pool_id, group_id, replicate, pg_num)

        self._write_rbd(self.pool_name, self.rbd_name, flag=True)
        self._check_rbd_write(self.pool_id, self.rbd_name, 0, 1024*1024)

        # Update the group to the pool
        group_id = 1
        self._update_pool(self.pool_id, replicate, group_id, pg_num)
        self.pool_name = \
            self._query_pool(self.pool_id, group_id, replicate, pg_num)

        self._write_rbd(self.pool_name, self.rbd_name, flag=True)
        self._check_rbd_write(self.pool_id, self.rbd_name, 0,
                              1024*1024)

    def teardown(self):
        if self.fio_working_path is not None:
            # delete files
            cmd_mid = 'rm -rf %s' % (os.path.join(self.dstpath, self.fio_version))
            cmd1 = 'pkill fio || true; '
            cmd2 = 'rm -rf %s %s' % (os.path.join(self.dstpath, self.fio_version),
                                 os.path.join(self.dstpath, self.fio_working_path))
            cmd = cmd1 + cmd2
            remote.run_cmd_between_remotes(mid_host_ip=self.mid_host_ip,
                                        mid_host_user=self.mid_host_user,
                                        mid_host_password
                                        =self.mid_host_password,
                                        end_host_ip=self.end_host_ip,
                                        end_host_user=self.end_host_user,
                                        end_host_password
                                        =self.end_host_passwprd,
                                        cmd=cmd,
                                        cmd_mid=cmd_mid)
        time.sleep(240)
        if self.rbd_id is not None:
            try:
                test_utils.delete_rbd(self.pool_id, self.rbd_id, self.params)
            except exceptions.UnexpectedResponseCode, e:
                pass

        # To do: Currently, all rbd deletion is delay deletion. So, the pool
        # cannot be deleted.
        #if self.pool_id is not None:
            #test_utils.delete_pool(self.pool_id, self.params)