#  -*- coding:utf-8 -*-

import os
import re
import time
import logging

from avocado.core import test
from avocado.core import exceptions
from cloudtest import remote
from cloudtest import data_dir
from cloudtest import utils_misc
from cloudtest.tests.ceph_api.lib.clusters_client import ClustersClient
from cloudtest.tests.ceph_api.lib.servers_client import ServersClient
from cloudtest.tests.ceph_api.lib.monitors_client import MonitorsClient
from cloudtest.tests.ceph_api.lib.osd_client import OsdClient
from cloudtest.tests.ceph_api.lib.pools_client import PoolsClient
from cloudtest.tests.ceph_api.lib import test_utils

LOG = logging.getLogger('avocado.test')
RBD_CAPACITY = 1024*1024*1024


class ClusterMaintenance(test.Test):
    def __init__(self, params, env):
        self.params = params
        self.env = env
        self.cluster_client = ClustersClient(params)
        self.server_client = ServersClient(params)
        self.monitor_client = MonitorsClient(params)
        self.pool_client = PoolsClient(params)
        self.osd_client = OsdClient(params)
        self.dstpath = '/root'
        self.workload_path = data_dir.COMMON_TEST_DIR
        self.fio_version = self.params.get('fio_version')
        self.fio_working_path = \
            self.fio_version[0:len(self.fio_version) - len('.tar.gz')]

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
        """
        1. start maintenance
        2. check osd, mon, agent status
        3. run fio
        5. wait 400s, stop maintenance, run step 2
        6. run step 4
        7. run fio
        """
        self.__copy_file()
        self.__get_available_server()
        self.__start_maintenance()
        status = self.__wait_for_osd_in_status('down')
        if not status:
            raise exceptions.TestFail('Osd status should be down, please check!')
        time.sleep(10)
        self.__check_monitor_status(status='inactive')
        self.__check_service_status(cmd='systemctl status sds-agent',
                                    pat='Active: (.*)',
                                    service_type='agent',
                                    status='dead')
        self.__get_pool_name_and_id()
        self.__create_rbd()
        self.__write_rbd(flag=True)
        osd_dict_before = self.__get_osd_capacity()
        LOG.info('Begin to sleep 300s ...')
        time.sleep(300)

        self.__stop_maintenance()
        status = self.__wait_for_osd_in_status(status='up')
        if not status:
            raise exceptions.TestFail('Osd status should be up, please check!')
        time.sleep(10)
        self.__check_monitor_status(status='active')
        self.__check_service_status(cmd='systemctl status sds-agent',
                                    pat='Active: (.*)',
                                    service_type='agent',
                                    status='running')
        self.__create_rbd()
        self.__write_rbd()
        osd_dict_after = self.__get_osd_capacity()
        self.__check_osd_capacity(osd_dict_before, osd_dict_after)

    def __copy_file(self):
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

    def __get_osd_capacity(self):
        """
        Get osd capacity var ceph osd df.
        """
        osd_dict = {}
        stdout_msg = remote.run_cmd_between_remotes(
            mid_host_ip=self.mid_host_ip,
            mid_host_user=self.mid_host_user,
            mid_host_password=self.mid_host_password,
            end_host_ip=self.end_host_ip,
            end_host_user=self.end_host_user,
            end_host_password=self.end_host_passwprd,
            cmd='ceph osd df',
            timeout=1000)
        stdout_msg = stdout_msg.strip()
        msg_list = stdout_msg.split('\n')
        for osd in self.osd_list:
            osd_id = osd.get('osdId')
            for msg in msg_list:
                msg = msg.strip()
                msg = msg.split()
                if msg[0].isdigit() and int(msg[0]) == osd_id:
                    osd_dict[osd_id] = float(msg[6])
        return osd_dict

    @staticmethod
    def __check_osd_capacity(osd_dict_before, osd_dict_after):
        """
        Check osd can use after host maintenance 2 hours.
        :param osd_dict_before: osd capacity in this host
               before run fio.
        :param osd_dict_after: osd capacity in this host
               after run fio.
        """
        for key in osd_dict_before.keys():
            if osd_dict_after[key] > osd_dict_before[key]:
                raise exceptions.TestFail('Osd AVAIL increased!')

    def __get_available_server(self):
        self.server_id = test_utils.get_available_server(self.params)

    def __start_maintenance(self):
        LOG.info('Start host maintenance...')
        self.server_client.start_maintenance(self.server_id)

    def __stop_maintenance(self):
        LOG.info('Stop host maintenance...')
        self.server_client.stop_maintenance(self.server_id)

    def __get_pool_name_and_id(self):
        pools = self.pool_client.query()
        if not len(pools):
            raise exceptions.TestSetupFail('No pool found!')
        self.pool_id = pools[0]['id']
        self.pool_name = pools[0]['name']

    def __create_rbd(self):
        resp = test_utils.create_rbd_with_capacity(self.pool_id,
                                                   self.params,
                                                   RBD_CAPACITY,
                                                   True)
        self.rbd_id = resp.get('id')
        self.rbd_name = resp.get('name')

    def __check_osd_status(self, status):
        LOG.info('Check osd status ...')
        resp = self.osd_client.get_osd_capacity(self.server_id)
        self.osd_list = resp['osds']
        for i in range(len(self.osd_list)):
            osd = self.osd_list[i]
            osd_name = osd['osdName']
            if osd.get('osdStatus') not in status:
                raise exceptions.TestFail('Osd %s status error(status: %s), '
                                          'status should be %s' %
                                          (osd_name, osd.get('osdStatus'),
                                           status))
        LOG.info('Check osd status pass !')

    def __wait_for_osd_in_status(self, status):
        def is_in_status():
            resp = self.osd_client.get_osd_capacity(self.server_id)
            self.osd_list = resp['osds']
            for i in range(len(self.osd_list)):
                osd = self.osd_list[i]
                if osd['osdStatus'] not in status:
                    return False
            return True
        return utils_misc.wait_for(is_in_status, timeout=360, first=0, step=30,
                                   text='Waiting for osd in status!')

    def __check_monitor_status(self, status):
        LOG.info('Check monitor status ...')
        resp = self.monitor_client.query(self.cluster_id, self.server_id)
        if len(resp) == 0:
            raise exceptions.TestFail('No minitor on server %s.' % self.server_id)
        if resp[0]['state'] not in status:
            raise exceptions.TestFail('Monitor state should be %s not %s' %
                                      (status, resp[0]['state']))

    def __check_service_status(self, cmd, pat, service_type, status=None):
        stdout_msg = remote.run_cmd_between_remotes(
            mid_host_ip=self.mid_host_ip,
            mid_host_user=self.mid_host_user,
            mid_host_password=self.mid_host_password,
            end_host_ip=self.end_host_ip,
            end_host_user=self.end_host_user,
            end_host_password=self.end_host_passwprd,
            cmd=cmd,
            timeout=1000)
        result = re.findall(pat, stdout_msg)
        if 'agent' in service_type:
            if len(result) != 0:
                if status in result[0]:
                    return
                raise exceptions.TestFail('Agent status error !')
        else:
            if len(result) != 0:
                raise exceptions.TestFail('Ceph goes to recovery mode!')

    def __write_rbd(self, flag=False):
        cmd1 = 'cd %s;' % self.fio_working_path
        cmd2 = './fio -ioengine=rbd -clientname=admin '
        cmd3 = '-pool=%s -rw=write -bs=1M -iodepth=128 -numjobs=1 -direct=1 ' % \
               self.pool_name
        cmd4 = '-size=1M -group_reporting -rbdname=%s -name=mytest' % \
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