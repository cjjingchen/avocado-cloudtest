import logging
import traceback
import sys

from avocado.core import test
from avocado.core import exceptions
from cloudtest.openstack import compute
from cloudtest.openstack import network
from cloudtest.openstack import volume


RESOURCE_TYPES = ['Server', 'Keypair', 'Flavor']


class NFVTestBase(test.Test):
    def __init__(self, params, env):
        super(NFVTestBase, self).__init__(methodName=params.get('func_name',
                                                                'test'))
        self.params = params
        self.env = env
        self.network_utils = network.Network(self.params)
        self.compute_utils = compute.Compute(self.params)
        self.volume_utils = volume.Volume(self.params)
        self.cleanup_resources = []
        self.flavor = None
        self.vm_list = []
        self.log = logging.getLogger('avocado.test')
        self.release_on_failure = self.params.get('delete_resource_on_error',
                                                  'yes')
        self.controller_ip = self.params.get('controller_ip')
        self.controller_username = params.get('controller_username')
        self.controller_password = self.params.get('controller_password')
        self.controller_login_method = params.get("controller_ssh_login_method")
        self.image_username = self.params.get('image_ssh_username', 'root')
        self.image_password = self.params.get('image_ssh_password', 'root')
        self.pub_key = self.compute_utils.get_public_key()

    def setup(self):
        pass

    def register_cleanup(self, resource, res_type=None):
        try:
            if type(resource).__name__ in RESOURCE_TYPES:
                # insert vms to top of the cleanup list,
                # then they will be deleted firstly.
                if type(resource).__name__ == RESOURCE_TYPES[0]:
                    self.cleanup_resources.insert(0, resource)
                else:
                    self.cleanup_resources.append(resource)
            elif res_type:
                self.cleanup_resources.append({res_type: resource})
            else:
                raise ValueError
        except ValueError:
            self.log.error("Could not found the type %s in resource list" %
                           type(resource))

    def delete_resource(self, resource):
        if type(resource).__name__ in RESOURCE_TYPES:
            # when deleting vm, check it is exist or not
            if type(resource).__name__ == RESOURCE_TYPES[0]:
                if not self.is_vm_exist(resource.name):
                    self.log.debug("VM %s has been released" % resource.name)
                    return
            resource.delete()
            self.log.info("Successfully released resource: %s" % resource.name)
        elif isinstance(resource, dict):
            for k, v in resource.items():
                if k in 'fip':
                    self.network_utils.delete_floating_ip(v)
                elif k in 'port':
                    self.network_utils.delete_port(port_id=v)
                elif k in 'network':
                    self.network_utils.delete_network(name=v)
                elif k in 'volume':
                    self.volume_utils.delete_volume(v)
                else:
                    self.log.warn("Failed to cleanup; "
                                  "unknown resource type: %s" % resource)
                    continue
                self.log.info("Successfully released resource: %s" % resource)

    def is_vm_exist(self, name):
        try:
            self.compute_utils.find_vm_from_name(name)
        except exceptions.VMNotFound:
            return False
        return True

    def teardown(self):
        for _vm in self.vm_list:
            self.register_cleanup(_vm)

        if self.pub_key:
            self.register_cleanup(self.pub_key)

        if self.flavor:
            self.register_cleanup(self.flavor)

        ex_type, ex_val, ex_stack = sys.exc_info()
        if (self.release_on_failure in 'yes' and ex_type is exceptions.TestFail)\
                or (ex_type is not exceptions.TestFail):
            for res in self.cleanup_resources:
                self.delete_resource(res)
