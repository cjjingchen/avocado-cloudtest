# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Lenovo Inc. 2016
# Author: Kai Pang <pangkai1@lenovo.com>

"""
Base Test Install Plugins.
"""

import os
import time
import logging
import commands
import aexpect

from avocado.core.plugin_interfaces import CLICmd
from avocado.utils import archive
from cloudtest import remote


class Slave(CLICmd):
    """
    Implements the avocado 'install', 'update',
    'uninstall' and 'add' subcommand
    ex:
    avocado slave --action=install --remote-ip=10.100.4.161
    --username=root --password=123456 --role=slave --module=avocado
    --src-dir=/chenjing/new/avocado-cloudtest --debug

    avocado slave --action=install --remote-ip=10.100.4.161
    --username=root --password=123456 --role=slave --module=avocado --debug

    avocado slave --action=add --remote-ip=10.100.4.161 --username=root
    --password=123456
    """

    name = 'slave'
    description = ("Install module")

    def configure(self, parser):
        """
        Add the subparser for the install action.

        :param parser: Install parser.
        """
        parser = super(Slave, self).configure(parser)

        parser.add_argument('--remote-ip', dest='remote_ip',
                            type=str, default=None,
                            help='The address of host you want to control')

        parser.add_argument('--username', dest='username',
                            type=str, default=None,
                            help='The user name to login to the host you '
                                 'want to control')

        parser.add_argument('--password', dest='user_password',
                            type=str, default=None,
                            help='The user password to login to the host you'
                                 'want to control')

        parser.add_argument('--role', dest='host_role',
                            type=str, default=None,
                            help='Which role will be for the host')

        parser.add_argument('--module', dest='install_module',
                            type=str, default=None,
                            help='Which module will be installed')

        parser.add_argument('--src-dir', dest='src_dir',
                            type=str, default=None,
                            help='Where are the avocado cloudtest source code'
                                 'in')

        parser.add_argument('--debug', action="store_true", default=False,
                            help='More detailed info')

        parser.add_argument('--action', dest='operation_type',
                            type=str, default=None,
                            help='4 operations are supported, '
                                 'including install, '
                                 'update, uninstall and add')

    def clean_srcdir(self, path, log):
        """
        Clean source dir.

        :param path: avocado-cloudtest location.
        """
        log.info("Clean source dir ...")
        cmd_1 = "cd " + path + "; make clean"
        # log.debug("run cmd:%s" % cmd_1)
        (status, output) = commands.getstatusoutput(cmd_1)
        # log.debug("status:%s" % status)
        # log.debug("output:%s" % output)
        cmd_2 = "rm -rf build/* dist/* avocado_cloudtest.egg-info/"
        # log.debug("run cmd:%s" % cmd_2)
        (status, output) = commands.getstatusoutput(cmd_2)
        # log.debug("status:%s" % status)
        # log.debug("output:%s" % output)

    def install_module(self, log, srcdir, src_pkg_dir, pkg_name, tg_pkg_dir,
                       pkg_dirname, remote_ip, username, password, mod,
                       debug_mode):
        if srcdir is not None:
            if len(srcdir) != 0:
                dependency_dir = srcdir + "/dependencies"
                if os.path.isdir(dependency_dir):
                    self.clean_srcdir(srcdir, log)
                    log.info("Compress source dir to tarball ...")
                    archive.compress(src_pkg_dir + pkg_name, srcdir)
                    remoter = remote.RemoteRunner(host=remote_ip,
                                                  username=username,
                                                  password=password)
                    result = remoter.run("rm -rf " + tg_pkg_dir)
                    result = remoter.run(
                        "mkdir -p " + tg_pkg_dir + pkg_dirname)
                    log.info("Copy %s to %s %s ..." % (
                        src_pkg_dir + pkg_name, remote_ip, tg_pkg_dir))
                    remote.scp_to_remote(remote_ip, 22, username,
                                         password,
                                         src_pkg_dir + pkg_name,
                                         tg_pkg_dir)
                    log.info("Decompress tarball %s on %s ..." % (
                        tg_pkg_dir + pkg_name, remote_ip))
                    result = remoter.run("tar xvf " + tg_pkg_dir + pkg_name +
                                         " -C " + tg_pkg_dir + "/" +
                                         pkg_dirname)
                    log.info("Install role %s %s on %s ... " %
                             ('slave', mod, remote_ip))

                    result = remoter.run("cd " + tg_pkg_dir + pkg_dirname
                                         + "; ./install.sh -m " + mod + " -r "
                                         + "slave " + "-o " + "install " +
                                         debug_mode, timeout=3600)

                    if result.exit_status == 0:
                        log.info("Success")
                        return True
                    else:
                        log.info("Failed")
                        return False
                else:
                    log.info(
                        "Fault source dir, there is not dependencies dir.")
            else:
                log.info("Source dir does has vaule.")
        else:
            log.info("Parameter fault, give the source dir.")

    def update_module(self, log, srcdir, src_pkg_dir, pkg_name, tg_pkg_dir,
                      pkg_dirname, remote_ip, username, password, mod,
                      debug_mode):
        if srcdir is not None:
            if len(srcdir) != 0:
                dependency_dir = srcdir + "/dependencies"
                if os.path.isdir(dependency_dir):
                    self.clean_srcdir(srcdir, log)
                    log.info("Compress source dir to tarball ...")
                    archive.compress(src_pkg_dir + pkg_name, srcdir)
                    remoter = remote.RemoteRunner(host=remote_ip,
                                                  username=username,
                                                  password=password)
                    result = remoter.run("rm -rf " + tg_pkg_dir)
                    result = \
                        remoter.run("mkdir -p " + tg_pkg_dir + pkg_dirname)
                    log.info("Copy %s to %s %s ..." %
                             (src_pkg_dir + pkg_name, remote_ip, tg_pkg_dir))
                    remote.scp_to_remote(remote_ip, 22, username,
                                         password,
                                         src_pkg_dir + pkg_name,
                                         tg_pkg_dir)
                    log.info("Decompress tarball %s on %s ..." %
                             (tg_pkg_dir + pkg_name, remote_ip))
                    result = remoter.run("tar xvf " + tg_pkg_dir + pkg_name +
                                         " -C " + tg_pkg_dir + "/" +
                                         pkg_dirname)
                    log.info("Update role %s %s on %s ... " %
                             ('slave', mod, remote_ip))

                    result = remoter.run("cd " + tg_pkg_dir + pkg_dirname
                                         + "; ./install.sh -m " + mod + " -r "
                                         + "slave " + "-o " + "update " +
                                         debug_mode, timeout=3600)

                    if result.exit_status == 0:
                        log.info("Success")
                        return True
                    else:
                        log.info("Failed")
                        return False
                else:
                    log.info(
                        "Fault source dir, there is not dependencies dir.")
            else:
                log.info("Source dir does has vaule.")
        else:
            log.info("Parameter fault, give the source dir.")

    def uninstall_avocado(self, log, tg_pkg_dir, pkg_dirname, remote_ip,
                          username, password, mod, debug_mode):
        log.info("Remote %s with username: %s and password %s " %
                 (remote_ip, username, password))
        remoter = remote.RemoteRunner(host=remote_ip,
                                      username=username,
                                      password=password)
        result = remoter.run("cd " + tg_pkg_dir + pkg_dirname)
        result = remoter.run("./install.sh -m " + mod + " -r "
                             + "slave " + "-o " + "uninstall " +
                             debug_mode, ignore_status=True)

        log.info("Done")

    def add_running_host(self, log, remote_ip, password):
        cmd = "ssh-copy-id -i ~/.ssh/id_rsa.pub -o StrictHostKeyChecking=" \
              "no root@%s" % remote_ip

        session = aexpect.ShellSession(cmd, prompt="password:")
        match, text = session.read_until_last_line_matches([r"password:"])
        result = None
        if match == 0:
            result = session.sendline(password)
            time.sleep(10)

        log.info("Done")

    def run(self, args):
        """
        Run test modules or simple tests.
        :param args: Command line args received from the run subparser.
        """
        log = logging.getLogger("avocado.app")

        remote_ip = args.remote_ip
        username = args.username
        password = args.user_password
        host_role = args.host_role
        if args.src_dir is None:
            srcdir = os.getcwd()
        else:
            srcdir = args.src_dir
        mod = args.install_module
        operation = args.operation_type
        if args.debug:
            debug_mode = " --debug "
        else:
            debug_mode = ""
        pkg_name = "avocado-cloudtest.tar"
        pkg_dirname = "avocado-cloudtest"
        src_pkg_dir = "/root/"
        tg_pkg_dir = "/root/new/"
        log.info("The current src-dir is %s" % srcdir)

        remoter = remote.RemoteRunner(host=remote_ip, username=username,
                                      password=password)
        if operation == 'install':
            self.install_module(log, srcdir, src_pkg_dir, pkg_name,
                                tg_pkg_dir, pkg_dirname, remote_ip, username,
                                password, mod, debug_mode)

        if operation == 'update':
            self.update_module(log, srcdir, src_pkg_dir, pkg_name,
                               tg_pkg_dir, pkg_dirname, remote_ip, username,
                               password, mod, debug_mode)

        if operation == 'uninstall':
            self.uninstall_avocado(log, tg_pkg_dir, pkg_dirname, remote_ip,
                                   username, password, mod, debug_mode)

        if operation == 'add':
            self.add_running_host(log, remote_ip, password)
