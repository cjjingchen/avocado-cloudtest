import logging
import random
import time
import copy
from datetime import date, datetime, timedelta

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib.remotebackup_client import RemoteBackupClient
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest import utils_misc

LOG = logging.getLogger('avocado.test')


class TestRemoteBackup(test.Test):
    """
    Remote backup related tests.
    """

    def __init__(self, params, env):
        self.params = params
        self.body = {}
        self.env = env
        self.cluster_id = ""
        self.des_cluster_id = ""
        self.src_ip = ""
        self.src_host_id = ""
        self.des_ip = ""
        self.des_host_id = ""

    def setup(self):
        """
        Set up before executing test
        """
        if 'cluster' in self.env:
            self.cluster_id = self.env.get('cluster')
        elif self.params.get('cluster_id'):
            self.cluster_id = int(self.params.get('cluster_id'))
        else:
            raise exceptions.TestSetupFail(
                'Please set cluster_id in config first')

        self.params['cluster_id'] = self.cluster_id
        self.client = RemoteBackupClient(self.params)

        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

    def __get_dest_site(self):
        self.dest_site = test_utils.get_available_backup_site(self.params)

    def __set_time_params(self):
        self.create_time = str(datetime.utcnow())
        self.end_time = str(date.today() + timedelta(days=1))
        self.startTime = str(datetime.utcnow())
        self.start_time = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
        self.startDt = str(datetime.utcnow())

    def __get_pool_rbd_id(self):
        rbd_list = []
        pool_id = test_utils.get_pool_id(self.env, self.params)
        if self.params.get("rbd_count"):
            rbd_count = int(self.params.get("rbd_count"))
            for i in range(rbd_count):
                rbd_id = test_utils.create_rbd(pool_id=pool_id, params=self.params)
                rbd_list.append(str(rbd_id))
        else:
            rbd_id = test_utils.create_rbd(pool_id=pool_id, params=self.params)
            rbd_list.append(str(rbd_id))

        return pool_id, rbd_list

    def __waite_for_backup(self, pool_id, rbd_id):
        def is_backup_ready():
            resp = self.client.get_backup_list(pool_id=pool_id, rbd_id=rbd_id)
            for backup in resp:
                if str(backup.get("rbd_id")) == rbd_id:
                    self.env["backup_pool_id"] = str(backup.get("pool_id"))
                    self.env["backup_rbd_id"] = str(backup.get("rbd_id"))
                    self.env["backup_snapshot_name"] = backup.get("snap_name")
                    self.env["backup_site"] = backup.get("site_uuid")
                    return True
            return False

        return utils_misc.wait_for(func=is_backup_ready, timeout=1200,
                                   first=0.0, step=10.0,
                                   text="Waiting for rbd remote backup")

    def test_rbd_remote_backup(self):
        self.__get_dest_site()
        self.__set_time_params()
        self.body["min"] = self.create_time
        self.body["dest_site"] = self.dest_site
        self.body["start_time"] = self.start_time

        pool_id, rbd_list = self.__get_pool_rbd_id()

        self.body["pool_id"] = pool_id
        self.body["rbd_list"] = rbd_list

        self.client.rbd_remote_backup(**self.body)

        status = self.__waite_for_backup(pool_id, rbd_list[0])
        if not status:
            raise exceptions.TestFail("Failed to backup rbd %s"
                                      % str(rbd_list))
        LOG.info("%s" % self.env)

    def test_rbd_restore(self):
        self.body["dest_site"] = self.env.get("backup_site")
        self.body["snap_time"] = self.env.get("backup_snapshot_name")
        self.body["id"] = self.env.get("backup_snapshot_name")
        self.body["cluster_id"] = self.cluster_id
        self.body["rbd_id"] = self.env.get("backup_rbd_id")
        self.body["pool_id"] = self.env.get("backup_pool_id")
        resp = self.client.rbd_restore(**self.body)
        LOG.info("%s" % resp.body)

    def test_get_backup_list(self):
        pool_id = self.env.get("backup_pool_id")
        rbd_id = self.env.get("backup_rbd_id")
        resp = self.client.get_backup_list(pool_id, rbd_id)
        LOG.info("%s" % resp)
        if not len(resp):
            raise exceptions.TestFail("Failed to get backup list!")

    def test_add_rbtask(self):
        flag = False
        self.__get_dest_site()
        self.__set_time_params()
        self.body["min"] = self.create_time
        self.body["dest_site"] = self.dest_site
        self.body["end_time"] = self.end_time
        self.body["startTime"] = self.startTime
        self.body["start_time"] = self.start_time
        self.body["startDt"] = self.startDt
        self.body["rbtask_name"] = "cloudtest_task_" \
                                   + utils_misc.generate_random_string(6)

        pool_id, rbd_list = self.__get_pool_rbd_id()

        self.body["pool_id"] = pool_id
        self.body["rbd_list"] = rbd_list

        resp = self.client.add_rbtask(**self.body)
        time.sleep(5)
        self.env["rbtask_name"] = self.body.get("rbtask_name")

        resp_query = self.client.get_rbtask_list()
        for task in resp_query.get("items"):
            if task.get("rbtask_name") == self.body.get("rbtask_name"):
                self.env["rbtask"] = task
                flag = True

        LOG.info("%s" % resp)
        if not flag:
            raise exceptions.TestFail("Failed to add rbtask!")

    def test_modify_rbtask(self):
        self.body = copy.deepcopy(self.env.get("rbtask"))
        self.body["frequency"] = "monthly"
        del self.body["id"]
        task_id = self.env["rbtask"]["id"]
        resp = self.client.modify_rbtask(task_id, **self.body)
        LOG.info("%s" % resp)

    def test_get_rbtask_list(self):
        resp = self.client.get_rbtask_list()
        LOG.info("%s" % resp.get("items"))
        if not len(resp.get("items")):
            raise exceptions.TestFail("No rbtask found!")
        for task in resp.get("items"):
            if task.get("rbtask_name") == self.env.get("rbtask_name"):
                self.env["rbtask"] = task
                LOG.info("%s" % self.env["rbtask"])

    def test_delete_rbtask(self):
        rbtask_id = self.env["rbtask"]["id"]
        flag = True
        resp = self.client.delete_rbtask(task_id=rbtask_id)
        resp_query = self.client.get_rbtask_list()
        for task in resp_query.get("items"):
            if task.get("id") == rbtask_id:
                flag = False
        LOG.info("%s" % resp)
        if not flag:
            raise exceptions.TestFail("Failed to delete rbtask!")

    def test_get_remotebackup_log(self):
        resp = self.client.get_remotebackup_log()
        if not len(resp.get("items")):
            raise exceptions.TestFail("No remote backup log found!")
        LOG.info("%s" % resp.get("items"))

    def test_add_backup_site(self):

        self.client.add_backup_site(self.body)

    def test_get_backup_site_list(self):

        response = self.client.get_backup_site_list()
        if 'tmp_site_id' not in self.env.keys() or not self.env['tmp_site_id']:
            ceph_backup_site = [resps for resps in response if
                                resps['type'] not in 'S3']
            backup_site_del = \
                [resps for resps in response if resps['external_site'] is True]
            backup_site_for_update = random.choice(ceph_backup_site)
            backup_site_to_del = random.choice(backup_site_del)
            self.env['tmp_site_id'] = backup_site_for_update['id']
            self.env['tmp_site_name'] = backup_site_for_update['name']
            self.env['del_site_id'] = backup_site_to_del['id']
            self.env['del_site_name'] = backup_site_to_del['name']
            logging.info('tmp_site_id is %s, tmp_site_name is %s' % (
                self.env['tmp_site_id'], self.env['tmp_site_name']))

    def test_update_backup_site(self):

        if 'tmp_site_id' not in self.env.keys() or not self.env['tmp_site_id']:
            self.test_get_backup_site_list()
        self.client.update_backup_site(self.env['tmp_site_id'], **self.body)

    def test_del_backup_site(self):

        if 'del_site_id' not in self.env.keys() or not self.env['del_site_id']:
            self.test_get_backup_site_list()
        self.client.del_backup_site(self.env['del_site_id'])
        logging.info('del_site_id is %s, del_site_name is %s' % (
                        self.env['del_site_id'], self.env['del_site_name']))

    def __set_params(self):
        if not self.params.get('rest_arg_des_cluster_id'):
            clusters = test_utils.get_available_clusters(self.params)
            if len(clusters) < 2:
                raise exceptions.TestSetupFail(
                    'There are not enough clusters!')
            for cluster in clusters:
                if cluster['id'] != self.cluster_id:
                    self.des_cluster_id = cluster['id']
                    self.params['rest_arg_des_cluster_id'] = cluster['id']
                    LOG.info("des_cluster_id = %s" % self.des_cluster_id)
                    break
            src_host = test_utils.get_available_server_info(self.params,
                                                            self.cluster_id)
            self.src_ip = src_host['publicip']
            self.params['rest_arg_src_ip'] = self.src_ip
            LOG.info('src_ip = %s' % self.src_ip)
            self.src_host_id = src_host['id']
            self.params['rest_arg_src_host_id'] = self.src_host_id
            LOG.info('src_host_id = %s' % self.src_host_id)
            des_host = test_utils.get_available_server_info(self.params,
                                                            self.des_cluster_id)
            self.des_ip = des_host['publicip']
            self.params['rest_arg_des_ip'] = self.des_ip
            LOG.info('des_ip = %s' % self.des_ip)
            self.des_host_id = des_host['id']
            self.params['rest_arg_des_host_id'] = self.des_host_id
            LOG.info('des_host_id = %s' % self.des_host_id)

        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

    def test_set_rbpolicy(self):
        """
        Execute the test of rbdpolicy configuration.
        :return: 
        """
        self.__set_params()
        self.client.configure_rbpolicy(**self.body)

    def test_delete_rbpolicy(self):
        self.client.delete_rbpolicy()
        resp = self.client.query_rbpolicy()
        body = resp.body
        if len(body):
            raise exceptions.TestError('Failed to delete rbpolicy!')

    def test_query_rbpolicy(self):
        resp = self.client.query_rbpolicy()
        body = resp.body
        if not len(body):
            raise exceptions.TestError('No rbpolicy found!')

    def test_start_rbtask(self):
        LOG.info('cluster_id %s' % self.params.get('cluster_id'))
        rbd_id = test_utils.create_rbd(self.pool_id, self.params)
        body = {'rbd_id': rbd_id}
        self.env['rbtask_rbd_id'] = rbd_id
        resp = self.client.start_rbtask(**body)
        time.sleep(10)
        body = resp.body
        if not len(body):
            raise exceptions.TestError('Failed to start rbtask!')
        self.env['rbtask_id'] = body.get('id')
        self.env['remote_timestamp'] = body['properties']['timestamp']

    def test_list_rbtasks(self):
        extra_url = '/list_rbtasks?count=1024&begin_index=0'
        resp = self.client.list_rbtasks(extra_url)
        if not len(resp):
            raise exceptions.TestError('No rbtasks found!')

    def test_query_restore_time(self):
        rbd_id = self.env.get('rbtask_rbd_id')
        resp = self.client.query_restore(rbd_id)
        if not len(resp):
            raise exceptions.TestError('No restore time found!')

    def test_start_restore(self):
        rbd_id = self.env.get('rbtask_rbd_id')
        snap_time = self.env.get('remote_timestamp')
        body = {'snap_time': snap_time}
        resp = self.client.start_restore(rbd_id, **body)
        body = resp.body
        if not len(body):
            raise exceptions.TestError('Failed to start restore!')

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        pass
