import os
import json
import time
import logging
import random
from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest.openstack import compute
from cloudtest.openstack import volume
from cloudtest.tests.nfv import test_utils
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


LOG = logging.getLogger('avocado.test')


class DiskPerformance(NFVTestBase):
    def __init__(self, params, env):
        super(DiskPerformance, self).__init__(params, env)
        self.params = params
        self.compute_utils = compute.Compute(self.params)
        self.volume_utils = volume.Volume(self.params)
        self.hypervisors_client = self.compute_utils.novaclient.hypervisors
        self.env = env

    def setup(self):
        self.volume_name = 'cloudtest_' + \
                    utils_misc.generate_random_string(6)
        self.volume_id = None

        LOG.info("To get flavor %s" % self.params["flavor_name"])
        self.flavor_detail = self.get_flavor_detail()
        self.flavor = self.get_flavor(self.params["flavor_name"],
                                      int(self.flavor_detail["mem"]),
                                      int(self.flavor_detail["cpu"]),
                                      int(self.flavor_detail["disk"]))
        LOG.info("Flavor %s id is %s" % (self.params["flavor_name"],
                                          self.flavor.id))
        if self.flavor.id is None:
            raise exceptions.TestSetupFail("Failed to get flavor %s" %
                            self.params["flavor_name"])
        if self.params.has_key("create_vm"):
            self.vmname = 'cloudtest_' + \
                    utils_misc.generate_random_string(6)
            LOG.info("Creating a new vm %s now" % self.vmname)
            self.add_to_cfg(self.params["result_file"], "vmname",
                            self.vmname)
            vm = self.compute_utils.create_vm(vm_name=self.vmname,
                                     image_name=self.params["image_name"],
                                     flavor_name=self.params["flavor_name"],
                                     network_name=self.params["network_name"],
                                     injected_key=None, sec_group=None,
                                     availability_zone=None)
            vm_created = self.compute_utils.wait_for_vm_active(vm, 1,
                                    int(self.params["vmtobeactive_timeout"]))
            if vm_created == False:
                raise exceptions.TestSetupFail("Created VM %s timeout" %
                                               self.vmname)
            self.compute_utils.assign_floating_ip_to_vm(vm)
            ipaddr = self.compute_utils.get_vm_ipaddr(self.vmname)
            self.volume_id = self.volume_utils.create_volume(self.volume_name,
                                               int(self.flavor_detail["disk"]))
            LOG.info("Created a new volume %s" % self.volume_name)
            self.add_to_cfg(self.params["result_file"], "volume_id",
                            self.volume_id)
            time.sleep(5)
            LOG.info("Try to make a session on FIP %s for vm"
                     % ipaddr["floating"])
            try:
                self.session_vm = test_utils.get_host_session(self.params,
                                                              'instance',
                                                              ipaddr["floating"])
            except Exception:
                params = self.params
                params["image_ssh_auth_method"] = "keypair"
                self.session_vm = test_utils.get_host_session(self.params,
                                                              'instance',
                                                              ipaddr["floating"])
            self.compute_utils.attach_volume(vm.id, self.volume_id)
            time.sleep(10)
            if not self.check_if_vm_has_device(self.session_vm,
                                   self.params["fio_devname_vm"]):
                raise exceptions.TestSetupFail(
                    "Failed to prepare new disk for FIO")
            self.prepare_fiodisk(self.session_vm, self.params["fio_devname_vm"],
                                 self.params["fio_diskdir_vm"])
        else:
            self.vmname = self.get_cfg_item(self.params["result_file"],
                                            "vmname")
            if self.vmname is None:
                raise exceptions.TestSetupFail("Failed to get vm name")
            LOG.info("Try to get the vm %s" % self.vmname)
            vm = self.compute_utils.find_vm_from_name(self.vmname)
            ipaddr = self.compute_utils.get_vm_ipaddr(self.vmname)
            LOG.info("Try to make a session on FIP %s for vm"
                     % ipaddr["floating"])
            try:
                self.session_vm = test_utils.get_host_session(self.params,
                                                              'instance',
                                                              ipaddr["floating"])
            except Exception:
                params = self.params
                params["image_ssh_auth_method"] = "keypair"
                params["image_ssh_username"] = self.params["image_ssh_username_alt"]
                try:
                    self.session_vm = test_utils.get_host_session(self.params,
                                                              'instance',
                                                              ipaddr["floating"])
                except Exception:
                    raise exceptions.TestSetupFail(
                        "Failed to set a session to VM")
            if not self.check_if_vm_has_device(self.session_vm,
                                   self.params["fio_devname_vm"]):
                raise exceptions.TestSetupFail(
                    "Failed to prepare new disk for FIO")
            cmd = ("[ -d %s ]" % self.params["fio_diskdir_vm"])
            run_result = self.session_vm.run(cmd)
            if run_result.exit_status != 0:
                raise exceptions.TestSetupFail(
                    "Failed to prepare new disk for FIO")

    def get_randomindex(self, _range, _count):
        _ranges = range(_range)
        random.shuffle(_ranges)
        return [_ranges[0], _ranges[1]]

    def get_flavor(self, flavor_name, ram, vcpus, disk):
        try:
            flavor = self.compute_utils.flavor_client.find(name=flavor_name)
        except:
            flavor = self.compute_utils.create_flavor(name=flavor_name,
                                       ram=ram, vcpus=vcpus, disk=disk)
        return flavor

    def get_flavor_detail(self):
        _flavor = self.params["flavor_name"].split("-")
        flavor_detail = {"cpu": _flavor[0][3:len(_flavor[0])],
                  "mem": _flavor[1][3:len(_flavor[1])],
                  "disk": _flavor[2][4:len(_flavor[2])]}
        return flavor_detail

    def get_cfg_all(self, filename):
        try:
            cfgfile = open(filename)
            cfgdict = json.load(cfgfile)
            cfgfile.close()
            return cfgdict
        except Exception:
            pass

    def get_cfg_item(self, filename, _key):
        try:
            cfgfile = open(filename)
            cfgdict = json.load(cfgfile)
            cfgfile.close()
            if cfgdict.has_key(_key):
                return cfgdict[_key]
        except Exception:
            pass

    def add_to_cfg(self, filename, _key, _value):
        cfgdict = self.get_cfg_all(filename)
        if cfgdict is None:
            cfgdict = {}
        cfgfile = open(filename, "w")
        cfgdict[_key]=_value
        json.dump(cfgdict, cfgfile, indent=4, sort_keys=True)
        cfgfile.close()

    def remove_from_cfg(self, filename, _key):
        cfgdict = self.get_cfg_all(filename)
        if not cfgdict is None:
            cfgfile = open(filename, "w")
            del cfgdict[_key]
            json.dump(cfgdict, cfgfile, indent=4, sort_keys=True)
            cfgfile.close()

    def get_fio_result(self, filename):
        iops = []
        cfgdict = self.get_cfg_all(filename)
        if not cfgdict is None:
            for k, v in cfgdict.items():
                if k != "vmname" and k != "volume_id":
                    _v = v.split(",")
                    __v = _v[2].split("=")
                    iops.append({k:__v[1]})
            return iops

    def run_fio(self, session, fs, bs, fiopath, mix):
        LOG.info("Run fio with parameters:"
                 "I/O mode: readwrite,  Block size: %2s, File size: %3s, "
                 "Numjobs: 1, Job name: test, Percentage(read/write): %2s%%" %
                (bs, fs, mix))
        cmd = ("sudo %s/fio -filename=%s/fio.data -rw=readwrite -bs=%s -size=%s \
               -numjobs=1 -name=test -rwmixread=%s | grep -E 'read :|write:'"
               % (fiopath, self.params["fio_diskdir_vm"], bs, fs, mix))
        run_result = session.run(cmd, int(self.params["fio_timeout"]))
        if run_result.exit_status == 0:
            return run_result.stdout

    def get_iodetail(self, kstr):
        k = kstr.split("_")
        return k[0], k[1], k[2], k[3], k[4]

    def compare_io_result(self, iops):
        hit_flag = [False] * len(iops)
        idx_i = 0
        LOG.info("============= Comparsion results ============")
        for _iops in iops:
            for (k, v) in _iops.items():
                cpu, fs, bs, percent, iotype = self.get_iodetail(k)
                idx_j = 0
                for __iops in iops:
                    for (_k, _v) in __iops.items():
                        _cpu, _fs, _bs, _percent, _iotype = self.get_iodetail(
                                                            _k)
                        if cpu == _cpu and fs != _fs and bs == _bs and \
                           percent == _percent and iotype == _iotype:
                            if (hit_flag[idx_i] is False and
                                hit_flag[idx_j] is False):
                                hit_flag[idx_i] = True
                                hit_flag[idx_j] = True
                                LOG.info("CPU core:%2s, "
                                         "Block size:%2s, "
                                         "Percentage(read/write):%2s%%, "
                                         "IO type:%5s, "
                                         "(File size:%3s / File size:%3s) "
                                         "= (%s / %s) = %s" %
                                         (cpu, bs, percent, iotype, fs, _fs,
                                          v, _v, float(v)/float(_v)))
                    idx_j += 1
            idx_i += 1
        hit_flag = [False] * len(iops)
        idx_i = 0
        LOG.info("=============================================")
        for _iops in iops:
            for (k, v) in _iops.items():
                cpu, fs, bs, percent, iotype = self.get_iodetail(k)
                idx_j = 0
                for __iops in iops:
                    for (_k, _v) in __iops.items():
                        _cpu, _fs, _bs, _percent, _iotype = self.get_iodetail(
                                                                 _k)
                        if cpu != _cpu and fs == _fs and bs == _bs and \
                           percent == _percent and iotype == _iotype:
                            if (hit_flag[idx_i] is False and
                                hit_flag[idx_j] is False):
                                hit_flag[idx_i] = True
                                hit_flag[idx_j] = True
                                LOG.info("Block size:%2s, "
                                         "Percentage(read/write):%2s%%, "
                                         "IO type:%5s, "
                                         "File size:%3s, "
                                         "(CPU core:%2s / CPU core:%2s) "
                                         "= (%s / %s) = %s"
                                         % (bs, percent, iotype, fs, cpu, _cpu,
                                            v, _v, float(v)/float(_v)))
                    idx_j += 1
            idx_i += 1
        LOG.info("=============================================")

    def check_if_vm_has_device(self, session, devname):
        cmd = ("sudo fdisk -l | grep %s | wc -l" % devname)
        try:
            run_result = session.run(cmd)
            if run_result.stdout[0] == "1":
                return True
            else:
                return False
        except:
            return False

    def prepare_fiodisk(self, session, devname, dirname):
        cmd_1 = ("sudo mkfs.ext3 %s" % devname)
        cmd_2 = ("sudo mkdir -p %s" % dirname)
        cmd_3 = ("sudo mount %s %s" % (devname, dirname))
        run_result_1 = session.run(cmd_1)
        if run_result_1.exit_status == 0:
            session.run(cmd_2)
            run_result_3 = session.run(cmd_3)
            if run_result_3.exit_status != 0:
                raise exceptions.TestError("Failed to mount %s to %s"
                                       % (devname, dirname))
        else:
            raise exceptions.TestError("Failed to make file system to %s"
                                       % devname)

    def test(self):
        results = []
        for percents in ["75", "50"]:
            run_result = self.run_fio(self.session_vm, self.params["fs"],
                                      self.params["bs"],
                                      self.params["fio_workdir_vm"],
                                      percents)
            _results = run_result.split("\n")
            for rst in _results:
                iotype = None
                if rst.find("read") >= 0:
                    iotype = "read"
                if rst.find("write") >= 0:
                    iotype = "write"
                if not iotype is None:
                    io_option = "%s_%s_%s_%s_%s" % (self.flavor_detail["cpu"],
                        self.params["fs"], self.params["bs"],
                        percents, iotype)
                    self.add_to_cfg(self.params["result_file"], io_option, rst)
                    LOG.info("Result %s" % (rst))
                    _rst = rst.split(",")
                    __rst = _rst[2].split("=")
                    threshold = self.params.get("iops_threshold_%s_%s" %
                                                    (iotype, percents))
                    results.append([{"percents": percents}, {"iotype": iotype},
                                {"result": __rst[1]}, {"threshold": threshold}])
        if self.params["check_everyone"] == "true":
            for r in results:
                if (int(r[2]["result"]) < int(r[3]["threshold"])):
                    raise exceptions.TestFail(
                        "The result is %s that less than the threshold"
                        " %s" % (r[2]["result"], r[3]["threshold"]))
                else:
                    LOG.info("%s%% %s IOPS: result %s > threshold %s" % (
                        r[0]["percents"], r[1]["iotype"],
                        r[2]["result"], r[3]["threshold"]))

        if self.params.has_key("result_compare"):
            if self.params["result_compare"] == "true":
                iops = self.get_fio_result(self.params["result_file"])
                if iops is None:
                    raise exceptions.TestError("Failed to get iops.")
                self.compare_io_result(iops)

    def teardown(self):
        if self.params.get("flavor_remove", "false") == "true":
            self.register_cleanup(self.flavor)
        if self.params.get("delete_vm", "false") == "true":
            self.volume_id = self.get_cfg_item(self.params["result_file"],
                                               "volume_id")
            vm = self.compute_utils.find_vm_from_name(self.vmname)
            self.compute_utils.detach_volume(vm.id, self.volume_id)
            self.register_cleanup(resource=self.volume_id, res_type='volume')
            self.register_cleanup(vm)
            self.remove_from_cfg(self.params["result_file"], "volume_id")
            self.remove_from_cfg(self.params["result_file"], "vmname")
        if self.params.get("result_cleanup", "false") == "true":
            os.remove(self.params["result_file"])
        super(DiskPerformance, self).teardown()

