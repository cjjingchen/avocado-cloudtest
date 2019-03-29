import json
import copy

from avocado.core import exceptions
from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.api_schema.request import remote_backup
from cloudtest.tests.ceph_api.api_schema.response import remote_backup as schema
from cloudtest import utils_misc
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody, \
    ResponseBodyList


class RemoteBackupClient(CephMgmtClient):
    """
    The REST client of remote backup.
    """

    def __init__(self, params):
        self.params = params
        super(RemoteBackupClient, self).__init__(params)
        self.path = '%s/clusters' % (params.get('version', 'v1'))
        self.cluster_id = self.params.get('cluster_id')
        self.backup_site_url = '/%s/backup/sites/' % params.get('version', 'v1')
        self.url = '/%s' % (params.get('version', 'v1'))

    def rbd_remote_backup(self, **kwargs):
        body = copy.deepcopy(remote_backup.RBD_REMOTE_BACKUP)
        body.update(kwargs)
        url = self.url + "/clusters/%s/backup/rbtasks" % self.cluster_id
        resp, body = self.post(url, body=json.dumps(body))
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def rbd_restore(self, **kwargs):
        body = copy.deepcopy(remote_backup.RBD_RESTORE)
        body.update(kwargs)
        url = self.url + "/backup/restore"
        resp, body = self.post(url, body=json.dumps(body))
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def get_backup_list(self, pool_id, rbd_id):
        url = self.url + "/clusters/%s/pools/%s/rbds/%s/backup/snaps" \
                         % (self.cluster_id, pool_id, rbd_id)
        resp, body = self.get(url)
        body = json.loads(body)
        return ResponseBodyList(resp, body)

    def add_rbtask(self, **kwargs):
        body = copy.deepcopy(remote_backup.ADD_RBTASK)
        body.update(kwargs)
        url = self.url + "/clusters/%s/backup/rbtasks" % self.cluster_id
        # this api return null
        resp, body = self.post(url, body=json.dumps(body))
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def get_rbtask_list(self):
        url = self.url + "/clusters/%s/backup/rbtasks" % self.cluster_id
        resp, body = self.get(url)
        body = json.loads(body)
        # self.validate_response()
        return ResponseBody(resp, body)

    def modify_rbtask(self, task_id, **kwargs):
        body = copy.deepcopy(remote_backup.MODIFY_RBTASK)
        body.update(kwargs)
        url = self.url + "/clusters/%s/backup/rbtasks/%s" % (self.cluster_id,
                                                             task_id)
        resp, body = self.put(url, body=json.dumps(body))
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def delete_rbtask(self, task_id):
        url = self.url + "/clusters/%s/backup/rbtasks/%s" % (self.cluster_id,
                                                             str(task_id))
        resp, body = self.delete(url)
        if body:
            return ResponseBody(resp, json.loads(body))
        return ResponseBody(resp)

    def get_remotebackup_log(self):
        url = self.url + "/clusters/%s/backup/logs" % self.cluster_id
        resp, body = self.get(url)
        body = json.loads(body)
        # self.validate_response()
        return ResponseBody(resp, body)

    def add_backup_site(self, kwargs):
        url = self.backup_site_url
        site_type = kwargs['site_type']
        if 'site_name' not in kwargs.keys() or not kwargs['site_name']:
            site_name = 'backup_site_%s' % utils_misc.generate_random_string(6)
            kwargs['site_name'] = site_name

        if site_type in 'ceph':
            body = remote_backup.CEPH_SITE.copy()
        elif site_type in 'S3':
            body = remote_backup.S3_SITE.copy()
        for key, value in body.items():
            body[key] = kwargs[key]

        resp, body = self.post(url=url, body=json.dumps(body))
        body = json.loads(body)
        return ResponseBody(resp, body)

    def get_backup_site_list(self):

        url = self.backup_site_url
        resp, body = self.get(url=url)
        body = json.loads(body)
        self.validate_response(schema.BACKUP_SITE_LIST, resp, body)
        return ResponseBodyList(resp, body)

    def update_backup_site(self, site_id=None, **kwargs):
        url = self.backup_site_url + "/%s" % site_id
        site_type = kwargs['site_type']
        if 'site_name' not in kwargs.keys() or not kwargs['site_name']:
            site_name = 'backup_site_%s' % utils_misc.generate_random_string(6)
            kwargs['site_name'] = site_name

        if site_type in 'ceph':
            body = remote_backup.CEPH_SITE.copy()
        elif site_type in 'S3':
            # body = remote_backup.S3_SITE.copy()
            raise exceptions.TestFail("Update function is not ready for S3.")
        for key, value in body.items():
            body[key] = kwargs[key]

        resp, body = self.put(url=url, body=json.dumps(body))
        body = json.loads(body)
        return ResponseBody(resp, body)

    def del_backup_site(self, site_id=None):

        url = self.backup_site_url + "/%s" % site_id
        resp, body = self.delete(url=url)
        body = json.loads(body)
        return ResponseBody(resp, body)

    def configure_rbpolicy(self, **kwargs):
        """
        Method to create remote backup policy 
        """
        body = copy.deepcopy(remote_backup.CONF_RBPOLICY)
        body.update(kwargs)
        url = self.url + "/rbpolicy"
        resp, body = self.post(url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.CONF_RBPOLICY, resp, body)
        return ResponseBody(resp, body)

    def delete_rbpolicy(self):
        """
        Method to delete remote backup policy 
        """
        url = self.url + "/rbpolicy"
        resp, body = self.delete(url=url)
        body = json.loads(body)
        self.validate_response(schema.DELETE_RBPOLICY, resp, body)
        return ResponseBody(resp, body)

    def query_rbpolicy(self):
        """
        Method to query remote backup policy 
        """
        url = self.url + "/rbpolicy"
        resp, body = self.get(url=url)
        body = json.loads(body)
        self.validate_response(schema.QUERY_RBPOLICY, resp, body)
        return ResponseBody(resp, body)

    def start_rbtask(self, **kwargs):
        """
        Method to start rbd remote backup
        """
        body = copy.deepcopy(remote_backup.START_RBTASK)
        body.update(kwargs)
        url = self.url + "/rbtask"
        resp, body = self.post(url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.START_RBTASK, resp, body)
        return ResponseBody(resp, body)

    def list_rbtasks(self, extra_url=None):
        """
        Method to query remote backup tasks
        """
        url = self.url + extra_url
        resp, body = self.get(url=url)
        body = json.loads(body)
        self.validate_response(schema.RBTASK_LIST, resp, body)
        return ResponseBodyList(resp, body)

    def query_restore(self, rbd_id):
        """
        Method to query remote restore time
        """
        url = self.url + "/rbds/%s/restore" % rbd_id
        resp, body = self.get(url=url)
        body = json.loads(body)
        self.validate_response(schema.RESTORE_LIST, resp, body)
        return ResponseBodyList(resp, body)

    def start_restore(self, rbd_id, **kwargs):
        """
        Method to start remote restore
        """
        body = copy.deepcopy(remote_backup.START_RESTORE)
        body.update(kwargs)
        url = self.url + "/rbds/%s/restore" % rbd_id
        resp, body = self.post(url=url, body=json.dumps(body))
        body = json.loads(body)
        self.validate_response(schema.START_RESTORE, resp, body)
        return ResponseBody(resp, body)
