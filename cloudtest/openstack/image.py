import logging
import os_client_config

from common import Common


class Image(Common):
    def __init__(self, params=None):
        super(Image, self).__init__(params)
        self.imageclient = os_client_config.make_client(
            'image', **self.nova_credential)
        self.log = logging.getLogger('avocado.test')

    def get_image(self, name):
        """
        Retrieve an image object
        :param name: the name of image
        """
        image = None
        images = self.imageclient.images.list()
        for img in images:
            if img.name == name:
                image = img
                break
        return image

    def _create_image(self, name='cloudtest_main', container_format="bare",
                      disk_format='raw', image_format='qcow2',
                      min_disk_size="0", min_ram=0, visibility='public',
                      is_public="public"):
        """
        Create an empty image
        :param name: the name of image
        :param container_format: the container format of image
        :param disk_format: the disk format of image
        :param image_format: the image format of image
        :param min_disk_size: the mini disk size of image
        :param min_ram: the mini ram of image
        :param visibility: the visibility of image
        :param is_public: if the image is public or not
        :returns: Created image object
        """
        kw = {
            "name": name,
            "container_format": container_format,
            "disk_format": disk_format,
            "image_format": image_format,
            "min_disk_size": min_disk_size,
            "min_ram": min_ram,
            "visibility": visibility,
            "is_public": is_public
        }
        result = self.imageclient.images.create(**kw)
        return result

    def _upload_image(self, image_id, image_data):
        """
        Upload the image data to image.
        :param image_id: the id of image
        :param image_data: the data to update to image
        :returns: the updated image object
        """
        kw = {
            "image_id": image_id,
            "image_data": image_data
        }
        return self.imageclient.images.upload(**kw)

    def delete_image(self, name):
        """
        Delete image
        :param name: the name of image to delete
        :returns: if delete image is successful then return True
                  or not successful return False
        """
        self.log.info("Try to delete image: %s" % name)
        img = self.get_image(name)
        if img:
            result = self.imageclient.images.delete(img.id)
            self.log.info("Successfully deleted image: %s" % name)
            return True
        self.log.error("Failed to find the image: %s" % name)
        return False

    def get_image_id(self, image_name):
        """
        Get image id
        :param image_name: the name of image
        :returns: the image id
        """
        image_id = None
        img = self.get_image(image_name)
        if img:
            image_id = img.id
        return image_id

    def get_image_data(self, img_path):
        """
        Get image data
        :param img_path: the path of image
        :returns: the data of the image
        """
        image_data = open(img_path, "rb")
        return image_data

    def create_image(self, name, image_path):
        """
        Create image
        :param name: image name
        :param image_path: the path of image data file
        :returns: the id of the image created
        """
        result = self._create_image(name=name)
        image_data = self.get_image_data(image_path)
        self._upload_image(image_id=result["id"], image_data=image_data)
        return result["id"]
