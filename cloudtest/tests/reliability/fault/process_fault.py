import logging
import time

from cloudtest.remote import RemoteRunner
from cloudtest import utils_env
from cloudtest.openstack.cloud_manager import CloudManager

LOG = logging.getLogger("avocado.test")


class ProcessFault(object):
    def __init__(self, session, params, env):
        self.session = session
        self.params = params
        self.env = env
        self.nodes_service_infos = []
        self.service_name = self.params.get('fault_service_name')
        self.select_policy = self.params.get('select_policy')
        self.select_count = int(self.params.get('select_count'))
        self.cloud_manager = CloudManager(self.params, self.env)

    def setup(self):
        self.nodes_service_infos = self.cloud_manager.get_nodes_service_info(
            self.service_name,
            'all',
            self.select_count)

    def test(self):
        return self.cloud_manager.act_to_process(
            self.params.get('fault_action'),
            self.service_name,
            self.params.get('fault_scale'),
            self.select_policy,
            self.select_count)

    def teardown(self):
        nodes_service_infos_after_act = self.cloud_manager.get_nodes_service_info(
            self.service_name,
            'all',
            self.select_count)
        ret = False
        for node_service_info in self.nodes_service_infos:
            for node_service_info_after_act in nodes_service_infos_after_act:
                if node_service_info['node'].host == node_service_info_after_act['node'].host:
                    if len(node_service_info['service_info']['child_pids']) \
                            != len(node_service_info_after_act['service_info']['child_pids']):
                        LOG.error("The killed pids were not automatically restarted!")
                        time.sleep(int(self.params.get('recover_time')))
                        LOG.info("Waiting 60s so that the process can be started automatically!")
                        ret = False
                        break
                    else:
                        ret = True

        if not ret:
            nodes_service_infos_after_act = self.cloud_manager.get_nodes_service_info(
                self.service_name,
                'all',
                self.select_count)
            for node_service_info in self.nodes_service_infos:
                for node_service_info_after_act in nodes_service_infos_after_act:
                    if node_service_info['node'].host \
                            == node_service_info_after_act['node'].host:
                        if len(node_service_info['service_info']['child_pids']) \
                                != len(node_service_info_after_act['service_info']['child_pids']):
                            LOG.error("The killed pids were not automatically restarted!")
                            return False

        LOG.info("The killed pids were automatically restarted!")
        return True


if __name__ == '__main__':
    session = RemoteRunner(client='ssh', host="10.100.4.105", username="root", port="22",
                           password="123456")
    env = utils_env.Env(filename='/tmp/cloud_env')
    # params = {"process_name": "nova-api", "fault_action": "SIGKILL", "scale_type": "random"}
    params = {'roller_user': 'root',
              'roller_ip': '10.20.0.2',
              "fault_service_name": "openstack-keystone",
              "fault_action": "SIGSTOP",
              "fault_scale": "random"}
    cf = ProcessFault(session, params, env)
    cf.setup()
    cf.test()
    cf.teardown()
