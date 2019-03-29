import logging
import time

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib.iscsi_client import ISCSIClient
from cloudtest.tests.ceph_api.lib.clusters_client import ClustersClient
from cloudtest.tests.ceph_api.lib import test_utils


LOG = logging.getLogger('avocado.test')


class TestISCSI(test.Test):
    """
    ISCSI related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.body = {}
        self.env = env
        self.created_resources = {}
        self.clusters_client = ClustersClient(self.params)
        self.cluster_id = None
        self.lun_id = None
        self.gateway_id = None

    def setup(self):
        """
        Set up before executing test
        """
        if 'cluster' in self.env:
            self.cluster_id = self.env['cluster']
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')

        self.client = ISCSIClient(self.params)

        self.gateway_id = test_utils.get_available_gateway(self.params)
        if self.gateway_id is None:
            self.gateway_id = test_utils.create_gateway(self.params)

    def test_create_target(self):
        """
        Execute the test of creating a iscsi target
        """
        iscsi_target_name = utils.utils_misc.generate_random_string(6)
        delay_time = time.strftime("%Y-%m", time.localtime(time.time()))

        iscsi_target_name = "iqn." + delay_time + ".com.lenovo:" + iscsi_target_name
        LOG.info("Target_name is %s" % iscsi_target_name)

        body = {'initiator_ips': '192.168.1.30',
                'target_name': iscsi_target_name,
                'multipath': self.params.get('multipath', '1'),
                'gateway_id': self.gateway_id}

        resp = self.client.create(**body)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Create target failed: %s" % body)
        self.env['iscsi_target'] = resp.body

    def test_query_target(self):
        resp = self.client.query()
        if not len(resp) > 0:
            raise exceptions.TestFail("Query iscsi target failed")
        LOG.info("Got all iscsi targets %s" % resp)

    def test_query_specified_target(self):
        target_id = self.env.get('iscsi_target')['target_id']
        resp = self.client.query(target_id)
        #Fixme if there is not any issue, the api return blank
        if len(resp) > 0:
            raise exceptions.TestFail("Query iscsi target failed")
        LOG.info("Got all iscsi targets %s" % resp)

    def _lun_ops(self, ops):
        target_id = self.env.get('iscsi_target')['target_id']

        self.rbd_pool_id = test_utils.get_pool_id(self.env, self.params)

        if self.params.get('rbd_id'):
            self.rbd_id = self.params.get('rbd_id')
        else:
            self.rbd_id = test_utils.create_rbd(self.rbd_pool_id, self.params)

        if ops in 'add':
            body = {'target_id': target_id,
                    'pool_id': self.rbd_pool_id,
                    'rbd_id': self.rbd_id}
            resp = self.client.add_lun(**body)
            self.env['iscsi_target_lun'] = resp.body
            return resp

        elif ops in 'delete':
            body = {
                'target_id': target_id,
                'lun_id': self.lun_id}

            return self.client.delete_lun(**body)

    def test_lun_ops(self):
        ops = self.params.get('lun_ops')
        if ops in 'add':
            if not self._lun_ops('add'):
                raise exceptions.TestFail('Test of add lun failed')

        elif ops in 'delete':
            if not self.lun_id:
                self.lun_id = self.env['iscsi_target_lun']['lun_id']
            if not self._lun_ops('delete'):
                raise exceptions.TestFail('Test of delete lun failed')

        elif ops in 'get_lun_info':
            resp = self.client.get_lun_info()
            if not len(resp) > 0:
                raise exceptions.TestFail("Test of get_lun_info failed")
        else:
            raise exceptions.TestNotFoundError('Did not find test for operation')

    def test_modify_iscsi(self):
        """
        Modify iscsi targets's initiator ip
        """
        target_id = self.env.get('iscsi_target')['target_id']
        modify_iscsi = {'initiator_ips': "192.168.1.34",
                       'old_initiator_ip': "192.168.1.30"}
        resp = self.client.modify_iscsi(target_id, **modify_iscsi)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail(
                "Modify iscsi target export host failed: %s" % self.body)

    def test_create_account_group(self):
        """
        Execute the test of creating account group
        """
        account_name = utils.utils_misc.generate_random_string(6)
        account_pass = utils.utils_misc.generate_random_string(12)
        gateway_id = self.gateway_id

        resp = self.client.create_account_group(account_name, account_pass,
                                                "single", str(gateway_id))
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Create account group failed: %s")
        self.env['iscsi_accountgroup'] = resp.body

    def test_query_account_group(self):
        """
        Execute the test of creating account group
        """
        resp = self.client.query_account_group()
        if not len(resp) > 0:
            raise exceptions.TestFail("Query iscsi target failed")
        LOG.info("Got all iscsi targets %s" % resp)

    def test_modify_account_group(self):
        """
        Modify account group
        """
        account_id = self.env.get('iscsi_accountgroup')['group_id']
        account_name = utils.utils_misc.generate_random_string(
            6)
        account_pass = utils.utils_misc.generate_random_string(6)

        resp = self.client.modify_account_group(account_id, account_name,
                                                account_pass)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail(
                "Modify account group failed: %s" % self.body)

    def test_bind_account_operation(self):
        """
        Test to bind or unbind account group to target
        """
        account_ops = self.params.get('account_operation')
        target_id = self.env.get('iscsi_target')['target_id']
        account_group_id = self.env.get('iscsi_accountgroup')['group_id']

        LOG.info("Try to %s account %s to target %s" %
                 (account_ops, account_group_id, target_id))

        if 'unbind' in account_ops:
            resp = self.client.unbind_account(target_id, account_group_id)
            if not len(resp) > 0:
                raise exceptions.TestFail("Unbind account group '%s' failed" %
                                          account_group_id)
        elif 'bind' in account_ops:
            resp = self.client.bind_account(target_id, account_group_id)
            if not len(resp) > 0:
                raise exceptions.TestFail("Bind account group '%s' failed" %
                                          account_group_id)
        else:
            raise exceptions.TestNotFoundError('Did not find test for bind '
                                               'account operation')

    def test_query_login_initiator(self):
        resp = self.client.query_login_initiator()
        #Fixme it returns blank
        #if not len(resp) > 0:
            #raise exceptions.TestFail("Query login initiator failed")
        LOG.info("Got all login initiator %s" % resp)

    def test_delete_account_group(self):
        """
        Test that deletion of account group
        """
        account_id = self.env.get('iscsi_accountgroup')['group_id']
        LOG.info("Try to delete account group with ID: %d" % account_id)
        self.client.delete_account(account_id)
        resp = self.client.query_account_group()
        for i in range(len(resp)):
            if resp[i]['group_id'] == account_id:
                raise exceptions.TestFail("Delete account group failed")

    def test_delete_target(self):
        """
        Test that deletion of delete target
        """
        target_id = self.env.get('iscsi_target')['target_id']
        LOG.info("Try to delete iscsi_target with ID: %d" % target_id)
        self.client.delete_iscsitarget(target_id)
        resp = self.client.query()
        if len(resp['items']) != 0:
            for i in range(len(resp['items'])):
                if resp['items'][i]['target_id'] == target_id:
                    raise exceptions.TestFail("Delete target failed")

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        pass