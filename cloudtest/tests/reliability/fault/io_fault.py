import os
import logging
import re

from cloudtest import data_dir
from cloudtest.remote import RemoteRunner
from cloudtest.remote import RemoteUtils
from cloudtest.openstack.cloud_manager import CloudManager
from cloudtest.openstack.cloud_node import CloudNode


LOG = logging.getLogger("avocado.test")


def convert_to_byte(unit, data):
    re_data = 0
    if unit == 'K':
        re_data = data * 1024
    elif unit == 'M':
        re_data = data * 1024 * 1024
    elif unit == 'G':
        re_data = data * 1024 * 1024 * 1024
    elif unit == 'T':
        re_data = data * 1024 * 1024 * 1024 * 1024
    return re_data


def convert_to_right_unit(data):
    in_data = data
    n = 0
    re_unit = ''

    while in_data > 1024:
        in_data /= 1024
        n += 1

    if n == 0:
        re_unit = 'B'
    elif n == 1:
        re_unit = 'K'
    elif n == 2:
        re_unit = 'M'
    elif n == 3:
        re_unit = 'G'
    elif n == 4:
        re_unit = 'T'

    if 1024 > in_data > 0:
        return in_data, re_unit


class IOFault(object):

    def __init__(self, session, params=None, env=None):
        self.params = params
        self.env = env

        roller_node = CloudNode(self.params.get('roller_ip'))
        self.session = roller_node.get_ssh_session()

        cloud_manager = CloudManager(params, env)
        compute_node = cloud_manager.get_compute_node()
        LOG.info("compute node is %s" % compute_node[0].host)

        self.cmd = "ssh -q %s -t " % compute_node[0].host
        self.fio_dir = ""
        self.dstpath = '/root'
        self.workload_path = ('%s' % data_dir.RELIABILITY_TEST_DIR) + \
                             "/workload"
        self.fio_version = self.params.get('fio_version')
        self.fio_working_path = \
            self.fio_version[0:len(self.fio_version)-len('.tar.gz')]
        self.mount_point = self.params.get('io_fault_mount_point')
        self.partition = self.params.get('partition')
        self.fio_filename = self.params.get('fio_filename')
        self.warning_base = self.params.get('warning_base', '80')
        self.disk_left = self.params.get('disk_left')
        self.direct = self.params.get('direct', '0')
        self.rw = self.params.get('rw', 'write')
        self.bs = self.params.get('fio_bs')
        self.numjobs = self.params.get('fio_numjobs')
        self.report_name = self.params.get('report_name', 'fio_write')

    def setup(self):
        self.install_fio(self.workload_path, self.dstpath,
                                      self.fio_version, self.fio_working_path)

        if self.fio_filename != "":
            self.mount_disk(self.mount_point, self.partition)
            # get file dir and file name
            file_name_list = self.fio_filename.split('/')
            file_name = file_name_list[len(file_name_list)-1]
            self.fio_dir = \
                self.fio_filename[0:len(self.fio_filename)-len(file_name)]

            cmd = "mkdir -p %s" % self.fio_dir
            cmd = self.cmd + cmd
            result = self.session.run(cmd)
            if result.exit_status == 0:
                LOG.info("Create %s Successfully" % self.fio_dir)
            else:
                LOG.error("Failed to create %s" % self.fio_dir)

            cmd = "touch %s" % self.fio_filename
            cmd = self.cmd + cmd
            result = self.session.run(cmd)
            if result.exit_status == 0:
                LOG.info("Create %s Successfully" % self.fio_filename)
            else:
                LOG.error("Failed to create %s" % self.fio_filename)

    def teardown(self):
        if self.fio_filename != "":
            cmd = "rm -rf %s" % self.fio_dir
            cmd = self.cmd + cmd
            result = self.session.run("rm -rf %s" % self.fio_dir)
            if result.exit_status == 0:
                LOG.info("Delete %s Successfully" % self.fio_dir)
            else:
                LOG.error("Failed to delete %s" % self.fio_dir)

            if self.params.get("io_fault_test_name") != 'disk_down':
                self.umount_disk(self.mount_point)

        self.uninstall_fio(self.dstpath, self.fio_version,
                                        self.fio_working_path)

    def test(self):
        test_name = self.params.get("io_fault_test_name")
        if test_name == 'disk_down':
            self._test_umount_disk()
        elif test_name == 'disk_almost_full_percentage':
            self._test_disk_almost_full_percentage()
        elif test_name == 'disk_almost_full_size':
            self._test_disk_almost_full_size()
        elif test_name == 'disk_full':
            if self.warning_base == '100':
                self._test_disk_almost_full_percentage()
            elif self.disk_left == '0':
                self._test_disk_almost_full_size()
            else:
                LOG.error("Running disk_full with warning_base:%s "
                          "and disk_left:%s is impossible." %
                          (self.warning_base, self.disk_left))

    def mount_disk(self, mount_point, partition):
        cmd = "mount %s %s" % (partition, mount_point)
        cmd = self.cmd + cmd

        try:
            result = self.session.run(cmd, ignore_status=True)
        except Exception, e:
            return False

        if result.exit_status == 0 or result.exit_status == 32:
            return True
        else:
            return False

    def umount_disk(self, mount_point):
        cmd = "umount %s" % mount_point
        cmd = self.cmd + cmd

        if os.path.exists(mount_point):
            result = self.session.run(cmd)
        if result.exit_status == 0:
            return True
        else:
            return False

    def install_fio(self, srcpath, dstpath, fio_version, fio_working_path):
        self.session.copy_file_to(os.path.join(srcpath, fio_version), dstpath)
        cmd = "tar -zxvf %s" % fio_version
        cmd = self.cmd + cmd
        self.session.run(cmd)
        cmd = "cd %s ; ./configure; make " % os.path.join(dstpath, fio_working_path)
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

    def _test_disk_almost_full_percentage(self):
        cmd_size = 'df -h'
        cmd_size = self.cmd + cmd_size

        result_size = self.session.run(cmd_size)
        pat = "%s (.*)/" % self.partition
        info = re.findall(pat, result_size.stdout)[0]
        # Get disk size of the partition
        disk_size = info.strip().split(' ')[:][0]
        disk_data = int(disk_size[0:len(disk_size)-1])
        fio_size = disk_data * int(self.warning_base) / 100
        disk_unit = disk_size[len(disk_size)-1:len(disk_size)]

        if fio_size > 0:
            size = '%d' % fio_size + disk_unit
        else:
            # Covert to right disk unit
            disk_size = convert_to_byte(disk_unit, disk_data)
            fio_size = disk_size * int(self.warning_base) / 100
            fio_size, fio_unit = convert_to_right_unit(fio_size)
            size = '%d' % fio_size + fio_unit

        if self.fio_filename == "":
            exit_status, out = self.fio_operation(self.dstpath,
                               self.fio_working_path, self.partition,
                               self.direct, self.rw, self.bs, size,
                               self.numjobs, self.report_name)
        else:
            exit_status, out = self.fio_operation(self.dstpath,
                               self.fio_working_path, self.fio_filename,
                               self.direct, self.rw, self.bs,
                               size, self.numjobs, self.report_name)
        LOG.info(out)

    def _test_disk_almost_full_size(self):
        cmd_size = 'df -h'
        cmd_size = self.cmd + cmd_size

        result_size = self.session.run(cmd_size)
        pat = "%s (.*)/" % self.partition
        info = re.findall(pat, result_size.stdout)[0]
        # Get disk size of the partition
        disk_size = info.strip().split(' ')[:][0]
        disk_data = int(disk_size[0:len(disk_size)-1])
        # Get disk unit of the partition
        disk_unit = disk_size[len(disk_size)-1:len(disk_size)]
        disk_size = convert_to_byte(disk_unit, disk_data)

        disk_left_data = int(self.disk_left[0:len(self.disk_left) - 1])
        disk_left_unit = \
            self.disk_left[len(self.disk_left) - 1:len(self.disk_left)]
        disk_left_size = convert_to_byte(disk_left_unit, disk_left_data)

        fio_data = disk_size - disk_left_size
        fio_size, fio_unit = convert_to_right_unit(fio_data)

        size = '%d' % fio_size + fio_unit
        if self.fio_filename == "":
            exit_status, out = self.fio_operation(self.dstpath,
                               self.fio_working_path, self.partition,
                               self.direct, self.rw, self.bs, size,
                               self.numjobs, self.report_name)
        else:
            exit_status, out = self.fio_operation(self.dstpath,
                               self.fio_working_path, self.fio_filename,
                               self.direct, self.rw, self.bs, size,
                               self.numjobs, self.report_name)
        LOG.info(out)

    def _test_umount_disk(self):
        self.umount_disk(self.mount_point)

class IOFaultCeph(object):

    def __init__(self, session, params=None, env=None):
        self.params = params
        self.env = env
        roller_node = CloudNode(self.params.get('roller_ip'))
        self.session = roller_node.get_ssh_session()

        self.ceph_node = self.params.get('ceph_node')
        self.osd_num = self.params.get('osd_num')
        self.mount_point = ''
        self.filename = "dd_test"
        self.cmd = "ssh -q %s -t " % (self.ceph_node)
        self.remote_utils = RemoteUtils(self.session)

    def setup(self):
        self.get_ceph_mount_point()

    def teardown(self):
        try:
            cmd = 'pkill dd || true'
            self.session.run(self.cmd + cmd)
            cmd = "rm -f %s/%s" % (self.mount_point, self.filename)
            self.session.run(self.cmd + cmd)
        except Exception, e:
            LOG.info(e)

        osd_stat = self.get_osd_status(self.osd_num)
        if osd_stat == 'down':
            self.start_osd(self.osd_num)

    def test(self):
        test_name = self.params.get("io_fault_test_name")
        if test_name == 'osd_down':
            self._test_osd_down()
        elif test_name == 'disk_almost_full_percentage':
            self._test_disk_almost_full_percentage()
        elif test_name == 'disk_almost_full_size':
            self._test_disk_almost_full_size()

    def get_ceph_mount_point(self):
        cmd = 'mount | grep -i ceph'

        if self.ceph_node:
            cmd = self.cmd + cmd
        result = self.session.run(cmd)

        self.mount_point = result.stdout.split(' ')[2]

        LOG.info("ceph mount point is %s" % self.mount_point)

    def dd_write(self, mount_point, of, bs):
        cmd = 'dd if=/dev/zero of=%s/%s bs=%s count=1' % (self.mount_point, of,
                                                          bs)
        if self.ceph_node:
            cmd = self.cmd + cmd
        result = self.session.run(cmd)

        if result.exit_status == 0:
            LOG.info("dd implement successfully.")
        else:
            LOG.error("dd implement failed.")

    def get_volume(self, result_size):
        pat = "(.*) %s" % self.mount_point
        info = re.findall(pat, result_size.stdout)[0]
        # Get disk size of the partition
        info = info.strip().split('//s+')
        info_separator = ','.join(filter(lambda x: x, info[0].split(' ')))
        info_list = info_separator.split(',')
        disk_data = float(info_list[1][0:len(info_list[1]) - 1])
        # Get used disk size of volume
        used_disk_data = float(info_list[2][0:len(info_list[2]) - 1])
        disk_unit = info_list[1][len(info_list[1]) - 1:len(info_list[1])]
        used_disk_unit = info_list[2][len(info_list[2]) - 1:len(info_list[1])]

        return disk_data, disk_unit, used_disk_data, used_disk_unit

    def start_osd(self, osd_num):
        cmd = "/etc/init.d/ceph -a start %s" % osd_num
        if self.ceph_node:
            cmd = self.cmd + cmd
        result = self.session.run(cmd)

        if result.exit_status == 0:
            LOG.info("Start %s successfully." % osd_num)
        else:
            LOG.error("Start %s failed." % osd_num)

    def get_osd_status(self, osd_num):
        cmd = "ceph osd dump"
        if self.ceph_node:
            cmd = self.cmd + cmd

        result = self.session.run(cmd)
        pat = "%s (.*)" % osd_num
        info = re.findall(pat, result.stdout)[0]
        osd_stat = info.split(' ')[0]

        return osd_stat

    def _test_disk_almost_full_percentage(self):
        usage_warning = self.params.get('usage_warning_in_percentage', '80')

        cmd = 'df -h'
        if self.ceph_node:
            cmd = self.cmd + cmd

        result_size = self.session.run(cmd)
        disk_data, disk_unit, used_disk_data, used_disk_unit = \
            self.get_volume(result_size)

        if disk_unit == used_disk_unit:
            write_size = disk_data * int(usage_warning) / 100 \
                          - used_disk_data
            write_unit = disk_unit
        else:
            # Convert volume size to byte
            disk_size = convert_to_byte(disk_unit, disk_data)
            used_disk_size = convert_to_byte(used_disk_unit, used_disk_data)
            write_size_byte = disk_size * int(usage_warning) / 100 \
                              - used_disk_size
            write_size, write_unit = convert_to_right_unit(write_size_byte)

        self.dd_write(self.mount_point, self.filename,
                      "%s%s" % (int(write_size), write_unit))

    def _test_disk_almost_full_size(self):
        disk_left = self.params.get('disk_left')

        cmd = 'df -h'
        if self.ceph_node:
            cmd = self.cmd + cmd

        result_size = self.session.run(cmd)
        disk_data, disk_unit, used_disk_data, used_disk_unit = \
            self.get_volume(result_size)

        disk_left_data = disk_left[0:len(disk_left)-1]
        disk_left_unit = \
            disk_left[len(disk_left) - 1: len(disk_left)]

        if disk_unit == used_disk_unit == disk_left_unit:
            write_size = disk_data - used_disk_data - float(disk_left_data)
            write_unit = disk_unit
        else:
            # Convert volume size to byte
            disk_size = convert_to_byte(disk_unit, disk_data)
            used_disk_size = convert_to_byte(used_disk_unit,
                                                  used_disk_data)
            disk_left_byte = convert_to_byte(disk_left_unit,
                                             float(disk_left_data))

            # Compute the size of writed file
            write_size_byte = disk_size - disk_left_byte - used_disk_size
            write_size, write_unit = convert_to_right_unit(write_size_byte)

        self.dd_write(self.mount_point, self.filename,
                      "%s%s" % (int(write_size), write_unit))

    def _test_osd_down(self):
        cmd = "/etc/init.d/ceph -a stop %s" % self.osd_num
        if self.ceph_node:
            cmd = self.cmd + cmd
        result = self.session.run(cmd)

        if result.exit_status == 0:
            LOG.info("Stop %s successfully." % self.osd_num)
        else:
            LOG.error("Stop %s failed." % self.osd_num)


if __name__ == '__main__':
    session = RemoteRunner(client='ssh', host="10.100.4.161", username="root",
                           port="22", password="123456")
    params = {"io_fault_test_name": "disk_down",
              "io_fault_mount_point": "/mnt/", "partition": "/dev/sdb3",
              "fio_filename": "/mnt/test/test_fio_write",
              "fio_version": "fio-2.1.10.tar.gz", "warning_base": "1",
              "disk_left": "27G", "fio_bs": "100M", "fio_numjobs": "2"}

    cf = IOFault(session, params)
    cf.setup()
    cf.test()
    cf.teardown()

    '''session = RemoteRunner(client='ssh', host="10.100.64.36", username="root",
                           port="22", password="passw0rd")
    params = {"io_fault_test_name": "disk_almost_full_size",
              "ceph_node": "node-3", "usage_warning_in_percentage": "36",
              "disk_left": "61G", "osd_num": "osd.0"}

    cf = IOFaultCeph(session, params)
    cf.setup()
    cf.test()
    cf.teardown()'''
