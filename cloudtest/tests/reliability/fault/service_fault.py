import logging

from cloudtest.tests.reliability.fault import test_utils

LOG = logging.getLogger("avocado.test")


class ServiceFault(object):

    def __init__(self, nodes, params, env):
        self.nodes = nodes
        self.params = params
        self.env = env

    def setup(self):
        self.service_name = self.params.get("fault_service_name")
        self.fault_action = self.params.get("fault_action")
        self.select_policy = self.params.get("select_policy", "random")
        self.select_count = int(self.params.get("select_count", 1))

    def test(self):
        rets = []
        if self.select_policy in 'random':
            nodes = test_utils.random_select(self.nodes, self.select_count)
        for node in nodes:
            rets.append(node.act_to_service(self.fault_action, self.service_name))
        return all(rets)

    def teardown(self):
        rets = []
        for node in self.nodes:
            rets.append(node.act_to_service('start', self.service_name))
        return all(rets)


if __name__ == "__main__":
    params = {"fault_service_name": "openstack-nova-api",
              "fault_action": "stop",
              'roller_user': 'root',
              'roller_ip': '10.20.0.2'}
    #env = utils_env.Env(filename='/tmp/cloud_env')
    #sf = ServiceFault(None, params, env)
    #sf.setup()
    #sf.test()
    #sf.teardown()
