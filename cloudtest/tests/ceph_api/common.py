# Copyright: Lenovo Inc. 2016~2017
# Author: Yingfu Zhou <zhouyf6@lenovo.com>

"""
Base class for ceph management rest clients.
"""

import os
import json
import logging
import datetime
import thread

from avocado.utils import genio
from cloudtest.tests.ceph_api.lib import rest_client


ISO8601_FLOAT_SECONDS = '%Y-%m-%dT%H:%M:%S.%fZ'
ISO8601_INT_SECONDS = '%Y-%m-%dT%H:%M:%SZ'
EXPIRY_DATE_FORMATS = (ISO8601_FLOAT_SECONDS, ISO8601_INT_SECONDS)
LOCK = thread.allocate_lock()


class CephMgmtClient(rest_client.RestClient):
    """
    Base class for all clients.
    """

    token_expiry_threshold = datetime.timedelta(seconds=3600)

    def __init__(self, params):
        self.params = params
        self.base_url = params.get('ceph_management_url')
        self.cached_token_path = '/tmp/sds_token'
        super(CephMgmtClient, self).__init__(self.base_url)
        self.logger = logging.getLogger('avocado.test')

    def get_cached_token(self):
        if os.path.exists(self.cached_token_path):
            with open(self.cached_token_path, 'r') as cache_file:
                return json.load(cache_file)
        return ""

    def set_cached_token(self, auth_data):
        with open(self.cached_token_path, 'w') as cache_file:
            self.logger.info('Saving auth data to cache...')
            json.dump(auth_data, cache_file)

    def is_token_expired(self, auth_data):
        LOCK.acquire()
        expiry = self._parse_expiry_time(auth_data['access']['token']['expires'])
        r = expiry <= datetime.datetime.utcnow()
        if r:
            self.logger.info('Token expired, will renew token...')
        LOCK.release()
        return r

    def _parse_expiry_time(self, expiry_string):
        expiry = None
        for date_format in EXPIRY_DATE_FORMATS:
            try:
                expiry = datetime.datetime.strptime(
                    expiry_string, date_format)
            except ValueError:
                pass
        if expiry is None:
            raise ValueError(
                "time data '{data}' does not match any of the"
                "expected formats: {formats}".format(
                    data=expiry_string, formats=self.EXPIRY_DATE_FORMATS))
        return expiry

    def get_token(self):
        if self.params.get('sds_version') in '1.2':
            cached_token = self.get_cached_token()
            if not cached_token or self.is_token_expired(cached_token):
                req = {'auth': {'tenantName': self.params.get('OS_TENANT_NAME'),
                                'passwordCredentials': {
                                    'username': self.params.get('OS_USERNAME'),
                                    'password': self.params.get('OS_PASSWORD')
                                 }
                                }
                      }
                self.logger.info("SDS version is 1.2, start authenticating...")
                auth = rest_client.RestClient(self.params.get('OS_AUTH_URL'))
                resp, body = auth.post('/tokens', body=json.dumps(req))
                body = json.loads(body)
                token = body['access']['token']['id']
                self.set_cached_token(body)
                return {'X-Auth-Token': token, 'LOG_USER': 'admin'}
            return {'X-Auth-Token': cached_token['access']['token']['id'],
                    'LOG_USER': 'admin'}
        else:
            self.logger.info('SDS version < 1.2, no need to authenticate')
            return {'LOG_USER': 'admin'}
