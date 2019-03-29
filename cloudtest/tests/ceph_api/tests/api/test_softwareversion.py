import logging

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib.version_client import VersionClient

LOG = logging.getLogger('avocado.test')


class TestVersion(test.Test):
    """
    Job list related tests.
    """

    def __init__(self, params, env):
        self.params = params
        self.client = VersionClient(params)
        self.body = {}
        self.env = env

    def setup(self):
        pass

    def test_get_version(self):
        resp = self.client.query_softwareversion()
        LOG.info("Got version: %s" % resp.body)
        if not len(resp) > 0:
            raise exceptions.TestFail("Get version failed!")

    def teardown(self):
        pass