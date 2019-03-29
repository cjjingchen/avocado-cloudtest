import logging
import time
import string

from avocado.core import test
from avocado.core import exceptions

from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.rbd_client import RbdClient
from cloudtest.tests.ceph_api.lib.iscsi_client import ISCSIClient
from cloudtest.tests.ceph_api.lib.pools_client import PoolsClient

LOG = logging.getLogger('avocado.test')


class TestISCSIMulpath(test.Test):
    """
    Module for testing ISCSI Multipath related operations.
    """
    def __init__(self, params, env):
        self.params = params
        self.body = {}
        self.env = env
        self.rbd_client = None 
        self.iscsi_client = None
        self.pool_client = None 

        self.control_server_ip = self.params.get('ceph_management_url')
        self.control_server_ip = self.control_server_ip.split(':')[1].strip(
            '/')
        self.control_username = self.params.get('ceph_server_ssh_username',
                                                'root')
        self.control_password = self.params.get('ceph_server_ssh_password')
        self.initiator_ip = self.params.get('ceph_node_ip')
        self.initiator_username = self.params.get('ceph_node_ssh_username')
        self.initiator_password = self.params.get('ceph_node_ssh_password')
        self.target_ip = self.params.get('ceph_node_ip')

        self.dirtypoint = "This is an example to check multipath"        
        self.mulpath_mountpoint = "/mnt/multipath"
        self.mulpath_filename = "example.txt"
        self.rbd_name = None
        self.rbd_id = None
        self.iscsi_target_id = None
        self.iscsi_target_name = None
        self.iscsi_target_hostip = []
        self.lun_id = None
        self.pool_name = None
        self.pool_id = None
        self.cluster_id = None

    def setup(self):
        if 'cluster' in self.env:
            self.cluster_id = self.env['cluster']
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')
        else:
            clusters = test_utils.get_available_clusters(self.params)
            if len(clusters) > 0 :
                self.cluster_id = clusters[0]['id']
        self.params['cluster_id'] = self.cluster_id
        self.pool_client = PoolsClient(self.params)

        if 'pool_name' in self.env:
            self.pool_name = self.env['pool_name']
        else:
            self.pool_name = self.params.get('pool_name', 'rbd')
        self.params['pool_name'] = self.pool_name
        if self.pool_name is not None:
            resp = self.pool_client.query()
            for i in range(len(resp)):
                if resp[i]['name'] == self.pool_name:
                    self.pool_id = resp[i]['id']
        else:
            self.pool_id = test_utils.create_pool(self.params)
            LOG.info("Created pool that id is %s" % self.pool_id)
        self.params['pool_id'] = self.pool_id

        self.rbd_client = RbdClient(self.params)
        self.iscsi_client = ISCSIClient(self.params)

    def _create_iscsi_target(self):
        self.iscsi_target_name = "cloudtest" + \
                                 utils.utils_misc.generate_random_string(6)
        body = {'initiator_ips': self.initiator_ip,
                'target_name': self.iscsi_target_name,
                'multipath': self.params.get('multipath', '3')}
        resp = self.iscsi_client.create(**body)
        if not resp and utils.verify_response(body, resp):
            raise exceptions.TestFail("Create target failed: %s" % body)
        self.iscsi_target_hostip = resp['host_ip'].split(',')

        return resp.body['target_id']

    def _create_iscsi_lun(self, target_id, rbd_id):
        body = {'target_id': target_id,
                'pool_id': self.pool_id,
                'rbd_id': rbd_id}
        resp = self.iscsi_client.add_lun(**body)

        return resp.body['lun_id']

    def _delete_iscsi_lun(self, target_id, lun_id):
        body = {
            'target_id': target_id,
            'lun_id': lun_id}
        self.iscsi_client.delete_lun(**body)

    def _delete_target(self, target_id):
        """
        Test that deletion of delete target
        """
        self.iscsi_client.delete_iscsitarget(target_id)
        resp = self.iscsi_client.query()
        for i in range(len(resp)):
            if resp[i]['target_id'] == target_id:
                raise exceptions.TestFail("Delete target failed")

    def _delete_rbd(self, pool_id, rbd_id):
        """
        Test that deletion of specified rdb
        """
        # delete the rbd created in the right pool
        resp = self.rbd_client.delete_rbd(self.pool_id, rbd_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("Delete rbd failed")

    def get_rbd_id(self, pool_id, rbd_name):
        """
        Query a specified rbd in a definitely pool
        
        """
        resp = self.rbd_client.query(pool_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("No specified rbd found in the pool")
        for i in range(len(resp)):
            if resp[i]['name'] == rbd_name:
                return resp[i]['id']
        return None

    def get_rbd_name(self, pool_id, rbd_id):
        """
        Query a specified rbd in a definitely pool
        
        """
        resp = self.rbd_client.query(pool_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("No specified rbd found in the pool")
        for i in range(len(resp)):
            if resp[i]['id'] == rbd_id:
                return resp[i]['name']
        return None

    def hit_target(self, control_server_ip, control_username, control_password,
              initiator_ip, initiator_username, initiator_password):
        for i in range(len(self.iscsi_target_hostip)):
            cmd = ('iscsiadm -m discovery -t st -p %s; ' % 
                   self.iscsi_target_hostip[i])
            find, buff = utils.sshclient_execmd(control_server_ip, 
                                                control_username, 
                                                control_password, 
                                                initiator_ip, 
                                                initiator_username, 
                                                initiator_password, 
                                                cmd)
            if buff.find(self.iscsi_target_name) == -1 :
                raise exceptions.TestFail("No specified target found for %s" % 
                                          self.iscsi_target_hostip[i])

    def do_iscsi_login(self, control_server_ip, control_username, 
                       control_password, initiator_ip, initiator_username, 
                       initiator_password, target_ip):
        cmd = ('iscsiadm -m node -T %s -p %s --login; ' % 
               (self.iscsi_target_name, target_ip))
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)

    def do_iscsi_logout(self, control_server_ip, control_username, 
                        control_password, initiator_ip, initiator_username, 
                        initiator_password, target_ip):
        cmd = ('iscsiadm -m node -T %s -p %s --logout; ' % 
               (self.iscsi_target_name, target_ip))
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)

    def get_iscsi_count(self, control_server_ip, control_username, 
                        control_password, initiator_ip, initiator_username, 
                        initiator_password):
        retval = 0
        cmd = ('lsblk -S | wc -l; ')
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        _lines = buff.split('\n')
        retval = string.atoi(_lines[1],10)
        return retval


    def get_iscsi_multipath(self, control_server_ip, control_username, 
                            control_password, initiator_ip, initiator_username, 
                            initiator_password):
        cmd = 'multipath -l; '
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        return find, buff

    def get_chars(self, str):
        _str = ""
        for i in str:
            if ((i >= 'a' and i <= 'z') 
                or i == '/' or i == ' ' or
                (i >= 'A' and i <= 'Z')):
                _str += i
        return _str

    def make_iscsi_dirty(self, control_server_ip, control_username, 
                         control_password, initiator_ip, initiator_username, 
                         initiator_password):
        cmd = 'ls --color=never /dev/mapper/mpath*'
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        _lines = buff.split('\n')
        if len(_lines) < 2 :
            raise exceptions.TestFail("Did not get any mapper device") 
        mapper_device = self.get_chars(_lines[1])
        if len(mapper_device) == 0:
            raise exceptions.TestFail("Did not get a valid mapper device name") 

        cmd = 'mkdir %s' % (mapper_device)
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        cmd = 'mkfs.ext4 %s' % mapper_device
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        cmd = 'mount %s %s' % (mapper_device, self.mulpath_mountpoint) 
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        cmd = 'echo "%s" > %s/%s' % (self.dirtypoint, self.mulpath_mountpoint, 
                                     self.mulpath_filename)
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        cmd = 'cat %s/%s' % (self.mulpath_mountpoint, self.mulpath_filename)
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)

    def start_iscsi_tgt(self, control_server_ip, control_username, 
                        control_password, initiator_ip, initiator_username, 
                        initiator_password):
        cmd = 'service tgtd start'
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)

    def stop_iscsi_tgt(self, control_server_ip, control_username, 
                       control_password, initiator_ip, initiator_username, 
                       initiator_password):
        cmd = 'service tgtd stop'
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)

    def check_iscsi_dirty(self, control_server_ip, control_username, 
        control_password, initiator_ip, initiator_username, initiator_password):
        cmd = 'cat %s/%s' % (self.mulpath_mountpoint, self.mulpath_filename)
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        _lines = buff.split('\n')
        if len(_lines) < 2 :
            raise exceptions.TestFail("Did not get info for validation") 
        info_val = self.get_chars(_lines[1])
        if self.dirtypoint == info_val :
            LOG.info("Find %s under %s!" % (self.mulpath_filename, 
                                            self.mulpath_mountpoint))
        else:
            raise exceptions.TestFail("%s not found under %s" % 
                             (self.mulpath_filename, self.mulpath_mountpoint))
        
        cmd = 'rm -rf %s/%s' % (self.mulpath_mountpoint, self.mulpath_filename)
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        cmd = '[ -f %s/%s ] || echo removed' % (self.mulpath_mountpoint, 
                                                self.mulpath_filename)
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        _lines = buff.split('\n')
        info_val = self.get_chars(_lines[1])
        if info_val == "removed":
            LOG.info("Removed %s successfully!" % self.mulpath_filename)
        else:
            raise exceptions.TestFail("Removed %s fault!" % self.mulpath_filename)

    def clean_iscsi_dirty(self, control_server_ip, control_username, 
                          control_password, initiator_ip, initiator_username, 
                          initiator_password):
        cmd = 'umount %s' % self.mulpath_mountpoint
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)

    def iscsi_actions(self, control_server_ip, control_username, 
                      control_password, initiator_ip, initiator_username, 
                      initiator_password, target_ip):
        
        cmd = 'yum -y install iscsi-initiator-utils ; '
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        if not (find) :
            raise exceptions.TestFail("Install iscsi-initiator-utils fault")

        cmd = 'yum -y install device-mapper-multipath ; '
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        if not (find) :
            raise exceptions.TestFail("Install device-mapper-multipath fault")

        multipathconf="""defaults{\n    user_friendly_names yes\n""" \
        """    polling_interval 10\n    checker_timeout 120\n    """ \
        """queue_without_daemon no\n}\nblacklist {\n""" \
        """    devnode "^(ram|raw|loop|fd|md|dm-|sr|scd|st)[0-9]*"\n""" \
        """    devnode "^hd[a-z]"\n}\ndevices {\n    device{\n        """ \
        """path_grouping_policy failover\n    }\n}"""
        cmd = 'echo \'%s\' > /etc/multipath.conf' % multipathconf
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)

        cmd = 'systemctl start multipathd '
        find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd)
        if not find :
            raise exceptions.TestFail("Start multipath service fault")

        self.hit_target(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password)

        iscsi_count1 = self.get_iscsi_count(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password)
        #Login iscsi
        self.do_iscsi_login(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        self.iscsi_target_hostip[0])
        time.sleep(1)
        iscsi_count2 = self.get_iscsi_count(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password)
        #Check lsblk
        if iscsi_count2 <= iscsi_count1:
            raise exceptions.TestFail("Login target to be first iscsi fault")

        self.do_iscsi_login(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        self.iscsi_target_hostip[1])
        time.sleep(1)
        iscsi_count3 = self.get_iscsi_count(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password)
        #Check lsblk
        if iscsi_count3 <= iscsi_count2:
            raise exceptions.TestFail("Login target to be second iscsi fault")

        #Get Multipath
        find, buff = self.get_iscsi_multipath(control_server_ip, 
                                              control_username, 
                                              control_password, 
                                              initiator_ip, 
                                              initiator_username, 
                                              initiator_password)
        #Check Multipath

        #make iscsi dirty
        self.make_iscsi_dirty(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password)
        time.sleep(1)
        #Stop one tgt
        self.stop_iscsi_tgt(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password)
        time.sleep(1)

        #Check iscsi dirty        
        self.check_iscsi_dirty(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password)
        time.sleep(1)

        #Start one tgt
        self.start_iscsi_tgt(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password)
        time.sleep(1)

        #Clean iscsi dirty        
        self.clean_iscsi_dirty(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password)

        #Logout iscsi
        self.do_iscsi_logout(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        self.iscsi_target_hostip[1])
        time.sleep(1)
        self.do_iscsi_logout(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        self.iscsi_target_hostip[0])
        time.sleep(1)

    def test(self):
        # Create rbd in the pool
        self.rbd_id = test_utils.create_rbd(self.pool_id, self.params)
        if self.rbd_id == None:
            raise exceptions.TestFail("rbd is not existed")
        else:
            LOG.info("RBD id is %d" % self.rbd_id)
            # Create iscsi
            self.iscsi_target_id = self._create_iscsi_target()
            time.sleep(1)
            target_multipath = len(self.iscsi_target_hostip)
            if target_multipath <= 2:
                raise exceptions.TestFail("Multipath is %d" % target_multipath)
            # Bind iscsi to rbd
            self.lun_id = self._create_iscsi_lun(self.iscsi_target_id, 
                                                 self.rbd_id)
            time.sleep(1)
            self.iscsi_actions(self.control_server_ip,
                   self.control_username,
                   self.control_password,
                   self.initiator_ip,
                   self.initiator_username,
                   self.initiator_password,
                   self.target_ip)

    def teardown(self):
        if self.lun_id is not None:
            self._delete_iscsi_lun(self.iscsi_target_id, self.lun_id)
        if self.iscsi_target_id is not None:
            self._delete_target(self.iscsi_target_id)
        if self.rbd_id is not None:
            self._delete_rbd(self.pool_id, self.rbd_id)
