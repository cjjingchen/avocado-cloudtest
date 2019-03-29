import logging

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib import utils
from cloudtest import remote
from cloudtest.tests.ceph_api.lib.clustersconf_client import ClustersConfClient


LOG = logging.getLogger('avocado.test')


class TestClustersConf(test.Test):
    """
    Test customized configuration can be made for the cluster.
    """
    def __init__(self, params, env):
        self.params = params
        self.client = ClustersConfClient(params)
        self.body = {}
        self.env = env
        self.original_body = {}
        self.configuration_before = None
        self.configuration_after = None
        self.cluster_id = None
        self.controller_ip = \
            self.params.get('ceph_management_url').split(':')[1].strip('/')
        self.controller_username = self.params.get('ceph_server_ssh_username')
        self.controller_password = self.params.get('ceph_server_ssh_password')

    def setup(self):
        """
        Set up before executing test
        """
        if 'cluster' in self.env:
            self.cluster_id = self.env['cluster']
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')
        else:
            raise exceptions.TestSetupFail(
                "Please set cluster_id in config first")

        zabbix_ip = remote.get_zabbix_server_ip(self.controller_ip,
                                                self.controller_username,
                                                self.controller_password)
        self.params['rest_arg_zabbix_server_ip'] = zabbix_ip
        self.params['rest_arg_ntp_server_ip'] = zabbix_ip

        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

        pre_body = {"zabbix_server_ip": zabbix_ip,
                    "zabbix_user": "Admin",
                    "zabbix_password": "zabbix",
                    "ntp_server_ip": "0.0.0.0",
                    "max_mdx_count": 4,
                    "max_mon_count": 4,
                    "daylight_begin": "23:00",
                    "daylight_end": "6:00",
                    "day_recover_bw": 1024,
                    "night_recover_bw": 1024}
        # get original configuration, used to restore env
        configuration = self._query_cluster_configuration()
        for key in pre_body.keys():
            self.original_body[key] = configuration.get(key)
        # pre-set
        self._set_cluster_configuration(pre_body)

    def _query_cluster_configuration(self):
        resp = self.client.query(self.cluster_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("Query clusters conf failed")
        LOG.info("Cluster configuration: %s" % resp.body)
        return resp.body

    def _set_cluster_configuration(self, body):
        resp = self.client.set(self.cluster_id, body)
        if not resp and utils.verify_response(body, resp):
            raise exceptions.TestFail("Set cluster conf failed: %s" % body)
        LOG.info("Set cluster configuration successfully: %s" % body)

    def test(self):
        """
        1. Get configuration of the cluster
        2. Modify: Maximum monitor count, ntp server ip, 
        zabbix server ip, acount
        3. Re-get configuration of cluster
        """
        # step 1:Get configuration of the cluster
        self.configuration_before = self._query_cluster_configuration()
        # step 2:Modify configuration
        self._set_cluster_configuration(self.body)
        # step 3:Re-get configuration of cluster
        self.configuration_after = self._query_cluster_configuration()
        # verify configuration take effect
        for key in self.body.keys():
            if 'zabbix' not in key:
                if self.configuration_after.get(key) \
                        == self.configuration_before.get(key):
                    raise exceptions.TestFail('Configuration does not take effect, '
                                              'expected: %s, actual: %s'
                                              % (self.body.get(key),
                                                 self.configuration_after.get(key)))

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        self._set_cluster_configuration(self.original_body)
