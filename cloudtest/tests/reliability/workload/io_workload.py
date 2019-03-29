import os
import logging

from cloudtest.remote import RemoteRunner
from cloudtest import data_dir
from cloudtest.openstack.cloud_node import CloudNode

LOG = logging.getLogger("avocado.test")


class FIO(object):
    def __init__(self, nodes, params=None, env=None):
        self.params = params
        self.env = env
        #self.session = session
        storage_host = self.params.get('storage_host')
        storage_host_password = self.params.get('storage_host_password')
        if storage_host_password == "" or storage_host_password == None:
            self.session = CloudNode(storage_host).get_ssh_session()
        else:
            self.session = RemoteRunner(client='ssh', host=storage_host,
                                        username="root", port="22",
                                        password=storage_host_password)
        self.fio_dir = ""
        self.dstpath = '/root'
        self.workload_path = ('%s' % data_dir.RELIABILITY_TEST_DIR) + \
                             "/workload"
        self.fio_version = self.params.get('fio_version')
        self.fio_working_path = \
            self.fio_version[0:len(self.fio_version) - len('.tar.gz')]
        self.fio_filename = self.params.get('fio_parameter_filename')
        self.direct = self.params.get('fio_parameter_direct')
        self.bs = self.params.get('fio_parameter_bs')
        self.size = self.params.get('fio_parameter_size')
        self.numjobs = self.params.get('fio_parameter_numjobs')
        self.report_name = self.params.get('fio_parameter_report_name')
        self.runtime = self.params.get("fio_parameter_runtime")

        self.cmd = ""

    def setup(self):
        self.install_fio(self.workload_path, self.dstpath,
                                      self.fio_version, self.fio_working_path)

    def teardown(self):
        self.uninstall_fio(self.dstpath, self.fio_version,
                                        self.fio_working_path)

    def install_fio(self, srcpath, dstpath, fio_version, fio_working_path):
        self.session.copy_file_to(os.path.join(srcpath, fio_version), dstpath)
        cmd = "tar -zxvf %s" % fio_version
        cmd = self.cmd + cmd
        self.session.run(cmd)
        cmd = "cd %s ; ./configure; make " % os.path.join(dstpath,
                                                          fio_working_path)
        cmd = self.cmd + cmd
        self.session.run(cmd)

    def uninstall_fio(self, dstpath, fio_version, fio_working_path):
        try:
            cmd = 'pkill fio || true'
            cmd = self.cmd + cmd
            self.session.run(cmd)
            cmd = "rm -rf %s %s" % (os.path.join(dstpath, fio_version),
                                    os.path.join(dstpath, fio_working_path))
            cmd = self.cmd + cmd
            self.session.run(cmd)
        except Exception, e:
            return False
        return True

    def fio_operation(self, dstpath, fio_working_path, filename, direct, rw,
                      bs,
                      size, numjobs, report_name, runtime=None):
        cmd = 'cd %s' % os.path.join(dstpath, fio_working_path)
        cmd = self.cmd + cmd
        self.session.run(cmd)
        if runtime is None:
            cmd = './fio -filename=%s -direct=%s -rw=%s -bs=%s -size=%s ' \
                  '-numjobs=%s -group_reporting -name=%s' % \
                  (filename, direct, rw, bs, size, numjobs, report_name)

        else:
            cmd = './fio -filename=%s -direct=%s -rw=%s -bs=%s -size=%s ' \
                  '-numjobs=%s -runtime=%s -group_reporting -name=%s' % \
                  (filename, direct, rw, bs, size, numjobs, runtime,
                   report_name)

        cmd = cmd + self.cmd
        result = self.session.run(cmd, timeout=120)

        return result.exit_status, result.stdout

    def test(self):
        fio_action = self.params.get('io_fio_workload_action')
        exit_status, out = self.fio_operation(self.dstpath,
                           self.fio_working_path, self.fio_filename,
                           self.direct, fio_action, self.bs, self.size,
                           self.numjobs, self.report_name, self.runtime)
        LOG.info("FIO exit_status is %s" % exit_status)
        LOG.info("FIO report following ...")
        LOG.info(out)


if __name__ == '__main__':
    session = RemoteRunner(client='ssh', host="10.100.4.161", username="root",
                           port="22", password="123456")
    params = {"storage_host": "10.100.4.161",
              "storage_host_password": "123456",
              "io_fio_workload_action": "randread",
              "fio_parameter_filename": "/dev/sdb3",
              "fio_version": "fio-2.1.10.tar.gz", "fio_parameter_size": "1G",
              "fio_parameter_direct": "1", "fio_parameter_bs": "4k",
              "fio_parameter_numjobs": "64", "fio_parameter_runtime": "20",
              "fio_parameter_report_name": "fio_test",
              "fio_parameter_runtime": "20"}

    cf = FIO(session, params)
    cf.setup()
    cf.test()
    cf.teardown()
