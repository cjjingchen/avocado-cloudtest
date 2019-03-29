import time

from avocado.core import exceptions
from cloudtest.openstack import image
from cloudtest import utils_misc
from cloudtest.tests.nfv import test_utils
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


class VolumeTest(NFVTestBase):
    def __init__(self, params, env):
        super(VolumeTest, self).__init__(params, env)

        self.volume_id_list = []
        self.image_utils = image.Image(self.params)
        self.image_name = None

    def setup(self):
        pass

    def _volume_operation(self, operation_type, vol_id, instance):
        if operation_type in 'attach':
            # Attach volume
            self.compute_utils.attach_volume(instance.id, vol_id)
            status = self.volume_utils.get_volume_status(vol_id)
            self.log.info("The status of volume %s is %s" % (vol_id, status))
        elif operation_type in "detach":
            # Detach volume
            self.compute_utils.detach_volume(instance.id, vol_id)
            status = self.volume_utils.get_volume_status(vol_id)
            self.log.info("The status of volume %s is %s" % (vol_id, status))
        else:
            raise exceptions.TestFail("Volume operation %s is NOT supported." %
                                      type)

    def _create_volume(self, size, source=None, volume_type=None, image=None):
        vol_name = 'cloudtest_volume_' + utils_misc.generate_random_string(
            6)
        if volume_type is not None:
            vol_id = self.volume_utils.create_volume(vol_name, size,
                                                     image=image)
        else:
            vol_id = self.volume_utils.create_volume(vol_name, size,
                                                     volume_type=volume_type,
                                                     image=image)

        status = self.volume_utils.get_volume_status(vol_id)
        self.log.info("The status of volume %s(id = %s) is %s" %
                      (vol_name, vol_id, status))
        self.volume_id_list.append(vol_id)
        return vol_id

    def _create_vm(self, image_name):
        net = test_utils.get_test_network(self.params)
        _network_name = net['name']
        vm = self.compute_utils.create_vm(vm_name=None,
                                          image_name=image_name,
                                          network_name=_network_name,
                                          injected_key=self.pub_key,
                                          sec_group=None)
        self.vm_list.append(vm)
        if not self.compute_utils.wait_for_vm_active(vm):
            raise exceptions.TestFail("Failed to build VM: %s" % vm)
        time.sleep(60)
        return vm

    def test_create_empty_volume(self):
        size = self.params.get('disk', 1)
        vol_id_1 = self._create_volume(size)

    def test_create_image_volume(self):
        image_ref = self.params.get('image')
        if not image_ref:
            image_ref = self.params.get('image_name')

        image = self.image_utils.get_image(image_ref)
        size = image.get('size')/(1024*1024*1024)
        self.log.info("Image size is %s" % size)

        vol_id_1 = self._create_volume(size, image=image_ref)

    def test_create_instance_snapshot_volume(self):
        image_name = self.params.get('image_name')
        instance = self._create_vm(image_name)
        self.vm_list.append(instance)

        resource_info = instance.flavor
        resource_info = self.compute_utils.flavor_client.get(resource_info['id'])
        size = resource_info.disk
        self.log.info("The instance disk size is %s" % size)

        snapshot = self.compute_utils.create_snapshot(instance)
        if not snapshot:
            raise exceptions.TestFail("Failed to create snapshot.")
        self.image_name = snapshot.name

        vol_id_1 = self._create_volume(size, image=snapshot.name)

    def test_attach_volume(self):
        image_name = self.params.get('image_name')
        instance = self._create_vm(image_name)
        self.vm_list.append(instance)

        size = self.params.get('disk', 1)
        vol_id_1 = self._create_volume(size)

        self._volume_operation('attach', vol_id=vol_id_1, instance=instance)

        self._volume_operation('detach', vol_id=vol_id_1, instance=instance)

    def test_backup_volume(self):
        size = self.params.get('disk', 1)
        vol_id_1 = self._create_volume(size)

        bak_name = 'cloudtest_volume_backup_' + \
                   utils_misc.generate_random_string(6)
        volume_bak = self.volume_utils.create_volume_backup(vol_id_1, bak_name)

        if not self.volume_utils.wait_for_volume_status(vol_id_1, 'available'):
            raise exceptions.TestFail("Failed to backup volume.")

        if not self.volume_utils.delete_volume_backup(volume_bak.id):
            raise exceptions.TestFail("Failed to delete volume backup.")

    def test_create_shared_volume(self):
        volume_type = self.params.get('volume_type')

        vol_type = None
        try:
            vol_type = self.volume_utils.create_volume_type(volume_type)
        except Exception as err:
            if "sharable already exists" not in str(err):
                raise exceptions.TestFail("Failed to create volume type.")

        size = self.params.get('disk', 1)
        vol_id_1 = self._create_volume(size, volume_type=volume_type)

        if vol_type is not None:
            if not self.volume_utils.delete_volume_type(vol_type.id):
                raise exceptions.TestFail("Failed to delete volume type.")

    def teardown(self):
        for volume_id in self.volume_id_list:
            self.register_cleanup(resource=volume_id, res_type='volume')

        super(VolumeTest, self).teardown()

        if self.image_name:
            self.image_utils.delete_image(self.image_name)




