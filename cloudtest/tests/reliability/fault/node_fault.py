import logging
#import time
from avocado.utils import process
from cloudtest.openstack.cloud_manager import CloudManager
from cloudtest.openstack.cloud_node import CloudNode
from cloudtest import utils_env
from cloudtest import utils_misc

LOG = logging.getLogger("avocado.app")


class NodeFault(object):

    def __init__(self, session, params, env=None):
        self.session = None
        self.params = params
        self.env = env or utils_env.Env(filename="/tmp/cloud_env")
        self.nodes = None

    def setup(self):
        if ((self.params["process_name"] is None) and
            (self.params["service_name"] is None) and
            (self.params["fault_action"] is None) and
            (self.params["node_role"] is None) and
            (self.params["node_status"] is None)):
            raise Exception("Params fault.")
        self.cloudmanager = CloudManager(self.params, self.env)
        self.nodes = self.cloudmanager.get_nodes(
            node_role = self.params["node_role"],
            service_name = self.params["service_name"],
            select_policy = self.params["select_policy"],
            node_status = self.params["node_status"])
        if self.nodes is None:
            raise Exception("No valid node to inject.")


    def test(self):
        def check_dead_with_ping():
            cmd_check_boot = "ping -c 5 %s" % self.nodes[i].host
            result = process.run(cmd_check_boot, shell=True, 
                                 ignore_status=True, verbose=False)
            if result.exit_status is 0:
                return False
            else:
                return True
        results = []
        try:
            for i in range(len(self.nodes)):
                if self.params["fault_action"] == "crash":
                    self.nodes[i].panic()
                    result = utils_misc.wait_for(check_dead_with_ping,
                                        self.params["wait_recovery_timeout"],
                                        first=0)
                if self.params["fault_action"] == "reboot":
                    self.nodes[i].soft_reboot()
                    result = utils_misc.wait_for(check_dead_with_ping,
                                        self.params["wait_recovery_timeout"],
                                        first=0)
                if self.params["fault_action"] == "shutdown":
                    self.nodes[i].poweroff()
                results.append(result)
            return results
        except Exception, e:
            LOG.error("%s" % e)

    def teardown(self):
        if ((self.params["fault_action"] == "reboot") or 
            (self.params["fault_action"] == "crash")):
            def check_alive_with_ping():
                cmd_check_boot = "ping -c 5 %s" % self.nodes[i].host
                result = process.run(cmd_check_boot, shell=True, 
                                     ignore_status=True, verbose=False)
                if result.exit_status is 0:
                    return True
                else:
                    return False
            for i in range(len(self.nodes)):
                utils_misc.wait_for(check_alive_with_ping, 
                                    self.params["wait_recovery_timeout"], 
                                    first=5)



if __name__ == "__main__":
    session = None
    params = { "roller_user": "root",
              "roller_ip": "10.20.0.2",
              "wait_recovery_timeout": 50}
    params1 = { "node_role": "controller",
              "process_name" : None,
              "service_name" : None,
              "fault_action" : None,
              # can be reboot, shutdown or crash
              "select_policy": "random",
              "node_status": "ready"
             }
    params2 = { "node_role": "controller",
              "process_name" : "zzzkevinzzz.sh",
              "service_name" : None,
              "fault_action" : None,
              # can be reboot, shutdown or crash
              "select_policy": "random",
              "node_status": "ready"
             }
    params3 = { "node_role": "controller",
              "process_name" : None,
              #"service_name" : "firewalld",
              "service_name" : "openstack-nova-api",
              "fault_action" : None,
              # can be reboot, shutdown or crash
              "select_policy": "random",
              "node_status": "ready"
             }
   # params4 = { "node_role": "controller",
    params4 = { "node_role": "compute",
              "process_name" : None,
              "service_name" : None,
              "fault_action" : "crash",
              # can be reboot, shutdown or crash
              #"select_policy": "random"
              "select_policy": "all",
              #"node_status": "error"
              "node_status": "ready"
             }
    params5 = { "node_role": "controller",
              "process_name" : None,
              "service_name" : None,
              "fault_action" : "reboot",
              # can be reboot, shutdown or crash
              "select_policy": "random",
              "node_status": "ready"
             }
    params6 = { "node_role": "controller",
              "process_name" : None,
              "service_name" : None,
              "fault_action" : "shutdown",
              # can be reboot, shutdown or crash
              "select_policy": "random",
              "node_status": "ready"
             }
    params7 = { "node_role": "controller",
              "process_name" : "zzzkevinzzz.sh",
              "service_name" : "firewalld",
              "fault_action" : "crash",
              # can be reboot, shutdown or crash
              "select_policy": "random",
              "node_status": "ready"
             }
    params.update(params5)
    env = utils_env.Env(filename="/tmp/cloud_env")
    nf = NodeFault(session, params, env)
    nf.setup()
    nf.test()
    nf.teardown()
