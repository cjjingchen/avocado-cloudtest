import logging
import os
import smtplib
import socket
import time
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from bottle import template
from collections import OrderedDict

from avocado.core.plugin_interfaces import JobPost
from avocado.core.settings import settings
from avocado.utils import process
from cloudtest import cartesian_config
from cloudtest.resources.config_string import *


class Mail(JobPost):
    name = 'mail'
    description = 'Sends mail to notify on job start/end'

    def __init__(self):
        self.log = logging.getLogger("avocado.app")
        self.receiver = None
        self.branch_name = ""
        self.version = ""
        self.manifest_file_path = ""
        self.SLA = 0.95

        self.sender = settings.get_value(section="send_result",
                                         key="sender",
                                         key_type=str,
                                         default='cloudtest@lenovo.com')
        self.smtp_host = settings.get_value(section="send_result",
                                            key="smtp_host",
                                            key_type=str)
        self.smtp_port = settings.get_value(section="send_result",
                                            key="smtp_port",
                                            key_type=int)
        self.smtp_user = settings.get_value(section="send_result",
                                            key="smtp_user",
                                            key_type=str,
                                            default='')
        self.smtp_password = settings.get_value(section="send_result",
                                                key="smtp_password",
                                                key_type=str,
                                                default='')
        parser = cartesian_config.Parser()
        cfg = os.path.join(settings.get_value('datadir.paths',
                                              'base_dir'),
                           'config/tests.cfg')
        parser.parse_file(cfg)
        dicts = parser.get_dicts()
        for params in (_ for _ in dicts):
            OPENSTACK_URL = params.get('identity_uri_ip')
            OPENSTACK_USERNAME = params.get('openstack_ssh_username')
            OPENSTACK_PASSWORD = params.get('openstack_ssh_password')
            self.receiver = params.get('report_send_to_email')
            self.ct_type = params.get('ct_type')
            self.branch_name = params.get('branch_name', '')
            self.version = params.get('product_version', '')
            self.manifest_file_path = params.get('manifest_file_path', '')
            self.HA_Enable = params.get('HA_Enable', 'no')
            self.HA = 'HA'if self.HA_Enable in 'yes' else 'Non-HA'
            break

    def mail(self, job):
        cmd = 'tempest --version'
        cmd1 = 'rally --version'
        # tempest_version = process.run(cmd, shell=True,
        #                              ignore_status=True,
        #                              verbose=False).stderr
        # rally_version = process.run(cmd1, shell=True,
        #                            ignore_status=True,
        #                            verbose=False).stderr

        localIP = socket.gethostbyname(socket.gethostname())
        ipList = socket.gethostbyname_ex(socket.gethostname())
        for i in ipList:
            if i != localIP:
                host = '%s' % i

        test_time = '%s' % (job.result.tests_total_time)
        job_id = '%s' % (job.unique_id)
        start_time = None
        end_time = None
        start_time = time.strftime("%Y-%m-%d %H:%M:%S",
                                   time.localtime(
                                       job.result.tests[0]['time_start']))
        end_time = time.strftime("%Y-%m-%d %H:%M:%S",
                                 time.localtime(
                                     job.result.tests[-1]['time_end']))

        if job.jenkins_build_url is not None:
            result_link = job.jenkins_build_url
        else:
            result_link = job.logdir

        if job.result.errors + job.result.failed > 0:
            result = 'FAILED'
        else:
            result = 'PASS'
        articles = [(job.product_build_number, self.ct_type, result,
                     job.result.passed, job.result.failed, job.result.errors,
                     test_time, start_time, end_time, result_link)]

        if float(job.result.passed) / float(job.result.errors +
                                                    job.result.failed +
                                                    job.result.passed) >= self.SLA:
            title_added = "Recommended for test"
        else:
            title_added = "NOT recomended for test"

        if "integrate" in self.ct_type:
            html = template(TEMPEST_TEST_REPORT, items=articles)
        elif 'ceph_management_api' in self.ct_type:
            test_details, url, build_location, ha_install, deploy_status = \
                self._get_ceph_test_details(job)
            logging.info("HA install is : %s" % ha_install)
            logging.info("deploy_status is : %s" % deploy_status)
            deployments = [(self.HA, url, deploy_status, ha_install)]
            html = template(CEPH_TEST_DETAIL_REPORT,
                            deployments=deployments, items=articles,
                            details=test_details,
                            build_location=build_location,
                            code_mainfest=self.manifest_file_path,
                            new_patch_list=self._get_new_patch_list(job))
            # html = template(CEPH_TEST_REPORT, items=articles)
        elif 'nfv_test' in self.ct_type:
            html = template(NFV_TEST_REPORT, items=articles)
        else:
            html = template(COMMON_TEST_REPORT, items=articles)

        msg = MIMEMultipart()
        if 'ceph_management_api' in self.ct_type:
            msg['Subject'] = "ThinkCloud Storage %s %s daily build release: %s" \
                             % (self.version, self.branch_name, title_added)
        else:
            msg['Subject'] = "[CloudTest Report] Test Result For Build %s: %s" \
                             % (job.product_build_number, result)
        msg['From'] = self.sender
        msg['To'] = self.receiver
        context = MIMEText(html, _subtype='html', _charset='utf-8')
        msg.attach(context)

        # So many possible failures, let's just tell the user about it
        try:
            if not self.receiver:
                self.log.error("Report not sent, please specify email"
                               " address in config file")
                return
            if ',' in self.receiver:
                self.receiver = self.receiver.split(',')
            elif ';' in self.receiver:
                self.receiver = self.receiver.split(';')

            smtp = smtplib.SMTP()
            smtp.connect(self.smtp_host, self.smtp_port)
            if self.smtp_user and self.smtp_password:
                smtp.login(self.smtp_user, self.smtp_password)
            smtp.sendmail(self.sender, self.receiver, msg.as_string())
            smtp.quit()
            self.log.info("Job report email sent to %s" % self.receiver)
        except Exception, e:
            self.log.error("Failed to send report email: %s" % e)

    post = mail

    def _get_ceph_test_details(self, job):
        articles_dict = OrderedDict()
        build_location = ""
        code_manifest = ""
        url = ""
        ha_install = None
        deploy_status = 'PASS'
        log_path = os.path.join(job.logdir, 'job.log')
        try:
            with open(log_path, 'r') as log_file:
                r_l = log_file.readline()
                regex = '^.*(test).*(PASS|FAIL|ERROR)(\s+)(\d+).*'
                while r_l:
                    r = re.findall(regex, r_l)
                    if r:
                        s = re.split('ceph_management_api', r_l)[1].split('.')
                        suite = 'ceph_management_api.' + s[1] + '.' + \
                                s[2].split(' ')[0]
                        if articles_dict.get(suite) is None:
                            articles_dict[suite] = [0, 0, 0]
                        if ' PASS ' in r_l:
                            articles_dict[suite][0] += 1
                        elif ' FAIL ' in r_l:
                            articles_dict[suite][1] += 1
                        elif ' ERROR ' in r_l:
                            articles_dict[suite][2] += 1

                        if ("deploy" in s[2].strip()) and \
                                ("multi_hosts" in s[3].strip()):
                            if ' PASS ' not in r_l:
                                deploy_status = 'FAILED'

                    if 'ceph_management_url' in r_l:
                        url = r_l.split(' = ')[1]

                    r2 = re.findall('.*ha_install.*', r_l)
                    if r2:
                        ha_install = r_l.split('ha_install = ')[1].strip()
                        if ha_install in 'true':
                            ha_install = 'true'
                        else:
                            ha_install = 'false'

                    if 'daily_build_location' in r_l:
                        build_location = r_l.split('daily_build_location = ')[1]

                    r_l = log_file.readline()

            articles_tuple = ()
            for suite in articles_dict:
                result_list = []
                result_list.append(suite)
                result_list.append(articles_dict[suite][0])
                result_list.append(articles_dict[suite][1])
                result_list.append(articles_dict[suite][2])
                test_list = []
                test_list.append(result_list)
                articles_tuple += tuple(test_list)
            articles_list = []
            articles_list.append(articles_tuple)
        except Exception, e:
            msg = "Exception happened during get test details: %s" % e
            self.log.error(msg)
            return None

        if build_location:
            build_location = build_location.replace('\n', '')
            build_location = \
                build_location.replace('branch_name', self.branch_name) \
                + job.product_build_number

        return articles_list, url, build_location, ha_install, deploy_status

    @staticmethod
    def _get_new_patch_list(job):
        new_patch_list = []
        if os.path.exists(job.new_patch_file):
            with open(job.new_patch_file, 'r') as f:
                new_patch = f.readline()
                while new_patch:
                    new_patch_list.append(new_patch)
                    new_patch = f.readline()

        return new_patch_list
