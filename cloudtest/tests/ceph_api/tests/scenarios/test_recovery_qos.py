import logging
import os
import time

from avocado.core import test
from avocado.core import exceptions
from cloudtest import remote
from cloudtest import utils_misc
from cloudtest import data_dir
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.clustersconf_client import ClustersConfClient
from cloudtest.tests.ceph_api.lib.zabbix_client import ZabbixClient
from cloudtest.tests.ceph_api.lib.clusters_client import ClustersClient
from cloudtest.tests.ceph_api.lib.servers_client import ServersClient


LOG = logging.getLogger('avocado.test')


class TestRecoveryQOS(test.Test):
    """
    Cluster recover speed limited by recovery QOS related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.clusterconf_client = ClustersConfClient(params)
        self.zabbix_client = ZabbixClient(params)
        self.cluster_client = ClustersClient(params)
        self.server_client = ServersClient(params)
        self.body = {}
        self.env = env
        self.pool_id = None
        self.pool_name = None
        self.recover_item_id = None
        self.statistical_time = self.params.get('statistical_time', 1800)
        self.interval_time = self.params.get('interval_time', 30)
        self.rbds_id = []
        self.dstpath = '/root'
        self.workload_path = data_dir.COMMON_TEST_DIR
        self.fio_version = self.params.get('fio_version')
        self.fio_working_path =\
            self.fio_version[0:len(self.fio_version) - len('.tar.gz')]
        self.mid_host_ip =\
            self.params.get('ceph_management_url').split(':')[1].strip('/')
        self.mid_host_user = self.params.get('ceph_server_ssh_username')
        self.mid_host_password = self.params.get('ceph_server_ssh_password')
        self.end_host_user = self.params.get('ceph_node_ssh_username')
        self.end_host_password = self.params.get('ceph_node_ssh_password')
        self.end_host_ip = test_utils.get_available_host_ip(self.params)

        self.server_name = None
        self.server_id = None

    def setup(self):
        """
        Set up before executing test
        1. Cluster is deployed
        2. 5 100G rbd/image are created, and sequence writen
        3. Zabbix server and account is configured
        4. More hosts are available for adding
        """
        # cluster is deployed
        if 'cluster' in self.env:
            self.cluster_id = self.env['cluster']
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')
        else:
            raise exceptions.TestSetupFail(
                "Please set cluster_id in config first")

        self.pool_response = test_utils.create_pool(self.params,
                                                           flag=True)
        self.pool_name = self.pool_response.get('name')
        self.pool_id = self.pool_response.get('id')

        # 5 100G rbd/image are created, and sequence writen
        self._copy_fio_package_to_host()
        self.params['capacity'] = 1024*1024*1024*100
        rw = self.params.get('fio_rw', 'write')
        bs = self.params.get('fio_bs', '1M')
        iodepth = self.params.get('fio_iodepth', 128)
        size = self.params.get('fio_write_size', '100G')
        flag = True
        for i in range(0, 5):
            rbd_name = 'cloudtest_' + utils_misc.generate_random_string(6)
            self.params['rbd_name'] = rbd_name
            rbd_id = test_utils.create_rbd(self.pool_id, self.params)
            LOG.info("Create rbd %s in pool %s" % (rbd_name, self.pool_id))
            self.rbds_id.append(rbd_id)
            self._write_rbd(rbd_name=rbd_name, rw=rw, bs=bs, iodepth=iodepth,
                            size=size, flag=flag)
            flag = False

        zabbix_ip = remote.get_zabbix_server_ip(self.mid_host_ip,
                                                self.mid_host_user,
                                                self.mid_host_password)
        self.params['rest_arg_zabbix_server_ip'] = zabbix_ip
        self.params['rest_arg_ntp_server_ip'] = zabbix_ip
        # Zabbix server and account is configured
        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v
        self._set_cluster_conf()
        zabbix_group_id = self.zabbix_client.get_host_group("cloudCeph")
        LOG.info("The cloudCeph group id in zabbix is %s" % zabbix_group_id)
        if zabbix_group_id:
            host_id = self.zabbix_client.get_host_id_by_group_id(zabbix_group_id)
            LOG.info("Monitored host id in zabbix is %s" % host_id)
        if host_id:
            self.recover_item_id = self.zabbix_client.get_item_id(
                host_id, "ceph.cluster.recovering_bytes")
            LOG.info("The ceph.cluster.recovering_bytes item id in zabbix is %s"
                     % self.recover_item_id)
        else:
            raise exceptions.TestSetupFail(
                "Zabbix server error, cannot get host id!")
        if self.recover_item_id is None:
            exceptions.TestSetupFail(
                "Cannot get the value of ceph.cluster.recovering_bytes!")

    def _set_cluster_conf(self):
        resp = self.clusterconf_client.set(self.cluster_id, self.body)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Set cluster conf failed: %s" % self.body)
        LOG.info("Set cluster conf: %s" % self.body)
        time.sleep(30)

    def _copy_fio_package_to_host(self):
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

    def _write_rbd(self, rbd_name, rw, bs, iodepth, size, flag=False):
        cmd1 = 'cd %s;' % self.fio_working_path
        cmd2 = './fio -ioengine=rbd -clientname=admin '
        cmd3 = '-pool=%s -rw=%s -bs=%s -iodepth=%s -numjobs=1 -direct=1 ' % \
               (self.pool_name, rw, bs, iodepth)
        cmd4 = '-size=%s -runtime=20 -group_reporting -rbdname=%s -name=mytest' % \
               (size, rbd_name)
        cmd = cmd1 + cmd2 + cmd3 + cmd4
        if flag:
            cmd = 'tar -xzvf %s;' % self.fio_version + cmd
        LOG.info("cmd = %s" % cmd)

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

    def _wait_for_recovery_to_begin(self, timeout=60):
        def is_recovery_start():
            resp = self.zabbix_client.get_item_history(self.recover_item_id, 1)
            if not len(resp):
                return False
            LOG.info("Item ceph.cluster.recovering_bytes latest data: %s"
                     % resp)
            if resp[0].get('value') != '0':
                    return True
            return False

        return utils_misc.wait_for(is_recovery_start, timeout, first=0, step=5,
                                   text='Waiting for recovery to begin.')

    def _check_qos(self, max_recover_bw):
        time.sleep(self.statistical_time)
        times = self.statistical_time / self.interval_time
        resp = self.zabbix_client.get_item_history(
            self.recover_item_id,
            times)
        LOG.info("Item ceph.cluster.recovering_bytes history: %s" % resp)
        total = 0
        for item in resp:
            total = total + float(item.get('value'))
        avg_value = total / self.statistical_time / 1024 / 1024
        if avg_value > max_recover_bw:
            raise exceptions.TestFail(
                "Flow is above the set value: %sMBPS > %sMBPS"
                % (avg_value, max_recover_bw))
        else:
            LOG.info("Flow is %s" % avg_value)

    def test(self):
        """
        1. Set begin and endtime for rush hour 150MBPS
        2. Add host to cluster in order to let cluster begin to recover,
        check QOS via zabbix is under value set for rush hour(error range 10%)
        3. Set begin and endtime for non-rush hour 200MBPS
        4. Remove osd to cluster in order to let cluster begin to recover,
        check QOS via zabbix is under value set for non-rush hour(error range 10%)
        """
        # set rush hour to current time
        day_recover_bw_max = float(self.body['day_recover_bw']) * 1.1
        localtime = time.localtime(time.time())
        self.body['daylight_begin'] = '%d:%d' \
                                      % (localtime.tm_hour, localtime.tm_min)
        self.body['daylight_end'] = '%d:%d' \
                                    % (localtime.tm_hour + 1, localtime.tm_min)
        self._set_cluster_conf()
        # Add host to start recovery
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

        # check QOS via zabbix is under value set for rush hour(error range 10%)
        self._check_qos(day_recover_bw_max)

        # set non-rush hour to current time
        night_recover_bw_max = float(self.body['night_recover_bw']) * 1.1
        localtime = time.localtime(time.time())
        self.body['daylight_begin'] = '%d:%d' \
                                      % (localtime.tm_hour-1, localtime.tm_min)
        self.body['daylight_end'] = '%d:%d' \
                                    % (localtime.tm_hour, localtime.tm_min)
        self._set_cluster_conf()
        # Remove osd to start recover
        server_id = test_utils.get_available_server(self.params)
        osd_id = test_utils.get_available_osd(server_id, self.params)
        test_utils.delete_osd(server_id, self.params, osd_id)
        time.sleep(60)
        # check QOS via zabbix is under value set for non-rush hour(error range 10%)
        self._check_qos(night_recover_bw_max)

    def teardown(self):
        """
        Some clean up work will be done here.
        """
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
                                        =self.end_host_password,
                                        cmd=cmd,
                                        cmd_mid=cmd_mid)
        for rbd_id in self.rbds_id:
            try:
                test_utils.delete_rbd(self.pool_id, rbd_id, self.params)
            except exceptions.UnexpectedResponseCode, e:
                pass

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
