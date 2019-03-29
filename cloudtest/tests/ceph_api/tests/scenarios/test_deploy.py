import time
import logging
import threading
import traceback
import sys
import re

from avocado.core import test
from avocado.core import exceptions
from cloudtest import remote
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.clusters_client import ClustersClient
from cloudtest.tests.ceph_api.lib.servers_client import ServersClient
from cloudtest.tests.ceph_api.lib.groups_client import GroupsClient

LOG = logging.getLogger('avocado.test')


class TestDeploy(test.Test):
    """
    Module for testing snapshot related operations.
    """

    def __init__(self, params, env):
        self.params = params
        self.env = env
        self.body = {}
        self.clusters_client = ClustersClient(params)
        self.servers_client = None

    def setup(self):
        LOG.info("Try to create cluster cloudtest_cluster")
        create_cluster = {'name': self.params.get('cluster_name',
                                                  'cloudtest_cluster'),
                          'addr': self.params.get('cluster_addr', 'vm')}
        resp = self.clusters_client.create(**create_cluster)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestSetupFail(
                "Create cluster failed: %s" % self.body)
        self.cluster_id = resp.body.get('id')

        self.params['cluster_id'] = self.cluster_id
        self.groups_client = GroupsClient(self.params)
        self.servers_client = ServersClient(self.params)
        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

    def _create_server(self, request_body):
        if not request_body.get('parent_bucket'):
            group_id, parent_id = \
                test_utils.get_available_group_bucket(self.params)
            request_body.update({'parent_bucket': parent_id})
        resp_body = self.servers_client.create(**request_body)
        body = resp_body.body
        status = test_utils.wait_for_server_in_status(
            'servername', request_body['servername'], self.servers_client,
            'added', 1, int(self.params.get('add_host_timeout', 800)))
        if not status:
            raise exceptions.TestFail("Failed to add server %s"
                                      % request_body['servername'])
        LOG.info('Create server %s successfully!'
                 % body['properties'].get('name'))

    def _deploy_cluster(self):
        self.clusters_client.deploy_cluster(self.cluster_id)
        status = test_utils.wait_for_cluster_in_status(self.cluster_id,
                                                       self.clusters_client,
                                                       'deployed',
                                                       int(self.params.get(
                                                           'deploy_host_timeout',
                                                           900)))
        if not status:
            raise exceptions.TestFail("Failed to deploy cluster %d" %
                                      self.cluster_id)
        LOG.info("Deploy cluster %d successfully!" % self.cluster_id)

    def _configure_zabbix_server(self):
        ceph_server_ip = self.params.get('ceph_management_url')
        # ceph_server_ip = ceph_server_ip.split(':')[1].strip('/')
        ceph_server_ip = test_utils.get_ip_from_string(ceph_server_ip)
        if not ceph_server_ip:
            msg = "get ceph server ip from management url error."
            logging.error(msg)
            raise exceptions.TestFail(msg)
        ceph_ssh_username = self.params.get('ceph_server_ssh_username',
                                            'root')
        ceph_ssh_password = self.params.get('ceph_server_ssh_password')
        LOG.info("Configuring zabbix server on Ceph server")
        session = remote.RemoteRunner(host=ceph_server_ip,
                                      username=ceph_ssh_username,
                                      password=ceph_ssh_password)
        cmd = 'source ~/localrc; '
        cmd += 'cephmgmtclient update-cluster-conf -c %s -z' % self.cluster_id
        cmd += ' %s -u admin -p zabbix -t 600 -r 10' % self.params.get('zabbix_server_ip')
        logging.info("cmd is:%s" % cmd)
        session.run(cmd)
        session.session.close()

    def test_deploy_cluster_with_multi_hosts(self):
        """
        This test basically performs following steps:
            1. create three hosts
            2. deploy the cluster
        """
        groups = self.groups_client.list_groups()
        parent_bucket = groups[0]['id']
        logging.info("cluster id is %s, parent_bucket id is %s" % (
            self.cluster_id, parent_bucket))
        # create three hosts
        isbackup = self.body.get('backup_node')
        i = 1
        threads = []
        while self.body.get('servername_%d' % i):
            tmp = 'servername_%d' % i
            servername = self.body.get(tmp, 'cloudtest_server_%d' % i)
            tmp = 'username_%d' % i
            username = self.body.get(tmp, 'root')
            tmp = 'password_%d' % i
            password = self.body.get(tmp, 'lenovo')
            tmp = 'publicip_%d' % i
            publicip = self.body.get(tmp)
            tmp = 'clusterip_%d' % i
            clusterip = self.body.get(tmp)
            tmp = 'managerip_%d' % i
            managerip = self.body.get(tmp)
            create_server_body = {'servername': servername,
                                  'username': username,
                                  'passwd': password,
                                  'publicip': publicip,
                                  'clusterip': clusterip,
                                  'managerip': managerip,
                                  'parent_bucket': parent_bucket,
                                  'backup_node': isbackup}
            t = threading.Thread(target=self._create_server,
                                 args=[create_server_body])
            threads.append(t)
            # self._create_server(create_server_body)
            i = i + 1
        # waiting for all servers ready
        for t in threads:
            t.setDaemon(True)
            t.start()

        for i in range(0, len(threads)):
            try:
                threads[i].join(800)
            except:
                logging.exception(
                    'Caught exception waiting for server %d added!' % i)
        logging.info('======start to _configure_zabbix_server=====')
        self._configure_zabbix_server()
        logging.info('======finished to _configure_zabbix_server=====')
        # deploy the cluster
        self._deploy_cluster()
        time.sleep(60)

    def teardown(self):
        pass
