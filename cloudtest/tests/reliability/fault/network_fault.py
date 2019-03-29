import logging
import time

from cloudtest.openstack.cloud_manager import CloudManager

LOG = logging.getLogger("avocado.test")
FAULT_LIST = ("loss", "delay", "duplicate", "corrupt", "reorder")
INTERFACE_FLASH = "interface_flash"
DOWN = "done"


class NetworkFault(object):
    def __init__(self, session, params, env):
        self.session = session
        self.params = params
        self.env = env
        self.flag = False  # Using for check fault action is tc cmd
        self.nodes = []

    def setup(self):
        self.cloud_manager = CloudManager(self.params, self.env)
        self.bridge_name = self.params.get('br_name')
        self.fault_action = self.params.get("fault_action")
        self.flash_count = self.params.get("flash_count")
        self.flash_time = self.params.get("flash_time")
        self.select_policy = self.params.get("select_policy", "random")
        self.select_count = int(self.params.get("select_count", 1))

    def test(self):
        ret = False
        for fault in FAULT_LIST:
            if fault in self.fault_action:
                self.flag = True
        if self.flag:
            ret, self.nodes = self.cloud_manager.act_to_net(
                                self.bridge_name,
                                'add',
                                self.fault_action,
                                self.select_policy,
                                self.select_count)
        elif self.fault_action == DOWN:
            ret = self.__network_down()
        elif self.fault_action == INTERFACE_FLASH:
            ret = self.__test_network_flash()
        return ret

    def teardown(self):
        rets = []
        for node in self.nodes:
            if self.flag:
                rets.append(node.traffic_control(self.fault_action,
                             self.bridge_name, 'del'))
            elif self.fault_action == DOWN:
                rets.append(node.act_to_network(self.bridge_name, 'up'))
        return all(rets)

    def __test_network_flash(self):
        count = 0
        rets = []
        while count < self.flash_count:
            ret1 = self.__network_down()
            time.sleep(self.flash_time)
            for node in self.nodes:
                rets.append(node.act_to_network(self.bridge_name, 'up'))
            ret2 = all(rets)
            count = count + 1
            if False in (ret1, ret2):
                return False
        return True

    def __network_down(self):
        # TODO: not run test
        ret, self.nodes = self.cloud_manager.act_to_net(
                                self.bridge_name,
                                'down',
                                select=self.select_policy,
                                count=self.select_count)
        return ret


if __name__ == "__main__":
    params = {"interface_name": "eth0",
              "fault_action": "loss 5% 25%",
              'flash_count': 5,
              'flash_time': 3,
              'roller_user': 'root',
              'roller_ip': '10.20.0.2'}
    #env = utils_env.Env(filename='/tmp/cloud_env')
    #sf = NetworkFault(None, params, env)
    #sf.setup()
    #sf.test()
    #sf.teardown()
