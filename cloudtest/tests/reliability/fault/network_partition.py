import logging

from cloudtest.remote import RemoteRunner
from cloudtest import utils_env
from cloudtest.openstack.cloud_manager import CloudManager

LOG = logging.getLogger("avocado.test")


class NetworkPartition(object):

    def __init__(self, session, params, env):
        self.session = session
        self.params = params
        self.env = env
        self.partition_ports = []
        self.service_name = self.params.get('fault_service_name')
        self.select_policy = self.params.get('select_policy')
        self.select_count = int(self.params.get('select_count'))
        self.cloud_manager = CloudManager(self.params, self.env)

    def setup(self):
        service_port = self.params.get("service_port")
        if service_port:
            self.partition_ports = service_port.split(',')

    def test(self):
        act_rule = {'action':'A', 'port': self.partition_ports}
        # inject fault by inserting iptables rules
        ret, self.nodes = self.cloud_manager.act_to_iptables(
            act_rule,
            self.service_name,
            self.select_policy,
            self.select_count)

    def teardown(self):
        """
        Delete the added iptables rules
        :return: 
        """
        rets = []
        act_rule = {'action': 'D', 'port': self.partition_ports}
        for node in self.nodes:
            rets.append(node.act_to_iptables(act_rule))

        return all(rets)

if __name__ == '__main__':
    session = RemoteRunner(client='ssh', host="10.100.64.36", username="root", port="22",
                           password="passw0rd")
    env = utils_env.Env(filename='/tmp/cloud_env')
    params = {'roller_user': 'root',
              'roller_ip': '10.20.0.2',
              'fault_service_name': 'openstack-nova-api',
              'service_port': '8774,8775'}
    cf = NetworkPartition(session, params, env)
    cf.setup()
    cf.test()
    cf.teardown()