import os
import logging
import time
import base64

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib.license_client import LicenseClient

LOG = logging.getLogger('avocado.test')


class TestLicense(test.Test):
    """
    License related test.
    """
    def __init__(self, params, env):
        self.params = params
        self.env = env
        self.body = {}

    def setup(self):
        self.client = LicenseClient(self.params)
        self.license_zip_file_path = self.params.get('license_zip_file_path')

    def test_get_license(self):
        resp = self.client.get_license()
        if not len(resp):
            raise exceptions.TestFail('No licence found!')

    def _get_zip_data(self):
        with open(self.license_zip_file_path, 'rb') as f:
            zipdata = base64.b64encode(f.read())
            return zipdata

    def test_validate_license(self):
        body = {"data": self._get_zip_data()}
        self.client.validate_license(**body)

    def test_update_license(self):
        body = {"data": self._get_zip_data()}
        self.client.update_license(**body)

    def teardown(self):
        pass