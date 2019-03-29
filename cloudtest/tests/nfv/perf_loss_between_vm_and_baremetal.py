#!/usr/bin/env python
# coding=utf-8

import os
import time
import logging
import cloudtest.remote
from cloudtest import utils_misc
from avocado.core import exceptions
from avocado.utils import process
from cloudtest.openstack import compute
from cloudtest.openstack import volume
from cloudtest.remote import RemoteRunner
from cloudtest.tests.nfv import test_utils
from cloudtest.tests.nfv.nfv_test_base import NFVTestBase


LOG = logging.getLogger('avocado.test')


class PerfLossBetweenVmPhysic(NFVTestBase):
    def __init__(self, params, env):
        super(PerfLossBetweenVmPhysic, self).__init__(params, env)
        self.compute_utils = compute.Compute(self.params)
        self.volume_utils = volume.Volume(self.params)
        self.hypervisors_client = self.compute_utils.novaclient.hypervisors

    def setup(self):
        self.vm_name = 'cloudtest_' + utils_misc.generate_random_string(6)
        self.volume_name = 'cloudtest_' + \
                           utils_misc.generate_random_string(6)
        self.aggregate_name = "cloudtest_aggregate_" + \
                              utils_misc.generate_random_string(6)
        self.flavor_name = self.params["flavor_name"]
        self.speccpu_workdir_vm = self.params["speccpu_workdir_vm"]
        self.speccpu_workdir_node = self.params["speccpu_workdir_node"]
        self.stream_workdir_vm = self.params["stream_workdir_vm"]
        self.stream_workdir_node = self.params["stream_workdir_node"]
        self.fio_workdir_vm = self.params["fio_workdir_vm"]
        self.fio_workdir_node = self.params["fio_workdir_node"]
        self.pkg_workdir = self.params["pkg_workdir"]
        self.speccpu_pkg = self.params["cpu_pkg_for_node"]
        self.stream_pkg = self.params["stream_pkg_for_node"]
        self.fio_pkg = self.params["fio_pkg_for_node"]
        self.workdir_node = "/root/pkg"
        self.vmtobeactive_timeout = int(self.params["vmtobeactive_timeout"])
        self.session_timeout = int(self.params["session_timeout"])
        self.speccpu_timeout = int(self.params["speccpu_timeout"])
        self.stream_timeout = int(self.params["stream_timeout"])
        self.fio_timeout = int(self.params["fio_timeout"])
        self.computenode_name = self.params["computenode"]
        self.computenode_username = self.params["openstack_ssh_username"]
        self.computenode_password = self.params["openstack_ssh_password"]
        self.times = int(self.params["times"])
        self.image_sizeingb = 1

        self.cleanup_aggregate = False
        self.cleanup_aggregate_host = False
        self.cleanup_ovsconfig = False
        self.cleanup_reboot = False
        self.cleanup_grub = False
        self.cleanup_cpucore = False
        self.cleanup_rbdimage = False

        self.volume_id = None
        self.vm = None
        self.ipaddr = None
        self.cpucores = None
        self.rbdimagename = None
        self.availability_zone = None
        self.flavor.id = None
        self.computenode_ip = None
        self.aggregate = None
        self.ovs_config_orig = None
        pkg_dir_node = [
            {"dir": self.stream_workdir_node, "pkg": self.stream_pkg},
            {"dir": self.fio_workdir_node, "pkg": self.fio_pkg},
            {"dir": self.speccpu_workdir_node, "pkg": self.speccpu_pkg}]

        host_zone = self.compute_utils.get_host_by_name(
            host_name=self.computenode_name).zone
        self.availability_zone='%s:%s' % (host_zone, self.computenode_name)
        self.computenode_ip = self.get_computenode_ip(self.computenode_name)
        LOG.info("Compute node ip:%s" % self.computenode_ip)
        LOG.info("Compute node name:%s" % self.computenode_name)
        session_node = self.get_session_computenode(self.computenode_ip)

        self.prepare_3rd_tools(session_node, self.workdir_node,
                         self.pkg_workdir, pkg_dir_node, self.computenode_ip)
        metadata = {"cpu_policy": "dedicated"}
        flavor_detail = self.get_flavor_detail(self.flavor_name)
        self.flavor = self.get_flavor(self.flavor_name,
                                      int(flavor_detail["mem"]),
                                      int(flavor_detail["cpu"]),
                                      int(flavor_detail["disk"]))
        LOG.debug("To get or create flavor %s id is %s" % (self.flavor_name,
                                                       self.flavor.id))
        if self.flavor.id is None:
            raise exceptions.TestSetupFail("Failed to get flavor %s" %
                                       self.flavor_name)
        self.register_cleanup(self.flavor)
        flavor = self.compute_utils.flavor_client.find(name=self.flavor_name)
        flavor.set_keys(metadata)
        LOG.debug("Create a new aggregate %s" % self.aggregate_name)
        aggregates = self.compute_utils.novaclient.aggregates.list()
        LOG.debug("Aggregate created is:%s" % aggregates)
        for ag in aggregates:
            for host in ag.hosts:
                if host == self.computenode_name:
                    raise exceptions.TestSetupFail(
                        "Failed to add host %s to a new aggregate" %
                        self.computenode_name)
        self.aggregate = self.compute_utils.novaclient.aggregates.create(
                                      self.aggregate_name, host_zone)
        self.cleanup_aggregate = True
        self.compute_utils.novaclient.aggregates.add_host(self.aggregate,
                                                       self.computenode_name)
        self.cleanup_aggregate_host = True
        self.compute_utils.novaclient.aggregates.set_metadata(self.aggregate,
                                                              metadata)
        LOG.info("Get ovs config for recovery")
        self.ovs_config_orig = self.get_ovsconfig(session_node)

        LOG.info("Set dpdk memory and cpu mask")
        self.set_ovsconfig(session_node, self.params["dpdk_mem"],
                           self.params["cpu_mask"])
        self.cleanup_ovsconfig = True
        confdir = ['usr', 'share', 'avocado-cloudtest', 'tests', 'nfv', 'conf']
        self.confallpath = ("%s/grub.cfg_%s" % (os.path.join(*(['/'] + confdir)),
                                           self.params["computenode"]))
        LOG.debug("To check if there is a matching config file for %s" %
                 self.params["computenode"])
        cmd_1 = ("[ -f %s_orig ]" % self.confallpath)
        _run_result_1 = process.run(cmd_1, timeout=5, ignore_status=True)
        if _run_result_1.exit_status != 0:
            raise exceptions.TestSetupFail("Failed to get grub config file %s" %
                                           self.confallpath)
        LOG.debug("Copy %s_orig to %s for comparing both them" % (self.confallpath,
                                              self.params["computenode"]))
        cmd_scp_1 = ("scp %s_orig %s@%s:/tmp/" % (self.confallpath,
                                           self.computenode_username,
                                               self.computenode_ip))
        cloudtest.remote.remote_scp(cmd_scp_1, self.computenode_password)
        self.cleanup_grub = True
        LOG.debug("Comparing /boot/grub2/grub.cfg to %s_orig" % self.confallpath)
        cmd_3 = ("/usr/bin/diff /boot/grub2/grub.cfg /tmp/grub.cfg_%s_orig" %
                self.params["computenode"])
        _run_result_3 = session_node.run(cmd_3, ignore_status=True)
        if _run_result_3.exit_status != 0:
            raise exceptions.TestSetupFail(
                "The grub config file does not match %s" %
                self.computenode_name)
        LOG.debug("Backup /boot/grub2/grub.cfg on %s" %
                 self.params["computenode"])
        cmd_2 = ("/bin/cp -f /boot/grub2/grub.cfg /boot/grub2/grub.cfg.bk")
        _run_result_2 = session_node.run(cmd_2)
        if _run_result_2.exit_status != 0:
            raise exceptions.TestSetupFail(
                "Failed to backup /boot/grub2/grub.cfg")
        LOG.debug("Scp the limit config file for VM to %s" %
                 self.params["computenode"])
        cmd_scp_2 = ("scp %s_vm %s@%s:/boot/grub2/grub.cfg" % (self.confallpath,
                                           self.computenode_username,
                                               self.computenode_ip))
        cloudtest.remote.remote_scp(cmd_scp_2, self.computenode_password)
        LOG.info("Reboot %s for running VM job" % self.params["computenode"])
        self.cleanup_reboot = True
        self.reboot_computenode(session_node)
        retval = self.wait_poweron_computenode(self.computenode_ip, 80)
        LOG.debug("Return value of reboot %s: %s" %
                 (self.params["computenode"], retval))
        if retval != 0:
            raise exceptions.TestSetupFail(
                "Compute node did not reboot successfully")

    def check_speccpu(self, path, session):
        cmd = ("[ -f %s/bin/runspec ]" % path)
        run_result = session.run(cmd, ignore_status=True)
        return run_result.exit_status

    def prepare_speccpu(self, path, session, timeout):
        cmd_1 = ("echo \"sudo chown -R centos.centos %s ; \
                 sudo chmod -R a+w %s\" | tee ~/chown_speccpu2006.sh "
                 % (path, path))
        cmd_2 = ("chmod 755 ~/chown_speccpu2006.sh")
        cmd_3 = ("~/chown_speccpu2006.sh")
        run_result = session.run(cmd_1)
        if run_result.exit_status == 0 :
            run_result = session.run(cmd_2)
            if run_result.exit_status == 0 :
                run_result = session.run(cmd_3)
                if run_result.exit_status == 0 :
                    return 0
                else:
                    return 1
            else:
                return 2
        else:
            return 3

    def get_result_speccpu(self, results, times):
        if len(results) == times:
            result = {"ratio":0}
            LOG.info(" ,Ratio")
            for idx in range(times):
                LOG.info("%d,%s" % (idx, results[idx]["ratio"]))
                result["ratio"] = result["ratio"] + results[idx]["ratio"]
            result["ratio"] = result["ratio"] / times
            return result

    def get_speccpu_ratio(self, str):
        index_key = str.find("ratio=", 0)
        start_value = index_key + len("ratio=")
        end_value = str.find(",", start_value)
        return str[start_value:end_value]

    def dospeccpu(self, path, session, timeout, times, casetype):
        result = None
        results = []
        cmd_prefix = ""
        if casetype == "node":
            cmd_prefix = "taskset -c 0-9"
        cmd_4 = ("cd %s && source shrc && %s ./bin/runspec "
        "--config=%s/config/Example-linux64-amd64-gcc41.cfg "
        "--size=ref --tune=base --noreportable --iterations=%d -T base bzip"
        % (path, cmd_prefix, path, times))
        run_result = session.run(command=cmd_4, timeout=timeout)
        LOG.info("----------------Run SpecCPU----------------")
        LOG.info("%s\n" % run_result.stdout)
        if run_result.exit_status == 0 :
            start = run_result.stdout.find("The log for this run is in", 0)
            if start > 0 :
                start = start + len("The log for this run is in")
                end = run_result.stdout.find("\n", start)
                filename = run_result.stdout[start:end]
                cmd_5 = ("cat %s" % filename)
                filecontext = session.run(command=cmd_5, timeout=timeout)
                stdout = filecontext.stdout.split('\n')
                for str in stdout:
                    if str.find("ratio=", 0) > 0 :
                        ratio = self.get_speccpu_ratio(str)
                        results.append({"ratio": float(ratio)})
                result = self.get_result_speccpu(results, times)
        return result

    def check_stream(self, path, session):
        cmd = ("[ -f %s/stream.80M ]" % path)
        run_result = session.run(cmd, ignore_status=True)
        return run_result.exit_status

    def get_stream_avgtime(self, str):
        arr = (str.split(" "))
        curr = 0
        for idx in range(len(arr)):
            if ( idx != 0 ) and ( len(arr[idx]) > 0 ):
                curr += 1
                if curr == 1:
                    bestrate= arr[idx]
                if curr == 2:
                    avgtime = arr[idx]
                if curr == 3:
                    mintime = arr[idx]
                if curr == 4:
                    maxtime = arr[idx]
        return float(avgtime)

    def dostream(self, path, session, timeout, times, casetype):
        cmd_prefix = ""
        if casetype == "node":
            cmd_prefix = "taskset -c 0-9"
        cmd_2 = ("cd %s && %s ./stream.80M" % (path, cmd_prefix))
        result = None
        results = []
        for idx in range(times):
            run_result = session.run(command=cmd_2, timeout=timeout)
            LOG.info("----------------Run Stream %d/%d----------------" %
                     (idx+1, times))
            LOG.info("%s\n" % run_result.stdout)
            if run_result.exit_status == 0 :
                stdout = run_result.stdout.split('\n')
                for str in stdout:
                    if str.find("Copy:", 0) == 0:
                        copy = self.get_stream_avgtime(str)
                    if str.find("Scale:", 0) == 0:
                        scale = self.get_stream_avgtime(str)
                    if str.find("Add:", 0) == 0:
                        add = self.get_stream_avgtime(str)
                    if str.find("Triad:", 0) == 0:
                        triad = self.get_stream_avgtime(str)
                results.append({"copy": copy, "scale": scale, "add": add,
                                "triad": triad})
        result = self.get_result_stream(results, times)
        return result

    def get_result_stream(self, results, times):
        if len(results) == times:
            result = {"copy":0, "scale":0, "add":0, "triad":0}
            LOG.info(" ,Copy,Scale,Add,Triad")
            for idx in range(times):
                LOG.info("%d,%s,%s,%s,%s" % (idx, results[idx]["copy"],
                         results[idx]["scale"], results[idx]["add"],
                        results[idx]["triad"]))
                result["copy"] = result["copy"] + results[idx]["copy"]
                result["scale"] = result["scale"] + results[idx]["scale"]
                result["add"] = result["add"] + results[idx]["add"]
                result["triad"] = result["triad"] + results[idx]["triad"]
            result["copy"] = result["copy"] / times
            result["scale"] = result["scale"] / times
            result["add"] = result["add"] / times
            result["triad"] = result["triad"] / times
            return result

    def check_fio(self, path, session):
        cmd = ("[ -f %s/fio ]" % path)
        run_result = session.run(cmd, ignore_status=True)
        return run_result.exit_status

    def get_fio_iops(self, str):
        index_key = str.find("iops=", 0)
        start_value = index_key + len("iops=")
        end_value = str.find(",", start_value)
        return str[start_value:end_value]

    def dofio(self, path, session, timeout, devname, times, casetype,
              size_in_gb=None):
        goahead = True
        result = None
        results = []
        cmd_1 = ("sudo yum -y install libaio ")
        cmd_2 = ("sudo yum -y install libaio-devel ")
        if casetype == "node":
            cmd_3 = ("cd %s && sudo ./fio -group_reporting -ioengine=rbd "
                     "-clientname=admin -iodepth=128 -pool=rbd "
                     "-numjobs=1 -runtime=600 -direct=1 -rw=rw -rwmixwrite=50 "
                     "-size=%dG -bs=64k -name=randrw_test -rbdname=%s"
                     % (path, size_in_gb, devname))
        else:

            cmd_3 = ("cd %s && sudo taskset -c 0-9 ./fio -group_reporting "
                     "-ioengine=libaio -iodepth=128 "
                     "-numjobs=1 -runtime=600 -direct=1 -rw=rw -rwmixwrite=50 "
                     "-size=1G -bs=64k -name=randrw_test -filename=%s"
                     % (path, devname))
        if casetype == "vm":
            goahead = False
            run_result = session.run(command=cmd_1, timeout=timeout)
            if run_result.exit_status == 0 :
                run_result = session.run(command=cmd_2, timeout=timeout)
                if run_result.exit_status == 0 :
                    goahead = True
        if goahead == True:
            for idx in range(times):
                run_result = session.run(command=cmd_3, timeout=timeout)
                LOG.info("----------------Run FIO %d/%d----------------" %
                         (idx+1, times))
                LOG.info("%s\n" % run_result.stdout)
                if run_result.exit_status == 0 :
                    stdout = run_result.stdout.split('\n')
                    for out in stdout:
                        linestr = out.lstrip()
                        if linestr.find("read :", 0) == 0:
                            readiops = self.get_fio_iops(linestr)
                        if linestr.find("write:", 0) == 0:
                            writeiops = self.get_fio_iops(linestr)
                    results.append({"readiops": float(readiops),
                                    "writeiops": float(writeiops)})
            result = self.get_result_fio(results, times)
        return result

    def get_result_fio(self, results, times):
        if len(results) == times:
            result = {"readiops":0, "writeiops":0}
            LOG.info(",Read iops,Write iops")
            for idx in range(times):
                LOG.info("Host,%s,%s" % (results[idx]["readiops"],
                         results[idx]["writeiops"]))
                result["readiops"] = result["readiops"] + \
                        results[idx]["readiops"]
                result["writeiops"] = result["writeiops"] + \
                        results[idx]["writeiops"]
            result["readiops"] = result["readiops"] / times
            result["writeiops"] = result["writeiops"] / times
            return result

    def get_cpu_cores(self, session):
        cmd = ("cat /sys/devices/system/cpu/online")
        run_result = session.run(cmd)
        core_range = run_result.stdout[0:-1].split('-')
        core_range[0] = int(core_range[0])
        core_range[1] = int(core_range[1])
        return core_range

    def set_cpu_cores(self, cores_start, cores_end, switch, session):
        if switch == "online":
            sv = 1
        else:
            sv = 0
        curr = cores_start
        while curr <= cores_end:
            cmd = ('echo %d > /sys/devices/system/cpu/cpu%d/online |'
                   % (sv, curr))
            session.run(cmd)
            LOG.info("CPU%d %s." % (curr, switch))
            curr += 1

    def get_alldevname_vm(self, session):
        cmd = ("ls /dev/vd?")
        run_result = session.run(cmd)
        _devnames = run_result.stdout.split()
        return _devnames

    def get_devname_vm(self, dname1, dname2):
        if len(dname2) <= len(dname1):
            return
        else:
            for idx_i in dname2:
                hit = False
                for idx_j in dname1:
                    if idx_i == idx_j:
                        hit = True
                        break
                if hit == False:
                    return idx_i

    def get_newrbdimagename(self, session):
        cmd = ("rbd ls")
        while True:
            imagename = 'cloudtest_rbd_' + utils_misc.generate_random_string(6)
            run_result = session.run(cmd)
            if run_result.exit_status == 0:
                if run_result.stdout.find(imagename) == -1:
                    return imagename

    def create_fullfill_rbdimage_node(self, session, imagename, size_in_gb,
                             fio_workdir_node):
        size = int(size_in_gb) * 1024
        cmd_1 = ('rbd create rbd/%s --size %d' % (imagename, size))
        run_result = session.run(cmd_1)
        if run_result.exit_status == 0:
            cmd_2 = ("%s/fio --ioengine=rbd --clientname=admin --pool=rbd "
                     "--rw=write --bs=1024k --iodepth=16 --numjobs=1 "
                     "--direct=1 --size=%dG --rbdname=%s --name=full" %
                     (fio_workdir_node, size_in_gb, imagename))
            session.run(cmd_2)
            return True
        else:
            return False

    def remove_rbdimage_node(self, session, imagename):
        cmd = ('rbd rm rbd/%s' % imagename)
        session.run(cmd)

    def get_computenode_ip(self, computenode_name):
        hysors = self.compute_utils.get_all_hypervisors()
        for hy in hysors:
            if hy.hypervisor_hostname == computenode_name:
                return hy.host_ip

    def get_session_computenode(self, ip, usekey=False):
        if self.params.has_key("usekey_node"):
            if self.params.get("usekey_node") in "False":
                _usekey = False
            if self.params.get("usekey_node") in "True":
                _usekey = True
        else:
            _usekey = usekey
        session = RemoteRunner(client='ssh', host=ip,
                          username=self.computenode_username, port="22",
                          password=self.computenode_password,
                          use_key=_usekey,
                          timeout=self.session_timeout,
                          internal_timeout=self.session_timeout)
        return session

    def reboot_computenode(self, session):
        cmd = ("nohup /usr/sbin/shutdown -r now")
        try:
            session.run(cmd, ignore_status=True, timeout=3)
        except:
            pass

    def wait_poweron_computenode(self, ip, timeout):
        cmd = ("ls")
        es = 1
        start_time = time.time()
        while es != 0:
            try:
                session = self.get_session_computenode(ip)
                run_result = session.run(cmd, ignore_status=True, timeout=3)
                es = run_result.exit_status
            except:
                time.sleep(1)
                pass
            if (time.time() - start_time) > timeout:
                break
        return es

    def prepare_3rd_tools(self, session, workdir_node,
                          pkg_workdir, pkg_dir_node, computenode_ip):
        session.run(("mkdir -p %s" % workdir_node), ignore_status=True)
        try:
            for idx in pkg_dir_node:
                run_result = session.run(("[ -d %s ]" % idx["dir"]),
                                              ignore_status=True)
                if run_result.exit_status != 0:
                    run_result = session.run(("[ -f %s/%s ]" %
                                 (pkg_workdir, idx["pkg"])), ignore_status=True)
                    if run_result.exit_status != 0:
                        process.run("scp %s/%s root@%s:%s" % (pkg_workdir,
                                  idx["pkg"], computenode_ip, workdir_node))
                    session.run("tar zxvf %s/%s -C %s" % (workdir_node,
                                  idx["pkg"], pkg_workdir), ignore_status=True)
        except:
            raise exceptions.TestSetupFail(
                "Failed to remote copy 3rd tools to compute node")

    def get_flavor(self, flavor_name, ram, vcpus, disk):
        try:
            flavor = self.compute_utils.flavor_client.find(name=flavor_name)
        except:
            flavor = self.compute_utils.create_flavor(name=flavor_name,
                                       ram=ram, vcpus=vcpus, disk=disk)
        return flavor

    def get_flavor_detail(self, flavor_name):
        _flavor = flavor_name.split("-")
        flavor_detail = {"cpu": _flavor[0][3:len(_flavor[0])],
                  "mem": _flavor[1][3:len(_flavor[1])],
                  "disk": _flavor[2][4:len(_flavor[2])]}
        return flavor_detail

    def get_ovsconfig_fromstr(self, str):
        ovs = {}
        ovs_l = str.split(", ")
        for idx in ovs_l:
            kv = idx.split("=")
            ovs[kv[0]]=kv[1].replace("\"","")
        return ovs

    def get_ovsconfig(self, session):
        cmd_ovsconf = ("ovs-vsctl --no-wait get Open_vSwitch . other_config")
        _run_result_ovsconf = session.run(cmd_ovsconf)
        if _run_result_ovsconf.exit_status != 0:
            raise exceptions.TestSetupFail("Failed to get OVS config")
        _ovs_config_orig = self.get_ovsconfig_fromstr(
            _run_result_ovsconf.stdout[1:len(_run_result_ovsconf.stdout)-2])
        return _ovs_config_orig

    def set_ovsconfig(self, session, dpdk_mem, cpu_mask):
        LOG.info("To get OVS config original")
        ovs_config_orig = self.get_ovsconfig(session)
        LOG.info("OVS config is: %s" % ovs_config_orig)
        LOG.info("To set OVS config for memory")
        cmd_ovsmem_set = ("ovs-vsctl set Open_vSwitch . "
                          "other_config:dpdk-socket-mem=\"%s\"" %
                         dpdk_mem)
        _run_result_ovsmem_set = session.run(cmd_ovsmem_set)
        if _run_result_ovsmem_set.exit_status != 0:
            raise exceptions.TestSetupFail(
                "Failed to set OVS config for memory")
        ovs_config_mem_set = self.get_ovsconfig(session)
        LOG.info("Set mem to: %s" % ovs_config_mem_set)
        LOG.info("To set OVS config for CPU")
        cmd_ovscpu_set = ("ovs-vsctl set Open_vSwitch . "
                          "other_config:pmd-cpu-mask=\"%s\"" %
                         cpu_mask)
        _run_result_ovscpu_set = session.run(cmd_ovscpu_set)
        if _run_result_ovscpu_set.exit_status != 0:
            raise exceptions.TestSetupFail(
                "Failed to set OVS config for CPU")
        ovs_config_cpu_set = self.get_ovsconfig(session)
        LOG.info("Set cpu to: %s" % ovs_config_cpu_set)

    def recover_ovsconfig(self, session, ovs_config_orig):
        LOG.info("To recover OVS config for CPU")
        cmd_ovscpu_recover = ("ovs-vsctl set Open_vSwitch . "
                              "other_config:pmd-cpu-mask=\"%s\"" %
                              ovs_config_orig["pmd-cpu-mask"])
        _run_result_ovscpu_recover = session.run(cmd_ovscpu_recover)
        if _run_result_ovscpu_recover.exit_status != 0:
            raise exceptions.TestSetupFail(
                "Failed to recover OVS config for CPU")
        ovs_config_cpu_recover = self.get_ovsconfig(session)
        LOG.info("Recover cpu to: %s" % ovs_config_cpu_recover)
        LOG.info("To recover OVS config for memory")
        cmd_ovsmem_recover = ("ovs-vsctl set Open_vSwitch . "
                              "other_config:dpdk-socket-mem=\"%s\"" %
                              ovs_config_orig["dpdk-socket-mem"])
        _run_result_ovsmem_recover = session.run(cmd_ovsmem_recover)
        if _run_result_ovsmem_recover.exit_status != 0:
            raise exceptions.TestSetupFail(
                "Failed to recover OVS config for memory")
        ovs_config_mem_recover = self.get_ovsconfig(session)
        LOG.info("Recover mem to: %s" % ovs_config_mem_recover)

    def compare_ovs_config(self, ovs_sample, ovs_compare):
        for item in ovs_sample.keys():
            if ovs_sample[item] != ovs_compare[item]:
                return 1
        return 0

    def _test_vm(self):
        fio_device_vm = None
        result_speccpu_vm = None
        result_fio_vm = None
        result_stream_vm = None
        LOG.debug("Start testing on VM")
        LOG.debug("Create VM %s on the same RAID of the LUN" % self.vm_name)
        LOG.debug("VM is booting on %s" % self.availability_zone)
        self.vm = self.compute_utils.create_vm(vm_name=self.vm_name,
                                     image_name=self.params["image_name"],
                                     flavor_name=self.flavor_name,
                                     network_name=self.params["network_name"],
                                     injected_key=None, sec_group=None,
                                     availability_zone=self.availability_zone)
        vm_created = self.compute_utils.wait_for_vm_active(self.vm, 1,
                                                     self.vmtobeactive_timeout)
        if vm_created == False:
            raise exceptions.TestSetupFail("Failed to creating VM")
        self.register_cleanup(self.vm)
        self.compute_utils.assign_floating_ip_to_vm(self.vm)
        ipaddr = self.compute_utils.get_vm_ipaddr(self.vm_name)
        LOG.debug("Ip address:%s" % ipaddr)
        try:
            session_vm = test_utils.get_host_session(self.params, 'instance',
                                                     ipaddr["floating"])
        except:
            raise exceptions.TestSetupFail("Failed to associate FIP to VM")

        LOG.debug("Creating a new volume")
        self.volume_id = self.volume_utils.create_volume(self.volume_name, 1)
        self.register_cleanup(resource=self.volume_id, res_type='volume')
        LOG.debug("Mount the new volume to VM")
        _devnames_vm_1 = self.get_alldevname_vm(session_vm)
        self.compute_utils.attach_volume(self.vm.id, self.volume_id)
        _devnames_vm_2 = self.get_alldevname_vm(session_vm)
        LOG.debug("Get device name in VM")
        fio_device_vm = self.get_devname_vm(_devnames_vm_1, _devnames_vm_2)
        LOG.info("The New device on VM is %s" % fio_device_vm)

        casetype = "vm"
        LOG.info("Run SpecCPU testing on VM")
        exit_status = self.check_speccpu(self.speccpu_workdir_vm, session_vm)
        if exit_status == 0:
            if exit_status == 0:
                result_speccpu_vm = self.dospeccpu(self.speccpu_workdir_vm,
                      session_vm, self.speccpu_timeout, self.times, casetype)
        else:
            LOG.info("SpecCPU is not ready on VM")
        LOG.info("Run Stream testing on VM")
        exit_status = self.check_stream(self.stream_workdir_vm, session_vm)
        if exit_status == 0:
            result_stream_vm = self.dostream(self.stream_workdir_vm,
                      session_vm, self.stream_timeout, self.times, casetype)
        else:
            LOG.info("Stream is not ready on VM")
        LOG.info("Run FIO testing on VM")
        exit_status = self.check_fio(self.fio_workdir_vm, session_vm)
        if (not fio_device_vm is None) and (exit_status == 0):
            if fio_device_vm is not None:
                result_fio_vm = self.dofio(self.fio_workdir_vm, session_vm,
                       self.fio_timeout, fio_device_vm, self.times, casetype)
            else:
                LOG.info("Did not get device in VM")
        else:
            LOG.info("FIO is not ready on VM")

        return result_speccpu_vm, result_stream_vm, result_fio_vm

    def _test_node(self, computenode_ipaddr):
        result_speccpu_node = None
        result_fio_node = None
        result_stream_node = None
        LOG.debug("Start testing on node %s" % self.availability_zone)
        session_node = self.get_session_computenode(computenode_ipaddr)
        ovs_config_orig = self.get_ovsconfig(session_node)
        self.set_ovsconfig(session_node, self.params["dpdk_mem"],
                           self.params["cpu_mask"])
        LOG.debug("Create a rbd image and full fill it on compute node")
        self.rbdimagename = self.get_newrbdimagename(session_node)
        if self.rbdimagename is None:
            raise exceptions.TestSetupFail("Failed to get a new image name")
        LOG.info("New image name is %s" % self.rbdimagename)
        if not (self.create_fullfill_rbdimage_node(session_node,
                                                   self.rbdimagename,
                                                   self.image_sizeingb,
                                                   self.fio_workdir_node)):
            raise exceptions.TestSetupFail("Failed to create rbd image")
        self.cleanup_rbdimage = True
        casetype = "node"
        LOG.info("Run SpecCPU testing on node")
        exit_status = self.check_speccpu(self.speccpu_workdir_node,
                                         session_node)
        if exit_status == 0:
            result_speccpu_node = self.dospeccpu(self.speccpu_workdir_node,
                                           session_node, self.speccpu_timeout,
                           self.times, casetype)
        else:
            LOG.info("SpecCPU is not ready on node")
        LOG.info("Run Stream testing on node")
        exit_status = self.check_stream(self.stream_workdir_node, session_node)
        if exit_status == 0:
            result_stream_node = self.dostream(self.stream_workdir_node,
                                 session_node, self.stream_timeout,
                                               self.times, casetype)
        else:
            LOG.info("Stream is not ready on node")
        LOG.info("Run FIO testing on node")
        exit_status = self.check_fio(self.fio_workdir_node, session_node)
        if exit_status == 0:
            result_fio_node = self.dofio(self.fio_workdir_node, session_node,
                                         self.fio_timeout, self.rbdimagename,
                                         self.times, casetype,
                                         self.image_sizeingb)
        else:
            LOG.info("FIO is not ready on node")
        self.recover_ovsconfig(session_node, ovs_config_orig)
        return result_speccpu_node, result_stream_node, result_fio_node

    def compare_results(self, result_speccpu_vm, result_speccpu_node,
                       result_stream_node, result_stream_vm, result_fio_node,
                        result_fio_vm):
        rate_speccpu = None
        rate_stream_copy = None
        rate_stream_scale = None
        rate_stream_add = None
        rate_stream_triad = None
        rate_fio_read = None
        rate_fio_write = None
        LOG.info("=========================Result:==========================")
        LOG.info("----SpecCPU:----")
        if not result_speccpu_vm is None:
            LOG.info("VM ratio  ,%s" % (result_speccpu_vm["ratio"]))
        else:
            LOG.info("VM ratio  ,None")
        if not result_speccpu_node is None:
            LOG.info("Host ratio,%s" % (result_speccpu_node["ratio"]))
        else:
            LOG.info("Host ratio,None")
        if ((not result_speccpu_node is None) and
            (not result_speccpu_vm is None)):
            rate_speccpu = ((float(result_speccpu_node["ratio"])-
                      float(result_speccpu_vm["ratio"]))/
                     float(result_speccpu_node["ratio"]))
            LOG.info( "Ratio : (Node - VM) / Node : %s" % rate_speccpu)
        LOG.info("----Stream: ----")
        if not result_stream_vm is None:
            LOG.info("VM   ,copy:%s,scale:%s,add:%s,triad:%s" % (
                result_stream_vm["copy"], result_stream_vm["scale"],
                result_stream_vm["add"], result_stream_vm["triad"]))
        else:
            LOG.info("VM   ,None")
        if not result_stream_node is None:
            LOG.info("Host ,copy:%s,scale:%s,add:%s,triad:%s" % (
                result_stream_node["copy"], result_stream_node["scale"],
                result_stream_node["add"], result_stream_node["triad"]))
        else:
            LOG.info("Host ,None")
        if (not result_stream_node is None) and (not result_stream_vm is None):
            rate_stream_copy = ((float(result_stream_node["copy"])-
                      float(result_stream_vm["copy"]))/
                     float(result_stream_node["copy"]))
            LOG.info( "Copy : (Node - VM) / Node : %s" % rate_stream_copy)
            rate_stream_scale = ((float(result_stream_node["scale"])-
                      float(result_stream_vm["scale"]))/
                     float(result_stream_node["scale"]))
            LOG.info( "Scale : (Node - VM) / Node : %s" % rate_stream_scale)
            rate_stream_add = ((float(result_stream_node["add"])-
                      float(result_stream_vm["add"]))/
                     float(result_stream_node["add"]))
            LOG.info( "Add : (Node - VM) / Node : %s" % rate_stream_add)
            rate_stream_triad = ((float(result_stream_node["triad"])-
                      float(result_stream_vm["triad"]))/
                     float(result_stream_node["triad"]))
            LOG.info( "Triad : (Node - VM) / Node : %s" % rate_stream_triad)
        LOG.info("----FIO:    ----")
        if not result_fio_vm is None:
            LOG.info("VM   ,readiops:%s,writeiops:%s" %
                     (result_fio_vm["readiops"],
                      result_fio_vm["writeiops"]))
        else:
            LOG.info("VM   ,None")
        if not result_fio_node is None:
            LOG.info("Host ,readiops:%s,writeiops:%s" %
                    (result_fio_node["readiops"],
                    result_fio_node["writeiops"]))
        else:
            LOG.info("Host ,None")
        if (not result_fio_node is None) and (not result_fio_vm is None):
            rate_fio_read = ((float(result_fio_node["readiops"])-
                      float(result_fio_vm["readiops"]))/
                     float(result_fio_node["readiops"]))
            LOG.info( "Readiops : (Node - VM) / Node : %s" % rate_fio_read)
            rate_fio_write = ((float(result_fio_node["writeiops"])-
                      float(result_fio_vm["writeiops"]))/
                     float(result_fio_node["writeiops"]))
            LOG.info( "Writeiops : (Node - VM) / Node : %s" % rate_fio_write)
        threshold = float(self.params["threshold"])
        if rate_speccpu is None:
            raise exceptions.TestError("Failed to get SpecCPU benchmark")
        else:
            if rate_speccpu > threshold:
                raise exceptions.TestFail(
                    "SpecCPU benchmark is more than " % threshold)
        if rate_stream_copy is None:
            raise exceptions.TestError("Failed to get Stream copy benchmark")
        else:
            if rate_stream_copy > threshold:
                raise exceptions.TestFail(
                    "Stream copy benchmark is more than " % threshold)
        if rate_stream_scale is None:
            raise exceptions.TestError("Failed to get Stream scale benchmark")
        else:
            if rate_stream_scale > threshold:
                raise exceptions.TestFail(
                    "Stream scale benchmark is more than " % threshold)
        if rate_stream_add is None:
            raise exceptions.TestError("Failed to get Stream add benchmark")
        else:
            if rate_stream_add > threshold:
                raise exceptions.TestFail(
                    "Stream add benchmark is more than " % threshold)
        if rate_stream_triad is None:
            raise exceptions.TestError("Failed to get Stream triad benchmark")
        else:
            if rate_stream_triad > threshold:
                raise exceptions.TestFail(
                    "Stream triad benchmark is more than " % threshold)
        if rate_fio_read is None:
            raise exceptions.TestError("Failed to get FIO read iops benchmark")
        else:
            if rate_fio_read > threshold:
                raise exceptions.TestFail(
                    "FIO read iops benchmark is more than " % threshold)
        if rate_fio_write is None:
            raise exceptions.TestError("Failed to get FIO write iops benchmark")
        else:
            if rate_fio_write > threshold:
                raise exceptions.TestFail(
                    "FIO write iops benchmark is more than " % threshold)

    def test(self):
        rst_speccpu_vm = None
        rst_stream_vm = None
        rst_fio_vm = None
        rst_speccpu_node = None
        rst_stream_node = None
        rst_fio_node = None

        #Benchmark SpecCPU, Stream, FIO on VM
        rst_speccpu_vm, rst_stream_vm, rst_fio_vm = self._test_vm()

        LOG.debug("Scp the limit config file for node to %s" %
                 self.params["computenode"])
        cmd_scp_3 = ("scp %s_node %s@%s:/boot/grub2/grub.cfg" % (
            self.confallpath,
            self.computenode_username,
            self.computenode_ip))
        cloudtest.remote.remote_scp(cmd_scp_3, self.computenode_password)

        session_node = self.get_session_computenode(self.computenode_ip)
        LOG.info("Reboot %s for running node job" % self.params["computenode"])
        self.reboot_computenode(session_node)
        retval = self.wait_poweron_computenode(self.computenode_ip, 80)
        LOG.debug("Return value of reboot %s: %s" %
                 (self.params["computenode"], retval))
        if retval != 0:
            raise exceptions.TestSetupFail(
                "Compute node did not reboot successfully")
        session_node = self.get_session_computenode(self.computenode_ip)
        self.cpucores = self.get_cpu_cores(session_node)
        LOG.debug("%s has CPU cores : %d" % (self.params["computenode"],
                                            self.cpucores[1]))
        LOG.info("Set %s CPU cores to be offline from core-%d to core-%d" % (
                   self.params["computenode"],
                   int(self.cpucores[1]-int(self.params["cpu_offline_from"])+1),
                   self.cpucores[1]))
        self.set_cpu_cores(
            int(self.cpucores[1]-int(self.params["cpu_offline_from"])+1),
            self.cpucores[1], "offline", session_node)
        self.cleanup_cpucore = True
        LOG.debug("Start to run test on %s" % self.params["computenode"])

        #Benchmark SpecCPU, Stream, FIO on compute node
        rst_speccpu_node, rst_stream_node, rst_fio_node = self._test_node(
                                        self.computenode_ip)

        self.compare_results(rst_speccpu_vm, rst_speccpu_node, rst_stream_node,
                             rst_stream_vm, rst_fio_node, rst_fio_vm)

    def teardown(self):
        session_node = self.get_session_computenode(self.computenode_ip)
        if self.cleanup_aggregate_host == True:
            LOG.info("Remove the aggregate %s" % self.aggregate_name)
            self.compute_utils.novaclient.aggregates.remove_host(
                self.aggregate, self.computenode_name)
        if self.cleanup_aggregate == True:
            self.compute_utils.novaclient.aggregates.delete(self.aggregate)
        if self.cleanup_ovsconfig == True:
            LOG.info("Recover dpdk memory and cpu mask")
            self.recover_ovsconfig(session_node, self.ovs_config_orig)
        if self.cleanup_grub == True:
            LOG.info("Recover /boot/grub2/grub.cfg on %s" %
                     self.params["computenode"])
            cmd_4 = ("/bin/cp -f /boot/grub2/grub.cfg.bk /boot/grub2/grub.cfg")
            _run_result_4 = session_node.run(cmd_4)
            if _run_result_4.exit_status != 0:
                logging.warn(
                    "Recover /boot/grub2/grub.cfg fault")
        if self.cleanup_cpucore == True:
            LOG.info("Recover CPU core of compute node")
            self.set_cpu_cores(
                self.cpucores[1]-int(self.params["cpu_offline_from"])+1,
                self.cpucores[1], "online", session_node)
        if self.cleanup_rbdimage == True:
            LOG.info("Remove the rbd image on compute node")
            self.remove_rbdimage_node(session_node, self.rbdimagename)
        if self.cleanup_reboot == True:
            LOG.info("Reboot %s for running node job" %
                     self.params["computenode"])
            self.reboot_computenode(session_node)
            self.wait_poweron_computenode(self.computenode_ip, 80)
        super(PerfLossBetweenVmPhysic, self).teardown()



