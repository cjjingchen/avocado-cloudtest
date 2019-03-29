import os
import re
import yaml
import logging
import StringIO

from avocado.core.settings import settings
from avocado.utils import process
from cloudtest import cartesian_config
from avocado.core.exceptions import TestError, HealthCheckFail
from cloudtest import remote
from cloudtest import data_dir
from cloudtest import utils_misc


class HealthCheck(object):
    """
    health check for nodes
    """

    def __init__(self, node, params, username="root",
                 is_raise_health_check_excp=True,
                 is_debug=False):
        self.host_ip = node.ip
        if "controller" in node.role:
            self.noderole = "controller"
        if "compute" in node.role:
            self.noderole = "compute"
            if params.has_key('health_check_cluster_status'):
                params['health_check_cluster_status'] = "false"
        self.failed_test = 0
        self.logger = logging.getLogger("avocado.test")
        if is_debug:
            self.logger = logging.getLogger()
            self.logger.setLevel(logging.DEBUG)
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        self.runner = remote.RemoteRunner(host=self.host_ip,
                                          username=username,
                                          use_key=True,
                                          timeout=10)

        self.raise_health_check_excp = is_raise_health_check_excp
        self.result = {}
        try:
            self.content = yaml.load(
                file(os.path.join(data_dir.CLOUDTEST_CONFIG_DIR,
                                  "health_check.yaml"), "r"))
        except yaml.YAMLError, yaml_err:
            self.logger.info(
                "Load health check yaml file failed: %s" % yaml_err.message)
            if self.raise_health_check_excp:
                raise TestError(
                    "Load health check yaml file failed: %s" % yaml_err.message)
            else:
                self.logger.error(
                    "Load health check yaml file failed: %s" % yaml_err.message)
        self.cpu_threshold = \
            self.content[0]["health_check"]["usage_should_lower_than"]["cpu"]
        self.memory_threshold = \
            self.content[0]["health_check"]["usage_should_lower_than"]["memory"]
        self.disk_threshold = \
            self.content[0]["health_check"]["usage_should_lower_than"]["disk"]
        self.ceph_threshold = \
            self.content[0]["health_check"]["usage_should_lower_than"]["ceph"]
        self.process_list = self._get_process_list()
        self.service_dict = self._get_services_dict()

        self.params = params
        self.hc_cpu = self._convert_to_bool(
            self.params.get('health_check_cpu'))
        self.hc_memory = self._convert_to_bool(
            self.params.get('health_check_memory'))
        self.hc_disk = self._convert_to_bool(
            self.params.get('health_check_disk'))
        self.hc_ceph = self._convert_to_bool(
            self.params.get('health_check_ceph'))
        self.hc_process = self._convert_to_bool(
            self.params.get('health_check_process'))
        self.hc_vm_count = self._convert_to_bool(
            self.params.get('health_check_vm_count'))
        self.hc_service_log = self._convert_to_bool(
            self.params.get('health_check_service_log'))
        self.hc_service = self._convert_to_bool(
            self.params.get('health_check_service'))
        self.rabbitmq_cluster_status = self._convert_to_bool(
            self.params.get('health_check_cluster_status'))
        self.hc_compute_node_service = self._convert_to_bool(
            self.params.get('health_check_compute_node_status'))
        self.hc_ceph_level = self.params.get('ceph_health_check_level')

    def _convert_to_bool(self, str_item):
        if str_item and str_item.lower() == "true":
            return True
        else:
            return False

    def _get_process_list(self):
        process_list = []
        for processes in self.content[0]["health_check"][
            "process_should_alive"].values():
            for process in processes:
                process_list.append(process["process"]["name"])
        return process_list

    def _get_services_dict(self):
        services_dict = {}
        for services in self.content[0]["health_check"][
            "service_status_check"][self.noderole].values():
            for service in services:
                services_dict[service["service"]["name"]] = "running"
        return services_dict

    def _get_cpu_useage(self):
        cpu_compile = re.compile("^\%Cpu\(s\):.*,\s+(.*)\s+id,")
        cpu_usage = 0.0
        result = self.runner.run("top -bn 1 -c", internal_timeout=1)
        reader = StringIO.StringIO(result.stdout)
        for item in reader:
            cpu_search = cpu_compile.search(item)
            if cpu_search is not None:
                cpu_usage = round(100.0 - float(cpu_search.group(1)), 1)
                break
        self.logger.info("Current cpu usage is %.1f%%" % cpu_usage)
        if cpu_usage - self.cpu_threshold < 0:
            return [True, cpu_usage]
        else:
            self.logger.error("CPU usage exceed threshold")
            self.failed_test += 1
            return [False, cpu_usage]

    def _get_memory_usage(self):
        memory_usage = 0.0
        total_memory = None
        free_memory = None
        result = self.runner.run("cat /proc/meminfo")
        reader = StringIO.StringIO(result.stdout)
        for item in reader:
            total_search = re.search("^MemTotal:\s+(\d+)\s+kB", item)
            free_search = re.search("^MemFree:\s+(\d+)\s+kB", item)
            if total_search is not None:
                total_memory = float(total_search.group(1))
            if free_search is not None:
                free_memory = float(free_search.group(1))
            if total_memory is not None and free_memory is not None:
                memory_usage = round(
                    (total_memory - free_memory) / total_memory * 100, 1)
                break
        self.logger.info("Current memory usage is %.1f%%" % memory_usage)
        if memory_usage - self.memory_threshold < 0:
            return [True, memory_usage]
        else:
            self.logger.error("Memory usage exceed threshold")
            self.failed_test += 1
            return [False, memory_usage]

    def _get_disk_usage(self, mount_point):
        result = self.runner.run("df -h %s" % mount_point)
        disk_usage = re.findall(r"\b([\d.]+)\b",
                                result.stdout, re.M | re.I)[0]
        disk_usage = float(disk_usage)
        self.logger.info("Current root disk usage is %.1f%%" % disk_usage)
        if disk_usage - self.disk_threshold < 0:
            return [True, disk_usage]
        else:
            self.logger.error(
                "Mount point %s disk usage exceed threshold" % mount_point)
            self.failed_test += 1
            return [False, disk_usage]

    def _get_ceph_status(self):
        try:
            result = self.runner.run("ceph -s")
            ceph_status = re.findall(r"health (.*)", result.stdout)
        except Exception, e:
            self.logger.info("No ceph found")
            self.logger.info(e)
            return [True, "NO CEPH"]

        warn_list = ["WARN", "ERR"]
        err_list = ["ERR"]
        if ceph_status[0][7:] in eval(self.hc_ceph_level):
            self.logger.error("Ceph status : %s, status check failed" %
                              ceph_status[0])
            self.failed_test += 1
            return [False, ceph_status[0]]
        else:
            self.logger.info("Ceph status : %s" % ceph_status[0])
            return [True, ceph_status[0]]

    def _get_process_info(self, process_name):
        pid_list = []
        result = self.runner.run(
            "ps aux | grep %s | grep -v grep | awk {'print $2,$12'}"
            % process_name)
        reader = StringIO.StringIO(result.stdout)
        for item in reader:
            item_list = item.split()
            if item_list[1].endswith(process_name):
                pid_list.append(item_list[0])
        if len(pid_list) == 0:
            self.logger.error("Can not find process: %s " % process_name)
            self.failed_test += 1
        else:
            for pid in pid_list:
                if not self._pid_is_alive(pid):
                    self.logger.error(
                        "%s process group has zombie process, pid is %s" % (
                            process_name, pid))
                    self.failed_test += 1
        return {process_name: len(pid_list)}

    def _get_multiple_processes_info(self):
        result = {}
        for process in self.process_list:
            result.update(self._get_process_info(process))
        return result

    def _pid_is_alive(self, pid):
        path = '/proc/%s/stat' % pid
        result = self.runner.run("test -f %s && echo OK" % path)
        if not result.stdout.strip().endswith("OK"):
            return False
        result = self.runner.run("head -1 %s" % path)
        return result.stdout.split()[2] != 'Z'

    def _get_vm_info(self):
        vm_list = []
        try:
            result = self.runner.run("virsh list")
        except:
            self.logger.info("Not a compute node")
            return vm_list
        reader = StringIO.StringIO(result.stdout)
        for item in reader:
            tmp_list = item.split()
            if len(tmp_list) == 0 or tmp_list[0].lower() == "id" or \
                            tmp_list[0].find("-") != -1:
                continue
            else:
                vm_list.append(tmp_list[0])
        return vm_list

    def _log_filter(self, component, service_name, keyword_list):
        error_info = {}
        log_file_path = os.path.join("/var/log", component,
                                     service_name + ".log")
        error_found = False
        for keyword in keyword_list:
            command = 'tail -n 500 %s | grep -n "%s"' % (log_file_path, keyword)
            try:
                result = self.runner.run(command, ignore_status=True)
                if len(result.stdout.strip()) != 0:
                    error_found = True
                    break
            except Exception, e:
                self.logger.info("Error happen when filter log")
                self.logger.info(e)
        if error_found:
            self.logger.error(
                "Error found in service %s log file" % service_name)
            self.failed_test += 1
        error_info[service_name] = not error_found
        return error_info

    def _filter_all_service_log(self):
        filter_result = {}
        error_string_dict = self.content[0]["health_check"][
            "log_should_not_contain_string"]
        for component in error_string_dict.keys():
            for service_name in error_string_dict[component].keys():
                filter_result.update(
                    self._log_filter(component, service_name,
                                     error_string_dict[component][
                                         service_name]))
        return filter_result

    def _check_service_status(self, service_name, service_status):
        check_result = {}
        command = ("systemctl status %s|grep \"Active:\"|awk '{print $2\" \"$3}'"
                  % service_name)
        result = self.runner.run(command)
        std_out_result = result.stdout.strip().lower()
        if len(std_out_result) <= 0:
            self.logger.info(
                "service %s : do not exist, skip checking" % service_name)
            check_result[service_name] = True
        elif (len(std_out_result) > 0 and
              service_status in std_out_result.split(" ")[1]):
            check_result[service_name] = True
            self.logger.info("service %s : %s" %
                             (service_name, std_out_result))
        else:
            check_result[service_name] = False
            self.logger.error("Service %s : %s, status check failed" %
                              (service_name, std_out_result))
            self.failed_test += 1
        return check_result

    def _check_all_service_status(self):
        check_results = {}
        for service_name in self.service_dict.keys():
            check_results.update(self._check_service_status(service_name,
                                                            self.service_dict[
                                                                service_name]))
        return check_results

    def _check_rabbitmq_cluster_status(self):
        command = "rabbitmqctl cluster_status"
        try:
            result = self.runner.run(command)
        except Exception, e:
            self.logger.info(e)
            return False
        pat_total = 'nodes,\[{disc,\[(.*)\]}\]}'
        total_nodes = re.findall(pat_total, result.stdout)[0].split(',')
        pat_running = 'running_nodes,\[(.*)\]}'
        running_nodes = re.findall(pat_running, result.stdout)[0].split(',')
        self.logger.info("Running nodes list is %s" % running_nodes)
        down_nodes = []
        if len(total_nodes) == len(running_nodes):
            return True
        else:
            for node in total_nodes:
                if node not in running_nodes:
                    down_nodes.append(node)
            self.logger.error("Nodes %s are down!" % down_nodes)
            return False

    def _check_compute_node_status(self):
        command = "nova hypervisor-list | awk -F '|' '/domain.tld/ {print $4}'"
        result = process.run(command, shell=True, verbose=False)
        if result.exit_status != 0:
            self.logger.error("Failed to execute command %s: %s" %
                              (command, result.stderr))
        reader = StringIO.StringIO(result.stdout).read()
        for state in reader.splitlines():
            if 'down' in state:
                return False
        return True

    def get_health_status(self):
        self.logger.info("=" * 50)
        self.logger.info("start health check in host: %s" % self.host_ip)
        try:
            if self.hc_cpu:
                self.result["cpu_usage"] = self._get_cpu_useage()
            if self.hc_memory:
                self.result["memory_usage"] = self._get_memory_usage()
            if self.hc_disk:
                self.result["disk_usage"] = self._get_disk_usage("/")
            if self.hc_ceph:
                self.result["ceph_status"] = self._get_ceph_status()
            if self.hc_process:
                self.result[
                    "process_info"] = self._get_multiple_processes_info()
            if self.hc_vm_count:
                self.result["vm_list"] = self._get_vm_info()
            if self.hc_service_log:
                self.result[
                    "service_log_filter"] = self._filter_all_service_log()
            if self.hc_service:
                self.result["service_info"] = self._check_all_service_status()
            if self.rabbitmq_cluster_status:
                self.result["rabbitmq_cluster_status"] = \
                    self._check_rabbitmq_cluster_status()
            if self.hc_compute_node_service:
                self.result[
                    "compute_node_status"] = self._check_compute_node_status()

            if self.failed_test > 0 and self.raise_health_check_excp:
                raise HealthCheckFail("health check failed")

        finally:
            self.logger.info("Health check result:")
            self.logger.info(self.result)
            self.logger.info("finish health check in host: %s" % self.host_ip)
            self.logger.info("=" * 50)


if __name__ == "__main__":
    parser = cartesian_config.Parser()
    cfg = os.path.join(settings.get_value('datadir.paths',
                                          'base_dir'), 'config/tests.cfg')
    parser.parse_file(cfg)
    dicts = parser.get_dicts()
    params = {"health_check_cpu": "false",
              "health_check_memory": "false",
              "health_check_disk": "false",
              "health_check_ceph": "true",
              "health_check_process": "false",
              "health_check_vm_count": "false",
              "health_check_service_log": "false",
              "health_check_service": "false",
              "health_check_cluster_status": "false",
              "health_check_compute_node_status": "false"
              }
    # params = None
    for tmp_params in (_ for _ in dicts):
        if 'health_check' in tmp_params.get('ct_type'):
            params = tmp_params
            break
    utils_misc.set_openstack_environment()
    health_check = HealthCheck('192.168.50.3', params, username='root',
                               is_raise_health_check_excp=True,
                               is_debug=True)
    health_check.get_health_status()
