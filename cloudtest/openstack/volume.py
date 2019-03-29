import logging
import time

import os_client_config
from common import Common

from avocado.core import exceptions


LOG = logging.getLogger('avocado.test')


class Volume(Common):
    def __init__(self, params):
        super(Volume, self).__init__(params)
        self.cinderclient = os_client_config.make_client(
            'volume', **self.nova_credential)

        self.volume_back = self.cinderclient.backups
        self.volume_type = self.cinderclient.volume_types

    def get_specified_volume(self, name):
        """
        Find the specified volume with name
        :param name: volume name
        :returns: the volume
        """
        for vol in self.cinderclient.volumes.list():
            if vol.name == name:
                return vol

    def get_specified_volume_by_id(self, id):
        """
        Find the specified volume with name
        :param id: volume name
        :returns: the volume
        """
        for vol in self.cinderclient.volumes.list():
            if vol.id == id:
                return vol

    def find_volume_by_id(self, id):
        """
        Find the specified volume with id
        :param id: volume id
        :returns: if find the volume return True, otherwise return False
        """
        find = False
        for vol in self.cinderclient.volumes.list():
            if vol.id == id:
                return True

        return find

    def create_volume(self, name, size, image=None, volume_type=None):
        """
        Create volume
        :param name: volume name
        :param size: the size of the volume created
        :returns: the id of the volume created
        """
        volume = self.cinderclient.volumes.create(name=name, size=size,
                                                  imageRef=image,
                                                  volume_type=volume_type)

        if self.wait_for_volume_status(volume.id, 'available'):
            return volume.id

    def delete_volume(self, volume_id, timeout=60):
        """
        Delete volume
        :param volume_id: id of the volume deleted
        """
        find = False
        for vol in self.cinderclient.volumes.list():
            if vol.id == volume_id:
                find = True
                vol.delete()
        if not find:
            raise exceptions.TestFail("Cannot find volume %s to delete." %
                                      volume_id)

        timeout = timeout + time.time()
        while timeout > time.time():
            if not self.find_volume_by_id(volume_id):
                return True
            else:
                time.sleep(5)

        return False

    def get_volume_status(self, volume_id):
        """
        Get volume status
        :param name: volume name
        :returns: the status of the volume
        """
        for vol in self.cinderclient.volumes.list():
            if vol.id == volume_id:
                return vol.status

    def create_volume_backup(self, volume_id, backup_name, incremental=False):
        """
        Create volume
        :param volume_name: volume name
        :param backup_name: the name for volume backup
        :param incremental: Full backup or Incremental backup
        :returns: the backup volume id
        """
        volume_bak = self.volume_back.create(volume_id, name=backup_name,
                                                 incremental=incremental)

        if self.wait_for_volume_status(volume_id, 'backing-up'):
            return volume_bak

    def find_volume_backup_by_id(self, id):
        """
        Find the specified volume with id
        :param id: the id for volume backup
        :returns: if find the volume backup return True, otherwise return False
        """
        find = False
        for bak in self.volume_back.list():
            if bak.id == id:
                return True

        return find

    def delete_volume_backup(self, backup_id, timeout=60):
        """
        Delete volume backup
        :param backup_id: id of the backup volume
        """
        find = False
        for bak in self.volume_back.list():
            if bak.id == backup_id:
                find = True
                bak.delete()
        if not find:
            raise exceptions.TestFail("Cannot find the volume backup %s to delete." %
                                      backup_id)

        timeout = timeout + time.time()
        while timeout > time.time():
            if not self.find_volume_backup_by_id(backup_id):
                return True
            else:
                time.sleep(5)

        return False

    def create_volume_type(self, name):
        """
        Create volume type
        :param name: name of volume type
        :returns: the volume type
        """
        vol_type = self.volume_type.create(name)
        for vol_type in self.volume_type.list():
            if vol_type.name == name:
                return vol_type

    def delete_volume_type(self, id):
        """
        Delete volume type
        :param backup_id: id of the backup volume
        """
        self.volume_type.delete(id)
        for vol_type in self.volume_type.list():
            if vol_type.id == id:
                return False

        return True

    def get_volume_type_by_name(self, name):
        for vol_type in self.volume_type.list():
            if vol_type.name == name:
                return vol_type

    def wait_for_volume_status(self, volume_id, status, step=5, timeout=90):
        """Waits for a Volume to reach a given status."""
        start = int(time.time())

        current_status = self.get_volume_status(volume_id)
        if current_status == 'error' and status != 'error':
            raise exceptions.VolumeBuildErrorException(volume_id=
                                                       volume_id)
        if current_status == 'error_restoring':
            raise exceptions.VolumeRestoreErrorException(volume_id=
                                                         volume_id)
        while current_status != status:
            LOG.info("vol.status is %s" % current_status)
            time.sleep(step)
            current_status = self.get_volume_status(volume_id)
            if int(time.time()) - start >= timeout:
                LOG.info("time left is %s" % str(int(time.time()) - start))
                raise exceptions.TestFail('Volume %s failed to reach %s '
                                          'status (current %s) within '
                                          'the required time (%s s).' %
                                          (volume_id, status,
                                           current_status, timeout))

        return True





