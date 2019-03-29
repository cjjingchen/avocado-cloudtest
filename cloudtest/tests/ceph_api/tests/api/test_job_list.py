import logging

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib.job_list_client import JobListClient

LOG = logging.getLogger('avocado.test')


class TestJobList(test.Test):
    """
    Job list related tests.
    """

    def __init__(self, params, env):
        self.params = params
        self.client = JobListClient(params)
        self.body = {}
        self.env = env

    def setup(self):
        pass

    def test_query_job_list(self):
        job_filter = self.params.get('job_filter')
        resp = self.client.query_job_list(job_filter)
        body = resp.body
        jobs_length = len(body.get('items'))
        if jobs_length > 0:
            if job_filter:
                for job_data in body.get('items'):
                    if job_filter not in job_data.get('name'):
                        raise exceptions.TestFail(
                            "Get job data failed, "
                            "not all data come from filer %s" % job_filter)
        else:
            raise exceptions.TestFail("No job data found!")

    def teardown(self):
        pass

