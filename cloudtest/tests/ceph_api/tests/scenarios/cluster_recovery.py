import os
import re
import time
import logging
import threading

from avocado.core import test
from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest import remote
from cloudtest import data_dir
from cloudtest.tests.ceph_api.lib.clusters_client import ClustersClient
from cloudtest.tests.ceph_api.lib.servers_client import ServersClient
from cloudtest.tests.ceph_api.lib.monitors_client import MonitorsClient
from cloudtest.tests.ceph_api.lib.osd_client import OsdClient
from cloudtest.tests.ceph_api.lib.pools_client import PoolsClient
from cloudtest.tests.ceph_api.lib.rbd_client import RbdClient
from cloudtest.tests.ceph_api.lib import test_utils

LOG = logging.getLogger('avocado.test')
RBD_CAPACITY = 1048576*2


class ClusterRecovery(test.Test):
    """
    Module for test cluster recovery related operations.
    
    1. create pool
    2. create rbd
    3. run fio
    4. osd down, check cluster status and run fio second
    5. remove host, including remove osd and monitor, so monitor must follower
    6. check host remove successfully
    7. add host
    8. expand cluster
    9. add monitor for this host
    10. create pool, create rbd, run fio
    """
    def __init__(self, params, env):
        self.params = params
        self.env = env
        # storage server info for add server
        self.server = None
        self.cluster_client = ClustersClient(params)
        self.server_client = ServersClient(params)
        self.monitor_client = MonitorsClient(params)
        self.osd_client = OsdClient(params)
        self.dstpath = '/root'
        self.workload_path = data_dir.COMMON_TEST_DIR
        self.fio_version = self.params.get('fio_version')
        self.fio_working_path = \
            self.fio_version[0:len(self.fio_version) - len('.tar.gz')]

        self.server_name = None
        self.server_id = None

    def setup(self):
        ceph_server_ip = self.params.get('ceph_management_url')
        self.mid_host_ip = ceph_server_ip.split(':')[1].strip('/')
        self.cluster_id = self.params.get('cluster_id')
        self.mid_host_user = self.params.get('ceph_server_ssh_username')
        self.mid_host_password = self.params.get('ceph_server_ssh_password')
        self.end_host_user = self.params.get('ceph_node_ssh_username')
        self.end_host_passwprd = self.params.get('ceph_node_ssh_password')

        self.end_host_ip = test_utils.get_available_host_ip(self.params)

    def test(self):
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
                                   d_passwd=self.end_host_passwprd,
                                   s_name=self.mid_host_user,
                                   d_name=self.end_host_user,
                                   s_path=os.path.join(self.dstpath,
                                                       self.fio_version),
                                   d_path=self.dstpath)
        self.__create_pool()
        self.__create_rbd()
        self.__write_rbd(True)

        self.__get_available_server()
        self.__get_available_osd()
        self.__down_osd()

        # self.__check_cluster_status()
        status = self.__wait_for_ceph_in_status()
        if not status:
            raise exceptions.TestFail('Cluster status must be HEALTH_OK, '
                                      'or HEALTH_WARN for clock skew detected')
        self.__write_rbd()

        self.__del_osd()
        self.__del_monitor()
        self.__del_server()

        self.server_name = test_utils.add_server(self.server_client,
                                                 self.params.get(
                                                     'rest_arg_servername'),
                                                 self.params.get(
                                                     'rest_arg_username'),
                                                 self.params.get(
                                                     'rest_arg_password'),
                                                 self.params.get(
                                                     'rest_arg_publicip'),
                                                 self.params.get(
                                                     'rest_arg_clusterip'),
                                                 self.params.get(
                                                     'rest_arg_managerip'),
                                                 self.params.get(
                                                     'rest_arg_parent_bucket'))
        test_utils.expand_cluster(self.cluster_client, self.server_client,
                                  self.cluster_id, self.server_name)

        self.__create_monitor()
        status = self.__wait_for_ceph_in_status()
        if not status:
            raise exceptions.TestFail('Cluster status must be HEALTH_OK, '
                                      'or HEALTH_WARN for clock skew detected')
        # self.__check_cluster_status()
        self.__is_monitor_added()
        self.__create_pool()
        self.__create_rbd()
        self.__write_rbd()

    def __get_available_server(self):
        self.server_id = test_utils.get_available_server(self.params)
        body = {}
        servers = self.server_client.query(**body)
        for server in servers:
            if server.get('id') == self.server_id:
                self.server = server

    def __get_available_osd(self):
        self.osd_id = test_utils.get_available_osd(self.server_id,
                                                   self.params)

    def __down_osd(self):
        resp = self.osd_client.stop_osd(self.server_id, self.osd_id)
        if resp.get('status') != 'down':
            raise exceptions.TestFail("Stop osd '%s' failed" % self.osd_id)

    def __del_osd(self):
        test_utils.delete_osd(self.server_id, self.params)

    def __del_monitor(self):
        test_utils.delete_monitor(self.cluster_id,
                                  self.server_id,
                                  self.params)

    def __is_monitor_added(self):
        monitors = self.monitor_client.query(self.cluster_id)
        for monitor in monitors:
            if monitor.get('host') == self.server.get('servername'):
                return
        raise exceptions.TestFail('Failed to add monitor to %s' %
                                  self.server.get('servername'))

    def __del_server(self):
        self.server_client.delete_server(self.server_id)
        body = {}
        servers = self.server_client.query(**body)
        for server in servers:
            if server.get('id') == self.server_id:
                raise exceptions.TestFail('Failed to delete server %s'
                                          % self.server_id)
        LOG.info('Delete server successfully !')

    def __create_monitor(self):
        LOG.info('Create monitor ...')
        t1 = threading.Thread(target=self.monitor_client.create,
                              args=[self.cluster_id, self.server_id])
        t1.start()
        time.sleep(50)

    def __check_cluster_status(self):
        time.sleep(400)
        stdout_msg = remote.run_cmd_between_remotes(
            mid_host_ip=self.mid_host_ip,
            mid_host_user=self.mid_host_user,
            mid_host_password=self.mid_host_password,
            end_host_ip=self.end_host_ip,
            end_host_user=self.end_host_user,
            end_host_password=self.end_host_passwprd,
            cmd='ceph -s',
            timeout=1000)
        pat = 'health (.*)'
        result = re.findall(pat, stdout_msg)
        if len(result) > 0:
            if result[0] not in ('HEALTH_OK', 'HEALTH_WARN'):
                raise exceptions.TestFail('Cluster status must be HEALTH_OK, '
                                          'or HEALTH_WARN not %s' % result[0])
            if 'HEALTH_WARN' in result[0]:
                pat = 'Monitor clock skew detected'
                war_msg = re.findall(pat, stdout_msg)
                if not len(war_msg):
                    raise exceptions.TestFail(
                        'Cluster status must be HEALTH_OK, '
                        'or HEALTH_WARN for clock skew detected')
        else:
            raise exceptions.TestFail('Msg data error, please check !')
        LOG.info('Cluster recovery successfully !')

    def __wait_for_ceph_in_status(self):
        def is_in_status():
            stdout_msg = remote.run_cmd_between_remotes(
                mid_host_ip=self.mid_host_ip,
                mid_host_user=self.mid_host_user,
                mid_host_password=self.mid_host_password,
                end_host_ip=self.end_host_ip,
                end_host_user=self.end_host_user,
                end_host_password=self.end_host_passwprd,
                cmd='ceph -s',
                timeout=1000)
            pat = 'health (.*)'
            result = re.findall(pat, stdout_msg)
            if len(result) > 0:
                if result[0] not in ('HEALTH_OK', 'HEALTH_WARN'):
                    return False
                if 'HEALTH_WARN' in result[0]:
                    pat = 'Monitor clock skew detected'
                    war_msg = re.findall(pat, stdout_msg)
                    if not len(war_msg):
                        return False
            else:
                raise exceptions.TestFail('Msg data error, please check !')
            return True
        return utils_misc.wait_for(is_in_status, timeout=1000, first=0, step=50,
                                   text='Waiting for ceph in status')

    def __create_pool(self):
        resp = test_utils.create_pool(self.params, flag=True)
        self.pool_id = resp.get('id')
        self.pool_name = resp.get('name')

    def __create_rbd(self):
        resp = test_utils.create_rbd_with_capacity(self.pool_id,
                                                          self.params,
                                                          RBD_CAPACITY,
                                                          True)
        self.rbd_id = resp.get('id')
        self.rbd_name = resp.get('name')

    def __write_rbd(self, flag=False):
        cmd1 = 'cd %s;' % self.fio_working_path
        cmd2 = './fio -ioengine=rbd -clientname=admin '
        cmd3 = '-pool=%s -rw=write -bs=1M -iodepth=128 -numjobs=1 -direct=1 ' % \
               self.pool_name
        cmd4 = '-size=2M -group_reporting -rbdname=%s -name=mytest' % \
               self.rbd_name
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
                                       =self.end_host_passwprd,
                                       cmd=cmd,
                                       timeout=1000)

    def teardown(self):
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