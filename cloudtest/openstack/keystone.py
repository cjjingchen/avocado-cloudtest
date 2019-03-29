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


import os_client_config
from common import Common


class Keystone(Common):
    def __init__(self, params):
        super(Keystone, self).__init__(params)
        self.keystoneclient = os_client_config.make_client('identity', **self.nova_credential)

    def get_tenant(self, tenant_name):
        """
        Get tenant object
        :param tenant_name: the name of the tenant
        :returns: the tenant object
        """
        tenant = None
        tenants = self.keystoneclient.tenants.list()
        for _tenant in tenants:
            if _tenant.name == tenant_name:
                tenant = _tenant
        return tenant
