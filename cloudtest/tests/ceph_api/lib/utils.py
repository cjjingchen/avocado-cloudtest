"""
Utilities for Ceph management system REST api test.
"""

import sys
import re
import inspect
import logging
import paramiko
import copy
import json

from avocado.utils import process
from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest.tests.ceph_api.api_schema.request import utils as schema_utils

LOG = logging.getLogger('avocado.test')


def verify_response(req_body, resp):
    """
    Verify if rest response is correct

    :param req_body: the request body
    :param resp: the rest resonse
    """
    LOG.info("Start verifing response '%s'" % resp)
    for k, v in req_body.items():
        if not v == resp[k]:
            return False
    return True


def sshclient_execmd(control_ip, control_username, control_passwd,
                     host, username, passwd, cmd, check_data=None):
    passinfo = r"[Pp]assword:\s*$"
    endinfo = r"[\#\$]\s*$"

    # Connect controller node
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=control_ip, username=control_username,
                password=control_passwd)

    # Connect ssh client from controller to iscsi target
    channel = ssh.invoke_shell()
    channel.settimeout(300)
    buff = ''
    resp = ''
    channel.send('ssh ' + username + '@' + host + '\n')

    while not buff.endswith(passinfo):
        try:
            resp = channel.recv(99999)
            LOG.info('resp1: %s' % resp)
        except Exception as e:
            LOG.error('%s connection time' % (str(e)))
            channel.close()
            ssh.close()
            continue

        buff += resp
        if ("password:" in buff) or (passinfo in buff):
            break
        if not buff.find('yes/no') == -1:
            channel.send('yes\n')
            buff = ''

    LOG.info("password is %s" % passwd)
    channel.send(passwd + '\n')
    buff = ''

    while not buff.endswith(endinfo):
        resp = channel.recv(99999)
        LOG.info('resp2: %s' % resp)
        if ("~]# " in resp):
            break
        if not resp.find(passinfo) == -1:
            LOG.error('Error info: Authentication failed.')
            channel.close()
            ssh.close()
            continue

        buff += resp
    channel.send(cmd + '\n')
    buff = ''
    try:
        while buff.find('#') == -1:
            resp = channel.recv(99999)
            buff += resp
    except Exception as e:
        LOG.error("Error info:" + str(e))

    LOG.info(buff)
    channel.close()
    ssh.close()

    if check_data is not None:
        if buff.find(check_data) == -1:
            return False, buff
        else:
            return True, buff

    return True, buff


class CmdUtils(object):
    """
    Ceph related command line wrapper class
    """

    def __init__(self, parent):
        self.cmd = parent


class OSDUtils(CmdUtils):
    """
    The module to operate OSD related objects
    """

    def __init__(self):
        super(OSDUtils, self).__init__('ceph osd')

    def _pool_ops(self, action, *args):
        """
        Basic function to operate pool object
        """
        cmd = self.cmd + ' pool %s' % action
        i = 0
        while i < len(args):
            cmd += ' ' + args[i]
            i += 1
        result = process.run(cmd, shell=True)
        if result.exit_status != 0:
            LOG.error("Failed to %s: %s" % (cmd, result.stderr))
            return False
        return True

    def create_pool(self, name):
        """
        Function to create a pool with specified name
        """
        return self._pool_ops('create', name)

    def delete_pool(self, name):
        """
        Delete the specified pool
        """
        return self._pool_ops('delete', name)


class RBDUtils(CmdUtils):
    """
    Base class for rbd related operations
    """

    def __init__(self):
        super(RBDUtils, self).__init__('rbd')

    def create_image(self, name, img_size, pool_name):
        """
        Function to create rbd image on specified pool

        :param name: the image name
        :param img_size: size in GB to create
        :param pool_name: the pool name to create onto
        """
        cmd = self.cmd + ' create image %s --size %s --pool %s' % (name,
                                                                   img_size,
                                                                   pool_name)
        result = process.run(cmd, shell=True)
        return result.exit_status == 0

    def delete_image(self, name):
        """
        Delete the specified image
        """
        pass


def find_test_caller():
    """Find the caller class and test name.

    Because we know that the interesting things that call us are
    test_* methods, and various kinds of setUp / tearDown, we
    can look through the call stack to find appropriate methods,
    and the class we were in when those were called.
    """
    caller_name = None
    names = []
    frame = inspect.currentframe()
    is_cleanup = False
    # Start climbing the ladder until we hit a good method
    while True:
        try:
            frame = frame.f_back
            name = frame.f_code.co_name
            names.append(name)
            if re.search("^(test_|setUp|tearDown)", name):
                cname = ""
                if 'self' in frame.f_locals:
                    cname = frame.f_locals['self'].__class__.__name__
                if 'cls' in frame.f_locals:
                    cname = frame.f_locals['cls'].__name__
                caller_name = cname + ":" + name
                break
            elif re.search("^_run_cleanup", name):
                is_cleanup = True
            elif name == 'main':
                caller_name = 'main'
                break
            else:
                cname = ""
                if 'self' in frame.f_locals:
                    cname = frame.f_locals['self'].__class__.__name__
                if 'cls' in frame.f_locals:
                    cname = frame.f_locals['cls'].__name__

                # the fact that we are running cleanups is indicated pretty
                # deep in the stack, so if we see that we want to just
                # start looking for a real class name, and declare victory
                # once we do.
                if is_cleanup and cname:
                    if not re.search("^RunTest", cname):
                        caller_name = cname + ":_run_cleanups"
                        break
        except Exception:
            break
    # prevents frame leaks
    del frame
    if caller_name is None:
        LOG.debug("Sane call name not found in %s" % names)
    return caller_name


def get_query_body(request, url, query_page=None):
    if not query_page:
        query_page = {'preindex': 0, 'sufindex': 100}
    body = copy.deepcopy(schema_utils.QUERY_PAGE)
    body['preindex'] = query_page.get('preindex', 0)
    body['sufindex'] = query_page.get('sufindex', 1024)
    resp, body = request('GET', url, body=json.dumps(body))
    items = json.loads(body)['items'] if body else body
    return resp, items
