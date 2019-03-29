#!/usr/bin/env python
# coding=utf-8

import os
import logging
from cloudtest import remote
from cloudtest import data_dir

LOG = logging.getLogger("avocado.test")


class StressNG(object):
    def __init__(self, nodes, params, env):
        self.nodes = nodes
        self.params = params
        self.env = env
        self.srcpkg = 'stress-ng-0.07.25.tar.gz'
        self.dstpath = '/root'
        self.workload_path = ('%s/reliability/workload' %
                              data_dir.CLOUDTEST_TEST_DIR)
        self.stressng_path = ('%s/stress-ng-0.07.25' % self.workload_path)
        self.dstpkg = '/root/stress-ng-0.07.25.tar.gz'
        self.init_usage = dict(cpu=0, mem=0, mem_total=0)
        self.tag_usage = dict(cpu=0, mem=0)
        self.cmd = ""
        self.output = ""
        self.session = self.nodes[0].ssh_session

    def load_workload(self):
        """
        Get current resource usage and generate the stress-ng cmd.
        """
        flag_cpu = False
        flag_mem = False
        flag_io = False
        io_cmd = ""
        cpu_cmd = ""
        mem_cmd = ""
        timeout = ""
        self.init_usage = remote.get_remote_resource_usage(self.session)

        if self.params.has_key('expected_cpu_usage'):
            if (float(self.init_usage['cpu']) >=
                    float(self.params['expected_cpu_usage'])):
                LOG.info("The MEM usage expected is %f, but now this is %f." %
                         (float(self.params['expected_cpu_usage']),
                          float(self.init_usage['cpu'])))
            else:
                self.tag_usage['cpu'] = \
                    (float(self.params['expected_cpu_usage']) -
                     float(self.init_usage['cpu']))
                cpu_cmd = ("--cpu 0 --cpu-load %d%% " %
                           int(self.tag_usage['cpu']))
                self.output = ("CPU: %s" %
                               int(self.params['expected_cpu_usage']))
                flag_cpu = True

        if self.params.has_key('expected_mem_usage'):
            if (float(self.init_usage['mem']) >=
                    float(self.params['expected_mem_usage'])):
                LOG.info("The MEM usage expected is %f, but now this is %f." %
                         (float(self.params['expected_mem_usage']),
                          float(self.init_usage['mem'])))
            else:
                self.tag_usage['mem'] = \
                    (float(self.params['expected_mem_usage']) -
                     float(self.init_usage['mem']))
                mem_cmd = ("--vm-rw 1 --vm-rw-bytes %d%% " %
                           int(self.tag_usage['mem']))
                self.output = ("%s ,MEM: %s" %
                               (self.output,
                                int(self.params['expected_mem_usage'])))
                flag_mem = True

        if self.params.has_key('expected_io_type'):
            self.output = ("%s ,I/O: %s" % (self.output,
                                            self.params['expected_io_type']))
            if self.params['expected_io_type'] == 'read':
                io_cmd = "--hdd 1 --hdd-bytes 1m --hdd-opt rd-rnd"
                flag_io = True
            else:
                if self.params['expected_io_type'] == 'write':
                    io_cmd = "--hdd 1"
                    flag_io = True
                else:
                    if self.params['expected_io_type'] == 'mix':
                        io_cmd = "--iomix 1 --iomix-bytes 10%"
                        flag_io = True

        if self.params.has_key('workload_timeout'):
            if self.params['workload_timeout'] == "0":
                timeout = ""
            else:
                timeout = (" -t %ss " % self.params['workload_timeout'])

        self.cmd = ("cd %s; ./stress-ng %s %s %s %s --times "
                    % (self.stressng_path, cpu_cmd, mem_cmd,
                       io_cmd, timeout))
        LOG.info('%s' % self.cmd)
        return flag_cpu & flag_mem & flag_io

    def install_stressng(self):
        """
        Install stress-ng to the host
        """
        self.session.copy_file_to(os.path.join(self.workload_path, self.srcpkg),
                                  self.dstpath)
        self.session.run("mkdir -p %s" % self.workload_path)
        self.session.run("tar zxvf %s -C %s" % (self.dstpkg,
                                                self.workload_path))
        self.session.run("cd %s ; make" % self.stressng_path)

    def setup(self):
        self.install_stressng()
        return self.load_workload()

    def test(self):
        try:
            LOG.info("Start injecting workload:")
            LOG.info(self.output)
            # Start inject stress-ng
            result = self.session.run(self.cmd)
            LOG.info('%s' % result)
        except Exception, e:
            return False
        return True

    def teardown(self):
        LOG.info("Try to pkill stress-ng!")
        try:
            self.session.run('pkill stress-ng || true')
            self.session.run("rm -rf %s %s" %
                             (self.stressng_path, self.dstpkg))
        except Exception, e:
            return False
        finally:
            self.session.session.close()
        return True
