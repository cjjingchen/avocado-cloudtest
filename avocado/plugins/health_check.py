import logging
import os
import ipaddr
from avocado.core.settings import settings
from avocado.core.plugin_interfaces import JobPost
from avocado.core import exceptions
from cloudtest import cartesian_config
from cloudtest.health_check import HealthCheck as hc_module


class HealthCheck(JobPost):
    name = 'healthcheck'
    description = 'health check on job start/end'

    def __init__(self):
        self.log = logging.getLogger("avocado.test")
        parser = cartesian_config.Parser()
        cfg = os.path.join(settings.get_value('datadir.paths',
                                              'base_dir'), 'config/tests.cfg')
        parser.parse_file(cfg)
        dicts = parser.get_dicts()
        self.ips_list = []
        self.post_check = 'false'
        execute_flag = True
        for params in (_ for _ in dicts):
            if execute_flag:
                self.params = params
                self.post_check = params.get('perform_health_check_after_job')
                host_list = params.get("host_ips")
                if host_list:
                    host_list = host_list.split(",")
                else:
                    return
                for item in host_list:
                    if item.find("/") != -1:
                        for ip_info in ipaddr.IPv4Network(item):
                            self.ips_list.append(str(ip_info))
                    elif item.find("-") != -1:
                        begin_ip, end_ip = item.split("-")
                        ip_ranges = ipaddr.summarize_address_range(
                            ipaddr.IPv4Address(begin_ip),
                            ipaddr.IPv4Address(end_ip))
                        for ip_range in ip_ranges:
                            for ip_info in ipaddr.IPv4Network(str(ip_range)):
                                self.ips_list.append(str(ip_info))
                    else:
                        self.ips_list.append(item)

                self.ips_list = sorted(set(self.ips_list),
                                       key=self.ips_list.index)
                self.log.info("All health check ip list:")
                self.log.info(self.ips_list)
                execute_flag = False
            if 'health_check' in params.get('ct_type'):
                self.post_check = params.get('perform_health_check_after_job')
                break
        self.post_check = self.post_check.lower() == "true"

    def health_check(self, job):

        if self.post_check:
            test_passed = True
            health_check_result = {}
            for host_ip in self.ips_list:
                self.log.info("Start to do health check on: %s" % host_ip)
                try:
                    health_check = hc_module(host_ip, self.params,
                                             is_raise_health_check_excp=True)

                    health_check.get_health_status()
                    health_check_result[host_ip] = True
                except exceptions.TestError:
                    health_check_result[host_ip] = False
            for key in health_check_result.keys():
                result = health_check_result[key]
                if not result:
                    self.log.info("Host %s health check failed" % key)
                    test_passed = False
                else:
                    self.log.info("Host %s health check passed" % key)

            if not test_passed:
                raise exceptions.TestError("health check failed")

    post = health_check
