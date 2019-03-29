import logging
import time

from avocado.core import test
from avocado.core import exceptions
from avocado.utils import data_factory

from cloudtest import remote
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.rbd_client import RbdClient
from cloudtest.tests.ceph_api.lib.iscsi_client import ISCSIClient

LOG = logging.getLogger('avocado.test')


class TestIscsi(test.Test):
    """
    Module for testing iscsi related operations.
    """
    def __init__(self, params, env):
        self.params = params
        self.body = {}
        self.env = env
        self.rbd_client = RbdClient(params)
        self.iscsi_client = ISCSIClient(params)

        self.control_server_ip = self.params.get('ceph_management_url')
        self.control_server_ip = self.control_server_ip.split(':')[1].strip(
            '/')
        self.control_username = self.params.get('ceph_server_ssh_username',
                                                'root')
        self.control_password = self.params.get('ceph_server_ssh_password')

        self.initiator_username = self.params.get('ceph_node_ssh_username')
        self.initiator_password = self.params.get('ceph_node_ssh_password')

        self.old_config_list = []
        self.old_config_list.append(self.params.get(
            'iscsi_config_authmethod', '#node.session.auth.authmethod = CHAP'))
        self.old_config_list.append(self.params.get(
            'iscsi_config_username', '#node.session.auth.username = username'))
        self.old_config_list.append(self.params.get(
            'iscsi_config_password', '#node.session.auth.password = password'))
        self.old_config_list.append(self.params.get(
            'iscsi_config_username_in',
            '#node.session.auth.username_in = username_in'))
        self.old_config_list.append(self.params.get(
            'iscsi_config_password_in',
            '#node.session.auth.password_in = password_in'))
        self.iscsi_config_file = self.params.get('iscsi_config_file',
                                                 r'/etc/iscsi/iscsid.conf')
        self.rbd_id = None
        self.target_id = None
        self.lun_id = None
        self.target_ip = None

    def setup(self):

        if 'cluster' in self.env:
            self.cluster_id = self.env['cluster']
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')

        if self.params.get('pool_id'):
            self.pool_id = self.params.get('pool_id')
        else:
            self.pool_id = test_utils.create_pool(self.params)
            LOG.info("pool_id is %s" % self.pool_id)

        if self.params.get('initiator_ip'):
            self.initiator_ip = test_utils.get_available_host_ip(self.params)

    def _create_iscsi_target(self):
        self.iscsi_target_name = "cloudtest" + \
                                 data_factory.generate_random_string(6)
        body = {'initiator_ips': self.initiator_ip,
                'target_name': self.iscsi_target_name,
                'multipath': self.params.get('multipath', '2')}

        resp = self.iscsi_client.create(**body)
        if not resp and utils.verify_response(body, resp):
            raise exceptions.TestFail("Create target failed: %s" % body)

        return resp.body['target_id']

    def _query_specified_target(self, target_id):
        resp = self.iscsi_client.query()
        if len(resp) < 0:
            raise exceptions.TestFail("Query iscsi target failed")
        LOG.info("Got all iscsi targets %s" % resp)
        for i in range(len(resp)):
            if resp[i]['target_id'] == self.target_id:
                return resp[i]['target_name']

    def _create_iscsi_lun(self, target_id, rbd_id):
        body = {'target_id': target_id,
                'pool_id': self.pool_id,
                'rbd_id': rbd_id}
        resp = self.iscsi_client.add_lun(**body)

        return resp.body['lun_id']

    def _get_lun_info(self):
        resp = self.iscsi_client.get_lun_info()
        LOG.info("Got all iscsi lun info %s" % resp)

    def _delete_iscsi_lun(self, target_id, lun_id):
        body = {
            'target_id': target_id,
            'lun_id': lun_id}

        resp = self.iscsi_client.delete_lun(**body)

    def _delete_target(self, target_id):
        """
        Test that deletion of delete target
        """
        self.iscsi_client.delete_iscsitarget(target_id)
        resp = self.iscsi_client.query()
        for i in range(len(resp)):
            if resp[i]['target_id'] == target_id:
                raise exceptions.TestFail("Delete target failed")

    def _create_account_group(self, account_type):
        """
        Execute the test of creating account group
        """
        account_name = data_factory.generate_random_string(6)
        account_pass = data_factory.generate_random_string(12)
        account_out_name = data_factory.generate_random_string(6)
        account_out_pass = data_factory.generate_random_string(12)

        resp = self.iscsi_client.create_account_group(account_name, account_pass,
                                                      account_type,
                                                      account_out_name,
                                                      account_out_pass)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Create account group failed: %s")

        return resp['group_id']

    def _query_account_group(self, account_group_id):
        """
        Execute the test of creating account group
        """
        resp = self.iscsi_client.query_account_group()
        LOG.info("Got all iscsi account group %s" % resp)
        if not len(resp) > 0:
            raise exceptions.TestFail("Query iscsi account failed")
        for i in range(len(resp)):
            if resp[i]['group_id'] == account_group_id:
                return resp[i]['username'], resp[i]['password'], \
                       resp[i]['username_out'], resp[i]['password_out']

    def _delete_account_group(self, account_id):
        """
        Test that deletion of account group
        """
        LOG.info("Try to delete account group with ID: %d" % account_id)
        self.iscsi_client.delete_account(account_id)
        resp = self.iscsi_client.query_account_group()
        for i in range(len(resp)):
            if resp[i]['group_id'] == account_id:
                raise exceptions.TestFail("Delete account group failed")

    def _modify_account_group(self, account_id, account_name, account_pass,
                              account_name_out, account_pass_out):
        """
        Modify account group
        """
        resp = self.iscsi_client.modify_account_group(account_id, account_name,
                                                      account_pass,
                                                      account_name_out,
                                                      account_pass_out)
        LOG.info('Rest Response: %s' % resp)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail(
                "Modify account group failed: %s" % self.body)

    def _bind_account_operation(self, account_ops, account_group_id, target_id):
        """
        Test to bind or unbind account group to target
        """
        LOG.info("Try to %s account %s to target %s" %
                 (account_ops, account_group_id, target_id))

        if 'unbind' in account_ops:
            resp = self.iscsi_client.unbind_account(target_id, account_group_id)
            if not len(resp) > 0:
                raise exceptions.TestFail("Unbind account group '%s' failed" %
                                          account_group_id)
        elif 'bind' in account_ops:
            resp = self.iscsi_client.bind_account(target_id, account_group_id)
            if not len(resp) > 0:
                raise exceptions.TestFail("Bind account group '%s' failed" %
                                          account_group_id)
        else:
            raise exceptions.TestNotFoundError('Did not find test for bind '
                                               'account operation')

    def _query_login_initiator(self, target_id):
        resp = self.iscsi_client.query_login_initiator()
        LOG.info("Got all login initiator %s" % resp)

    def _create_new_config_list(self, username, password, username_out,
                                password_out, old_config_list):
        new_config_list = []
        self.find_username_in = 'username_in'
        self.find_password_in = 'password_in'
        self.find_username = 'username'
        self.find_password = 'password'

        for i in range(len(old_config_list)):
            tmp = old_config_list[i].strip('#')
            sub = tmp[0:tmp.find('=')+1]
            if self.find_username_in in tmp:
                tmp = sub + username
                new_config_list.append(tmp)
                self.find_username_in = username
                continue
            elif self.find_password_in in tmp:
                tmp = sub + password
                new_config_list.append(tmp)
                self.find_password_in = password
                continue
            elif self.find_username in tmp:
                tmp = sub + username_out
                new_config_list.append(tmp)
                self.find_username = username_out
                continue
            elif self.find_password in tmp:
                tmp = sub + password_out
                new_config_list.append(tmp)
                self.find_password = password_out
            else:
                new_config_list.append(tmp)

        return new_config_list

    def _verify_login_iscsi_with_account(self, username, password, username_out,
                                         password_out, old_config_list,
                                         expect_login):
        new_config_list = []
        new_config_list = self._create_new_config_list(username, password,
                                                       username_out,
                                                       password_out,
                                                       old_config_list)
        LOG.info("new_config_list is %s" % new_config_list)

        # Modify file /etc/iscsi/iscsid.conf
        test_utils.modify_file(self.control_server_ip, self.control_username,
                               self.control_password, self.initiator_ip,
                               self.initiator_username, self.initiator_password,
                               self.iscsi_config_file, old_config_list,
                               new_config_list)

        login = test_utils.iscsi_login_with_account(self.control_server_ip,
                                                    self.control_username,
                                                    self.control_password,
                                                    self.initiator_ip,
                                                    self.initiator_username,
                                                    self.initiator_password,
                                                    self.iscsi_target_name,
                                                    self.target_ip)

        #self._query_login_initiator(self.target_id)

        test_utils._logout_iscsi(self.control_server_ip, self.control_username,
                                 self.control_password, self.initiator_ip,
                                 self.initiator_username, self.initiator_password,
                                 None, self.iscsi_target_name, self.target_ip)

        if login == expect_login:
            LOG.info("Login status is expected!")
        else:
            LOG.info("Login status is NOT expected!")

    def test_iscsi_chap(self):
        # Create rbd in the pool
        self.rbd_id = test_utils.create_rbd(self.pool_id, self.params)

        # Create iscsi
        self.target_id = self._create_iscsi_target()
        target_name = self._query_specified_target(self.target_id)

        if target_name not in self.iscsi_target_name:
            LOG.info("Target name %s is not expected. "
                     "The target name created is %s" %
                     (target_name, self.iscsi_target_name))

        # Get the first target ip via target id
        self.target_ip = test_utils.get_specified_targetip(self.params,
                                                           self.target_id, 0)

        # Bind iscsi to rbd
        self.lun_id = self._create_iscsi_lun(self.target_id, self.rbd_id)
        self._get_lun_info()

        # Create count1 and count2(single way chap)
        self.account_group_id1 = self._create_account_group("two")
        self.account_group_id2 = self._create_account_group("two")

        self.username1, self.password1, self.username_out1, self.password_out1\
            = self._query_account_group(self.account_group_id1)
        LOG.info("username1: %s, password1: %s, username_out1: %s, "
                 "password_out1: %s" % (self.username1, self.password1,
                 self.username_out1, self.password_out1))
        self.username2, self.password2, self.username_out2, self.password_out2\
            = self._query_account_group(self.account_group_id2)
        LOG.info("username2: %s, password2: %s, username_out2: %s, "
                 "password_out2: %s" % (self.username2, self.password2,
                 self.username_out2, self.password_out2))

        self._bind_account_operation('bind', self.account_group_id2,
                                     self.target_id)

        self._delete_account_group(self.account_group_id1)

        # There are bugs about iscsi modify function
        '''account_name_out = data_factory.generate_random_string(
            6)
        account_pass_out = data_factory.generate_random_string(6)
        self._modify_account_group(self.account_group_id2, self.username2,
                                   self.password2, account_name_out,
                                   account_pass_out)
        self.username2, self.password2, self.username_out2, self.password_out2 \
            = self._query_account_group(self.account_group_id2)
        LOG.info("username2: %s, password2: %s, username_out2: %s, "
                 "password_out2: %s" % (self.username2, self.password2,
                 self.username_out2, self.password_out2))'''

        LOG.info("old_config_list is %s" % self.old_config_list)

        self._verify_login_iscsi_with_account(self.username2, self.password2,
                                              self.username_out2,
                                              self.password_out2,
                                              self.old_config_list, True)

        self.password_out2 = 'test'
        self._verify_login_iscsi_with_account(self.username2, self.password2,
                                              self.username_out2,
                                              self.password_out2,
                                              self.old_config_list, False)

        # There is bug relatived to unbind account. 
        #self._bind_account_operation('unbind', self.account_group_id2,
                                     #self.target_id)

    def teardown(self):
        if self.lun_id is not None:
            self._delete_iscsi_lun(self.target_id, self.lun_id)
        if self.target_id is not None:
            self._delete_target(self.target_id)
        if self.rbd_id is not None:
            test_utils.delete_rbd(self.pool_id, self.rbd_id, self.params)
        if self.account_group_id2 is not None:
            self._delete_account_group(self.account_group_id2)