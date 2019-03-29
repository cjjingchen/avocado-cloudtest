# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Lenovo Inc. 2017
# Author: Yingfu Zhou <zhouyf6@lenovo.com>

from keystoneclient.v2_0 import client as keystone


class Common(object):
    def __init__(self, params):
        self.params = params
        self.cred = {}
        self.ksclient = None

    @property
    def aodh_credential(self):
        self._get_credential()
        self.cred['password'] = self.params.get('OS_PASSWORD')
        return self.cred

    @property
    def ceilometer_credential(self):
        self._get_credential()
        self.cred['version'] = self.params.get('CEILOMETER_API_VERSION', '2')
        self.cred['api_key'] = self.params.get('OS_PASSWORD')
        self.cred['password'] = self.params.get('OS_PASSWORD')
        return self.cred

    @property
    def nova_credential(self):
        self._get_credential()
        self.cred['version'] = self.params.get('NOVA_API_VERSION', '2')
        self.cred['api_key'] = self.params.get('OS_PASSWORD')
        self.cred['password'] = self.params.get('OS_PASSWORD')
        return self.cred

    @property
    def neutron_credential(self):
        self._get_credential()
        self.cred['password'] = self.params.get('OS_PASSWORD')
        return self.cred

    def _get_credential(self):
        self.cred['username'] = self.params.get('OS_USERNAME')
        self.cred['auth_url'] = self.params.get('OS_AUTH_URL')
        self.cred['tenant_name'] = self.params.get('OS_TENANT_NAME')
        return self.cred

    def get_keystone_client(self, auth_token=None, auth_url=None):
        if auth_token and auth_url:
            return keystone.Client(token=auth_token, auth_url=auth_url)
        return keystone.Client(**self._get_credential())


def get_host_list(self, zone=None):
    """
    Get host list according to specified zone.
    :param zone: zone name, could be 'nova' which means compute node and,
                 'internal' means controller node
    :return: list object
    """
    host_list = []
    cmd = "openstack host list --zone nova -c 'Host Name' -f json"
    output = process.run(cmd, shell=True).stdout
    for host in json.loads(output):
        host_list.append(host.get('Host Name'))
    return host_list
