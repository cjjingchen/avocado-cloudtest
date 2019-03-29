import logging
import os

from cloudtest import utils_env
from cloudtest import data_dir
from cloudtest.remote import RemoteRunner

LOG = logging.getLogger("avocado.test")
LOG.level = logging.INFO
LTP_RUN_PATH = '/opt/ltp'


class NetworkWorkload(object):
    def __init__(self, nodes, params, env):
        self.nodes = nodes
        self.session = self.nodes[0].ssh_session
        self.params = params
        self.env = env
        self.nodes = []

    def setup(self):
        self.ltp_cmd = self.params.get('ltp_cmd')
        self.file_version = self.params.get('file_version')
        self.file_working_path = \
            self.file_version[0:len(self.file_version) - len('.tar.gz')]
        self.dstpath = '/root'
        self.workload_path = ('%s' % data_dir.RELIABILITY_TEST_DIR) \
                              + '/workload'
        self.select_policy = self.params.get("select_policy", "random")
        self.select_count = int(self.params.get("select_count", 1))
        make_cmd = 'make autotools ; ./configure; make; make install'
        self.__install_tool(make_cmd)

    def teardown(self):
        file_list = '%s %s %s' % (os.path.join(self.dstpath, self.file_version),
                                  os.path.join(self.dstpath, self.file_working_path),
                                  LTP_RUN_PATH)
        self.session.run('pkill ltp || true')
        self.session.run("rm -rf %s" % file_list)
        self.session.session.close()

    def test(self):
        cmd = 'cd %s ; %s' % (LTP_RUN_PATH, self.ltp_cmd)
        result = self.session.run(cmd)
        if result.exit_status != 0:
            LOG.error("Failed to run %s" % cmd)
        LOG.info("Successfully run %s" % cmd)

    def __install_tool(self, make_cmd):
        self.session.copy_file_to(os.path.join(self.workload_path,
                                               self.file_version), self.dstpath)
        LOG.info("tar -zxvf %s" % (self.file_version))
        self.session.run("tar -zxvf %s" % (self.file_version))
        LOG.info("cd %s ; %s" % (self.file_working_path, make_cmd))
        self.session.run("cd %s ; %s" % (self.file_working_path, make_cmd), timeout=600)


if __name__ == '__main__':
    session = RemoteRunner(client='ssh', host="10.100.109.120", username="root", port="22",
                           password="123456")
    params = {'file_version': 'ltp.tar.gz',
              'ltp_cmd': './runltp -n'}
    env = utils_env.Env(filename='/tmp/cloud_env')
    cf = NetworkWorkload(session, params, env)
    cf.setup()
    cf.test()
    cf.teardown()
