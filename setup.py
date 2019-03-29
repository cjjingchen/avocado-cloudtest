#!/bin/env python
# Copyright: Lenovo Inc. 2016-2017
# Author: Yingfu Zhou <zhouyf6@lenovo.com>

import glob
import os
import sys

# pylint: disable=E0611
from setuptools import setup, find_packages

VERSION = open('VERSION', 'r').read().strip()
VIRTUAL_ENV = hasattr(sys, 'real_prefix')


def get_dir(system_path=None, virtual_path=None):
    """
    Retrieve VIRTUAL_ENV friendly path
    :param system_path: Relative system path
    :param virtual_path: Overrides system_path for virtual_env only
    :return: VIRTUAL_ENV friendly path
    """
    if virtual_path is None:
        virtual_path = system_path
    if VIRTUAL_ENV:
        if virtual_path is None:
            virtual_path = []
        return os.path.join(*virtual_path)
    else:
        if system_path is None:
            system_path = []
        return os.path.join(*(['/'] + system_path))


def get_tests_dir():
    return get_dir(['usr', 'share', 'avocado-cloudtest', 'tests'], ['tests'])


def get_avocado_libexec_dir():
    if VIRTUAL_ENV:
        return get_dir(['libexec'])
    elif os.path.exists('/usr/libexec'):  # RHEL-like distro
        return get_dir(['usr', 'libexec', 'avocado'])
    else:  # Debian-like distro
        return get_dir(['usr', 'lib', 'avocado'])


def get_data_files():
    data_files = [(get_dir(['etc', 'avocado']), ['etc/avocado/avocado.conf'])]
    data_files += [(get_dir(['etc', 'avocado', 'conf.d']),
                    ['etc/avocado/conf.d/README',
                     'etc/avocado/conf.d/cloudtest.conf'])]
    data_files += [(get_dir(['etc', 'avocado', 'sysinfo']),
                    ['etc/avocado/sysinfo/commands',
                     'etc/avocado/sysinfo/files',
                     'etc/avocado/sysinfo/profilers'])]
    data_files += [(get_dir(['etc', 'avocado', 'scripts', 'job', 'pre.d']),
                    ['etc/avocado/scripts/job/pre.d/README'])]
    data_files += [(get_dir(['etc', 'avocado', 'scripts', 'job', 'post.d']),
                    ['etc/avocado/scripts/job/post.d/README'])]

    data_files.append((get_dir(['usr', 'share', 'doc', 'avocado'], ['.']),
                       ['man/avocado.rst', 'man/avocado-rest-client.rst']))
    data_files += [(get_dir(['usr', 'share', 'avocado-cloudtest', 'wrappers'],
                            ['wrappers']),
                    glob.glob('examples/wrappers/*.sh'))]

    CLOUDTEST_DIR = 'cloudtest'
    CLOUDTEST_TESTS_DIR = os.path.join(CLOUDTEST_DIR, 'tests')
    CLOUDTEST_CONFIG_DIR = os.path.join(CLOUDTEST_DIR, 'config')
    rally_tests = 'performance/*'
    for rally_test_type in glob.glob(os.path.join(CLOUDTEST_TESTS_DIR,
                                                  rally_tests)):
        # rally_test_type can be 'scenarios'
        for sub_test_type in glob.glob('%s/*' % rally_test_type):
            # cloudtest/tests/performance/*/*
            subtest = '%s/*.yaml' % sub_test_type
            for f in glob.glob(subtest):
                dirs = sub_test_type.split('/')
                for dir_name in CLOUDTEST_TESTS_DIR.split('/'):
                    dirs.remove(dir_name)
                data_files += [(os.path.join(get_tests_dir(), '/'.join(dirs)),
                                [f])]

    stability_tests = 'stability/*'
    for mod in glob.glob(os.path.join(CLOUDTEST_TESTS_DIR,
                                      stability_tests)):
        testname = '%s/*.yaml' % mod
        for f in glob.glob(testname):
            data_files += [(os.path.join(get_tests_dir(),
                                         mod.split(CLOUDTEST_TESTS_DIR + '/')[
                                             1]),
                            [f])]

    rally_jobsdir = '%s/performance/rally/rally/rally-jobs' % \
                    CLOUDTEST_TESTS_DIR
    if os.path.exists(rally_jobsdir):
        _data_fileslist = get_file_names(rally_jobsdir)
        for i in range(len(_data_fileslist)):
            # to make /usr/share/avocado-cloudtest/tests/performance/rally-jobs
            fpath_pre = (os.path.join(get_tests_dir(), "performance"))
            file_path = _data_fileslist[i]
            start = file_path.find("rally-jobs")
            end = file_path.rfind("/")
            fpath_sub = file_path[start:end]
            fpath = os.path.join(fpath_pre, fpath_sub)
            data_files += [(fpath, [_data_fileslist[i]])]

    vm_reliability_dir = '%s/reliability/vm_reliability_tester' % \
                         CLOUDTEST_TESTS_DIR
    if os.path.exists(vm_reliability_dir):
        data_files += [(get_dir(['usr', 'share', 'avocado-cloudtest', 'tests',
                                 'vm_reliability_tester'],
                                ['vm_reliability_tester']),
                        glob.glob('%s/*' % vm_reliability_dir))]

    data_files += [(get_dir(['usr', 'share', 'avocado-cloudtest', 'config'],
                            ['config']),
                    glob.glob('%s/*' % CLOUDTEST_CONFIG_DIR))]

    data_files += [(get_dir(['usr', 'share', 'avocado-cloudtest', 'tests',
                             'common'],
                            ['common']),
                    glob.glob('%s/*' % os.path.join(CLOUDTEST_TESTS_DIR,
                                                    'common')))]

    data_files.append((get_avocado_libexec_dir(), glob.glob('libexec/*')))
    return data_files


def _get_resource_files(path, base):
    """
    Given a path, return all the files in there to package
    """
    flist = []
    for root, _, files in sorted(os.walk(path)):
        for name in files:
            fullname = os.path.join(root, name)
            flist.append(fullname[len(base):])
    return flist


def get_long_description():
    with open('README.rst', 'r') as req:
        req_contents = req.read()
    return req_contents


def _get_file_names(file_path):
    returnstr = ""
    returndirstr = ""
    returnfilestr = ""
    filelist = os.listdir(file_path)
    for num in range(len(filelist)):
        filename = filelist[num]
        if os.path.isdir(file_path + "/" + filename):
            returndirstr += _get_file_names(file_path + "/" + filename)
        else:
            returnfilestr += file_path + "/" + filename + "\n"
    returnstr += returnfilestr + returndirstr
    return returnstr


def get_file_names(file_path):
    """
    param file_path: the file path
    return: list of file paths
    """
    _data_files = _get_file_names(file_path)
    _data_files = _data_files[:-1]
    data_files = _data_files.split("\n")
    return data_files


if __name__ == '__main__':
    setup(name='avocado-cloudtest',
          version=VERSION,
          description='Avocado CloudTest Automation Framework',
          author='Yingfu Zhou',
          author_email='zhouyf6@lenovo.com',
          url='http://10.100.3.216/zhouyf6/avocado-cloudtest.git',
          long_description=get_long_description(),
          # use_2to3=True,
          packages=find_packages(),
          package_data={"cloudtest": ["*.*"],
                        "avocado": ["avocado.plugins.html/*"]},
          include_package_data=True,
          find_package_data=True,
          data_files=get_data_files(),
          scripts=['scripts/avocado',
                   'scripts/avocado-rest-client',
                   'scripts/avocado-run-testplan',
                   'scripts/avocado-run-test-strategy'],
          entry_points={
              'avocado.plugins.cli': [
                  'ct = avocado.plugins.ct:CloudTestRun',
                  'ct-list = avocado.plugins.ct:CloudTestLister',
                  'wrapper = avocado.plugins.wrapper:Wrapper',
                  'xunit = avocado.plugins.xunit:XUnitCLI',
                  'json = avocado.plugins.jsonresult:JSONCLI',
                  'journal = avocado.plugins.journal:Journal',
                  'yaml_to_mux = avocado.plugins.yaml_to_mux:YamlToMux',
                  'zip_archive = avocado.plugins.archive:ArchiveCLI',
                  'html = avocado.plugins.html:HTML'
              ],
              'avocado.plugins.cli.cmd': [
                  'config = avocado.plugins.config:Config',
                  'distro = avocado.plugins.distro:Distro',
                  'exec-path = avocado.plugins.exec_path:ExecPath',
                  'multiplex = avocado.plugins.multiplex:Multiplex',
                  'list = avocado.plugins.list:List',
                  'run = avocado.plugins.run:Run',
                  'sysinfo = avocado.plugins.sysinfo:SysInfo',
                  'plugins = avocado.plugins.plugins:Plugins',
                  'diff = avocado.plugins.diff:Diff',
                  'slave = avocado.plugins.install:Slave',
              ],
              'avocado.plugins.job.prepost': [
                  'jobscripts = avocado.plugins.jobscripts:JobScripts',
                  'mail = avocado.plugins.avocado_job_mail:Mail',
                  'healthcheck = avocado.plugins.health_check:HealthCheck'
              ],
              'avocado.plugins.result': [
                  'xunit = avocado.plugins.xunit:XUnitResult',
                  'json = avocado.plugins.jsonresult:JSONResult',
                  'zip_archive = avocado.plugins.archive:Archive',
                  'html = avocado.plugins.html:HTMLResult',
              ],
              'avocado.plugins.result_events': [
                  'human = avocado.plugins.human:Human',
                  'journal = avocado.plugins.journal:JournalResult',
              ],
          },
          zip_safe=False,
          test_suite='selftests',
          python_requires='>=2.6',
          install_requires=['stevedore'])
