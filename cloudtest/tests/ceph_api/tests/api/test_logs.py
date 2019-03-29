import logging
import time

from avocado.core import test
from avocado.core import exceptions
from cloudtest.tests.ceph_api.lib.logs_client import LogsClient

LOG = logging.getLogger('avocado.test')


class TestOperationLogs(test.Test):
    """
    Operation logs related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.env = env
        self.client= LogsClient(self.params)

    def setup(self):
        pass

    def test_query_operation_logs(self):
        user_name = self.params.get('user_name')
        category = self.params.get('category')
        state = self.params.get('state')
        start_time = self.params.get('start_time')
        end_time = self.params.get('end_time')
        if user_name:
            extral_url = "user=%s" % user_name
        else:
            extral_url = "user=all"
        if category:
            extral_url = extral_url + "&category=%s" % category
        if state:
            extral_url = extral_url + "&state=%s" % state
        if start_time:
            extral_url = extral_url + "&starttime=%s" % start_time
            start_str = start_time.split('+')[0] + " " + start_time.split('+')[1]
            s_time = time.mktime(time.strptime(start_str, "%Y-%m-%d %H:%M:%S"))
        if end_time:
            extral_url = extral_url + "&endtime=%s" % end_time
            end_str = end_time.split('+')[0] + " " + end_time.split('+')[1]
            e_time = time.mktime(time.strptime(end_str, "%Y-%m-%d %H:%M:%S"))
        resp_bodys = self.client.query_operation_logs(extral_url)
        for body in resp_bodys.get("items"):
            if user_name:
                if body.get('user') != user_name:
                    raise exceptions.TestFail(
                        "Get logs from user %s failed,"
                        " not all logs come from user %s!"
                        % (user_name, user_name))
            if category:
                if body.get('category') != category:
                    raise exceptions.TestFail(
                        "Failed to get %s category log, "
                        "not all logs belong to %s type!"
                        % (category, category))
            if state:
                if body.get('state') != state:
                    raise exceptions.TestFail(
                        "Failed to get %s state log, "
                        "not all logs state is %s !"
                        % (state, state))
            if start_time and end_time:
                log_stime = time.mktime(
                    time.strptime(body.get('start_time'),
                                  "%Y-%m-%d %H:%M:%S"))
                log_etime = time.mktime(
                    time.strptime(body.get('end_time'),
                                  "%Y-%m-%d %H:%M:%S"))
                if (log_etime < s_time) or (log_stime > e_time):
                    raise exceptions.TestFail(
                        "Failed to get logs between %s and %s!"
                        % (start_str, end_str))

    def teardown(self):
        pass
