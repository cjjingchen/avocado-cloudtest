import logging
import random
import time

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib.warnings_client import WarningsClient
from cloudtest.tests.ceph_api.lib.servers_client import ServersClient
from cloudtest.tests.ceph_api.lib.monitors_client import MonitorsClient
from cloudtest.tests.ceph_api.lib.osd_client import OsdClient
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest import utils_misc

LOG = logging.getLogger('avocado.test')


class TestWarnings(test.Test):
    """
    Snapshots related tests.
    """

    def __init__(self, params, env):
        self.params = params
        self.client = WarningsClient(params)
        self.server_client = ServersClient(params)
        self.monitor_client = MonitorsClient(params)
        self.osd_client = OsdClient(params)
        self.body = {}
        self.env = env

    def setup(self):
        """
        Set up before executing test
        """
        for k, v in self.params.items():
            if 'rest_arg_warnings_' in k:
                new_key = k.split('rest_arg_warnings_')[1]
                if v.isdigit():
                    v = int(v)
                self.body[new_key] = v

    def test_query_waring_type(self):
        resp = self.client.query_waring_type()
        if not len(resp) > 0:
            raise exceptions.TestFail(
                "No warning type found, query warning type failed")

    def test_modify_waring_type(self):
        alerttype_id = self.params.get('alerttype_id')
        self.client.modify_waring_type(alerttype_id, **self.body)

    def test_create_warning(self):
        entity_type = self.params.get('entity_type')
        description = 'warning' + utils_misc.generate_random_string(6)
        self.body['description'] = description
        if entity_type in 'cluster':
            self.body['entity_id'] = self.__get_cluster_id()
        elif entity_type in 'server':
            self.body['entity_id'] = self.__get_server_id()
        elif entity_type in 'monitor':
            self.body['entity_id'] = self.__get_monitor_id()
        elif entity_type in 'osd':
            self.body['entity_id'] = self.__get_osd_id()
        elif entity_type in 'disk':
            self.body['entity_id'] = self.__get_disk_id()
        elif entity_type in 'rbd':
            self.body['entity_id'] = self.__get_rbd_id()
        elif entity_type in 'pool':
            self.body['entity_id'] = self.__get_pool_id()
        elif entity_type in 'network_interface':
            self.body['entity_id'] = self.__get_network_interface_id()

        if entity_type in 'rbd':
            timeout = int(self.params.get('timeout_for_create', '650'))
            timeout = timeout + time.time()
            resp = None
            while timeout > time.time():
                try:
                    time.sleep(10)
                    resp = self.client.create_warning(**self.body)
                    if resp.body.get('alert_id'):
                        self.env['warning_temp'] = resp.body
                        break
                except exceptions.BadRequest, e:
                    pass
        else:
            resp = self.client.create_warning(**self.body)
        if not resp or not resp.body.get('alert_id'):
            raise exceptions.TestFail("Create warning failed")
        self.env['warning_temp'] = resp.body

    def __get_pool_id(self):
        pool_id = test_utils.get_pool_id(self.env, self.params)
        return pool_id

    def __get_server_id(self):
        if self.env.get('server'):
            server_id = self.env.get('server')
        else:
            server_id = self.params.get('server_id')
        return server_id

    def __get_monitor_id(self):
        cluster_id = self.__get_cluster_id()
        body = self.monitor_client.query(cluster_id)
        length = len(body)
        for i in range(0, length):
            if 'follower' in body[i].get('role'):
                monitor_id = body[i].get('id')
                break
        return monitor_id

    def __get_cluster_id(self):
        if self.env.get('cluster'):
            cluster_id = self.env.get('cluster')
        else:
            cluster_id = self.params.get('cluster_id')
        return cluster_id

    def __get_rbd_id(self):
        pool_id = self.__get_pool_id()
        rbd_id = test_utils.create_rbd(pool_id, self.params)
        return rbd_id

    def __get_osd_id(self):
        sever_id = self.__get_server_id()
        if self.env.get('osd'):
            osd_id = self.env.get('osd')
        else:
            osd_id = test_utils.get_available_osd(sever_id, self.params)
        return osd_id

    def __get_disk_id(self):
        osd_id = self.__get_osd_id()
        server_id = self.__get_server_id()
        body = self.osd_client.get_osd_disk(server_id, osd_id)
        length = len(body)
        LOG.info(body)
        index = random.randint(0, length-1)
        disk_id = body[index].get('diskId')
        return disk_id

    def __get_network_interface_id(self):
        server_id = self.__get_server_id()
        body = self.server_client.get_server_nics(server_id)
        length = len(body)
        index = random.randint(0, length-1)
        interface_id = body[index].get('id')
        return interface_id

    def test_query_warning(self):
        query_type = self.params.get('query_type')
        if query_type in 'all':
            resp = self.client.query_warning()
        elif query_type in 'entity_id':
            if self.env.get('warning_temp'):
                LOG.info(self.env.get('warning_temp'))
                entity_type = self.env['warning_temp'].get('entity_type')
                entity_id = self.env['warning_temp'].get('entity_id')
            else:
                entity_type = self.params.get('entity_type')
                entity_id = self.params.get('entity_id')
            self.body['entity_id'] = entity_id
            self.body['entity_type'] = entity_type
            resp = self.client.query_warning(**self.body)
        elif query_type in 'alert_status':
                self.body['status'] = self.params.get('status')
                resp = self.client.query_warning(**self.body)
        elif query_type in 'alert_value':
                self.body['value'] = self.params.get('value')
                resp = self.client.query_warning(**self.body)
        elif query_type in 'trap_enabled':
                self.body['trap_enabled'] = self.params.get('trap_enabled')
                resp = self.client.query_warning(**self.body)
        else:
            resp = self.client.query_warning()

        body = resp.get('items')
        if not len(body) > 0:
            raise exceptions.TestFail(
                "No warning found, query warning failed")

    def test_query_warning_log(self):
        resp = self.client.query_waring_log()
        body = resp.get('items')
        LOG.info('%s' % body)
        # warning log cannot be produced at times because of rbd capacity.
        # if not len(body) > 0:
        #     raise exceptions.TestFail(
        #         "No warning found, query warning log failed")

    def test_modify_warning(self):
        if self.env.get('warning_temp'):
            alert_id = self.env['warning_temp'].get('alert_id')
        elif self.params.get('alert_id'):
            alert_id = self.params.get('alert_id')
        else:
            raise exceptions.TestFail(
                "Please set alert_id in config")
        resp = self.client.modify_warning(alert_id, **self.body)
        if not len(resp.body) > 0:
            raise exceptions.TestFail(
                "No warning found, modify warning failed")

    def test_delete_warning(self):
        if self.env.get('warning_temp'):
            alert_id = self.env['warning_temp'].get('alert_id')
        elif self.params.get('alert_id'):
            alert_id = self.params.get('alert_id')
        else:
            raise exceptions.TestFail(
                "Please set alert_id in config")
        self.client.delete_warning(alert_id)

    def test_create_email(self):
        resp = self.client.create_email(**self.body)
        self.env['email_temp'] = resp.body.get('id')

    def test_query_email(self):
        resp = self.client.query_email()
        if not len(resp) > 0:
            raise exceptions.TestFail(
                "No email found, query email failed")

    def test_modify_email(self):
        if self.env.get('email_temp'):
            email_id = self.env['email_temp']
        elif self.params.get('email_id'):
            email_id = self.params.get('email_id')
        else:
            raise exceptions.TestFail(
                "Please set email_id in config")
        self.client.modify_email(email_id, **self.body)

    def test_delete_email(self):
        if self.env.get('email_temp'):
            email_id = self.env['email_temp']
        elif self.params.get('email_id'):
            email_id = self.params.get('email_id')
        else:
            raise exceptions.TestFail(
                "Please set email_id in config")
        resp = self.client.delete_email(email_id)
        body = resp.body
        if body.get('success') is None:
            raise exceptions.TestFail("Delete email failed !")

    def test_query_settings(self):
        self.client.query_notification_settings()

    def test_modify_settings(self):
        self.client.modify_notification_settings(**self.body)

    def test_set_SNMP(self):
        self.body['id'] = self.params.get('id')
        self.body['community'] = self.params.get('community')
        self.body['version'] = self.params.get('version')
        if self.params.get('traphostlist'):
            self.body['traphostlist'] = self.params.get('traphostlist').split('-')
        if self.params.get('gethostlist'):
            self.body['gethostlist'] = self.params.get('gethostlist').split('-')
        body_temp = {"entity": [self.body]}
        resp = self.client.set_SNMP(**body_temp)
        body = resp.body
        LOG.info(body)
        if body.get('result') != 0:
            raise exceptions.TestFail(
                "set SNMP failed!")
        LOG.info('set SNMP success!')

    def test_query_SNMP(self):
        resp = self.client.query_SNMP()
        if not len(resp) > 0:
            raise exceptions.TestFail(
                "No snmp config found, query snmp failed")

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        pass