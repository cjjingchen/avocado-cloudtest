import logging
import os
import threading

from avocado.core import test
from avocado.core import exceptions
from cloudtest import remote
from cloudtest import utils_misc
from cloudtest import data_dir
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.groups_client import GroupsClient
from cloudtest.tests.ceph_api.lib.clusters_client import ClustersClient
from cloudtest.tests.ceph_api.lib.servers_client import ServersClient
from cloudtest.tests.ceph_api.lib.pools_client import PoolsClient
from cloudtest.tests.ceph_api.lib.rbd_client import RbdClient
from cloudtest.tests.ceph_api.lib.osd_client import OsdClient


LOG = logging.getLogger('avocado.test')


class TestGroup(test.Test):
    """
    Test group can separate the data io from customized domain
    """
    def __init__(self, params, env):
        self.params = params
        self.clusters_client = ClustersClient(params)
        self.body = {}
        self.env = env
        self.cluster_id = None
        self.host_group_name = 'host_group_' \
                               + utils_misc.generate_random_string(6)
        self.host_group_id = None
        self.host_group_pool_id = None
        self.host_group_pool_name = None
        self.host_group_rbd_id = None
        self.host_group_rbd_name = None
        self.host_group_servers_id = []
        self.rack_group_name = 'rack_group_' \
                               + utils_misc.generate_random_string(6)
        self.rack_group_id = None
        self.rack_group_pool_id = None
        self.rack_group_pool_name = None
        self.rack_group_rbd_id = None
        self.rack_group_rbd_name = None
        self.rack_group_servers_id = []
        self.dstpath = '/root'
        self.workload_path = data_dir.CEPH_API_SCENARIOS_TEST_DIR
        self.fio_version = self.params.get('fio_version')
        self.fio_working_path = \
            self.fio_version[0:len(self.fio_version) - len('.tar.gz')]
        self.mid_host_ip = \
            self.params.get('ceph_management_url').split(':')[1].strip('/')
        self.mid_host_user = self.params.get('ceph_server_ssh_username')
        self.mid_host_password = self.params.get('ceph_server_ssh_password')
        self.end_host_user = self.params.get('ceph_node_ssh_username')
        self.end_host_password = self.params.get('ceph_node_ssh_password')
        self.rw = self.params.get('rw', 'randrw')
        self.bs = self.params.get('bs', '8k')
        self.iodepth = self.params.get('iodepth', 128)
        self.runtime = self.params.get('runtime', 120)
        self.rwmixread = self.params.get('rwmixread', 70)
        self.end_host_ip = None

    def setup(self):
        """
        Set up before executing test
        """
        LOG.info("Try to create cluster cloudtest_cluster")
        create_cluster = {'name': self.params.get('cluster_name',
                                                  'cloudtest_cluster'),
                          'addr': self.params.get('cluster_addr', 'vm')}
        resp = self.clusters_client.create(**create_cluster)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestSetupFail(
                "Create cluster failed: %s" % self.body)
        self.cluster_id = resp.body.get('id')
        LOG.info("Created cluster successfully!")
        self.params['cluster_id'] = self.cluster_id
        self.servers_client = ServersClient(self.params)
        self.group_client = GroupsClient(self.params)
        self.pool_client = PoolsClient(self.params)
        self.rbd_client = RbdClient(self.params)
        self.osd_client = OsdClient(self.params)

    def _copy_fio_package_to_host(self):
        self.end_host_ip = test_utils.get_available_host_ip(self.params)
        self.fio_working_path = \
            self.fio_version[0:len(self.fio_version) - len('.tar.gz')]
        LOG.info('Copy file %s from local to %s' % (self.fio_version,
                                                    self.mid_host_ip))
        remote.scp_to_remote(host=self.mid_host_ip,
                             port=22,
                             username=self.mid_host_user,
                             password=self.mid_host_password,
                             local_path=os.path.join(self.workload_path,
                                                     self.fio_version),
                             remote_path=self.dstpath)
        LOG.info('Copy file %s from %s to %s' % (self.fio_version,
                                                 self.mid_host_ip,
                                                 self.end_host_ip))
        remote.scp_between_remotes(src=self.mid_host_ip,
                                   dst=self.end_host_ip,
                                   port=22,
                                   s_passwd=self.mid_host_password,
                                   d_passwd=self.end_host_password,
                                   s_name=self.mid_host_user,
                                   d_name=self.end_host_user,
                                   s_path=os.path.join(self.dstpath,
                                                       self.fio_version),
                                   d_path=self.dstpath)

    def _write_rbd(self, pool_name, rbd_name, flag=False):
        cmd1 = 'cd %s;' % self.fio_working_path
        cmd2 = './fio -ioengine=rbd -clientname=admin -pool=%s ' % \
               pool_name
        cmd3 = '-rw=%s -rwmixread=%s -bs=%s -iodepth=%s -numjobs=1 -direct=1 ' % \
               (self.rw, self.rwmixread, self.bs, self.iodepth)
        cmd4 = '-runtime=%s -group_reporting -rbdname=%s -name=mytest' % \
               (self.runtime, rbd_name)
        cmd = cmd1 + cmd2 + cmd3 + cmd4
        if flag:
            cmd = 'tar -xzvf %s;' % self.fio_version + cmd
        LOG.info("cmd = %s" % cmd)

        remote.run_cmd_between_remotes(mid_host_ip=self.mid_host_ip,
                                       mid_host_user=self.mid_host_user,
                                       mid_host_password
                                       =self.mid_host_password,
                                       end_host_ip=self.end_host_ip,
                                       end_host_user=self.end_host_user,
                                       end_host_password
                                       =self.end_host_password,
                                       cmd=cmd,
                                       timeout=1000)

    def _create_group(self, name, leaf_firstn):
        group_body = {'name': name,
                      'max_size': 10,
                      'leaf_firstn': leaf_firstn}
        resp_body = self.group_client.create_group(**group_body)
        body = resp_body.body
        if 'id' not in body:
            raise exceptions.TestFail("Create group policy failed")
        LOG.info("Created group '%s' with id: %s"
                 % (body['name'], body['id']))
        return body['id']

    def _create_bucket(self, group_id):
        create_body = {'name':
                           'cloudtest_bucket_'
                           + utils_misc.generate_random_string(6),
                       'type': 'rack'}
        resp_body = self.group_client.create_bucket(group_id, **create_body)
        body = resp_body.body
        if 'id' not in body:
            raise exceptions.TestFail("Create bucket failed")
        LOG.info("Created bucket '%s' with id: %s"
                 % (body['name'], body['id']))
        return body['id']

    def _create_server(self, request_body):
        if not request_body.get('parent_bucket'):
            group_id, parent_id = \
                test_utils.get_available_group_bucket(self.params)
            request_body.update({'parent_bucket': parent_id})
        resp_body = self.servers_client.create(**request_body)
        body = resp_body.body
        status = test_utils.wait_for_server_in_status(
            'servername', request_body['servername'], self.servers_client,
            'added', 1, int(self.params.get('add_host_timeout', 600)))
        if not status:
            raise exceptions.TestFail("Failed to add server %s"
                                      % request_body['servername'])
        LOG.info('Create server %s successfully!'
                 % body['properties'].get('name'))

    def _add_three_hosts(self, kwargs):
        body = {}
        for k, v in self.params.items():
            if kwargs in k:
                new_key = k.split(kwargs)[1]
                body[new_key] = v
        LOG.info("body = %s" % body)
        i = 1
        threads = []
        while body.get('servername_%d' % i):
            tmp = 'servername_%d' % i
            servername = body.get(tmp, 'cloudtest_server_%d' % i)
            tmp = 'username_%d' % i
            username = body.get(tmp, 'root')
            tmp = 'password_%d' % i
            password = body.get(tmp, 'lenovo')
            tmp = 'publicip_%d' % i
            publicip = body.get(tmp)
            tmp = 'clusterip_%d' % i
            clusterip = body.get(tmp)
            tmp = 'parent_bucket_%d' % i
            parent_bucket = body.get(tmp)
            create_server_body = {'servername': servername,
                                  'username': username,
                                  'passwd': password,
                                  'publicip': publicip,
                                  'clusterip': clusterip,
                                  'parent_bucket': parent_bucket}
            t = threading.Thread(target=self._create_server,
                                 args=[create_server_body])
            threads.append(t)
            i = i + 1

        # waiting for all servers ready
        for t in threads:
            t.setDaemon(True)
            t.start()

        for i in range(0, len(threads)):
            try:
                threads[i].join(600)
            except Exception as details:
                LOG.exception('Caught exception waiting for server %d added : %s'
                              % (i, details))

    def _deploy_cluster(self):
        self.clusters_client.deploy_cluster(self.cluster_id)
        status = test_utils.wait_for_cluster_in_status(self.cluster_id,
                                                       self.clusters_client,
                                                       'deployed',
                           int(self.params.get('deploy_host_timeout', 900)))
        if not status:
            raise exceptions.TestFail("Failed to deploy cluster %d" %
                                      self.cluster_id)
        LOG.info("Deploy cluster %d successfully!" % self.cluster_id)

    def _create_pool(self, group_id):
        pool_name = 'cloudtest_' + utils_misc.generate_random_string(6)
        LOG.info("Try to create pool %s" % pool_name)
        create_pool = {'name': pool_name,
                       'size': self.params.get('pool_size', 3),
                       'group_id': group_id,
                       'pg_num': self.params.get('pg_num', 128)}
        resp = self.pool_client.create(**create_pool)
        status = self._wait_for_pool_create(pool_name)
        if not status:
            raise exceptions.TestFail('Failed to create pool %s' % pool_name)
        LOG.info('Create pool %s successfully !' % pool_name)
        pool_id = resp.body['properties']['context']['pool_id']
        return pool_id, pool_name

    def _wait_for_pool_create(self, pool_name, timeout=1000):
        def is_pool_create():
            resp = self.pool_client.query()
            for i in range(len(resp)):
                if resp[i]['name'] == pool_name \
                        and resp[i]['state'] == 1 \
                        and resp[i]['size'] == 3 \
                        and resp[i]['pg_num'] == 128:
                    return True
            return False

        return utils_misc.wait_for(is_pool_create, timeout, first=0, step=5,
                                   text='Waiting for pool %s create.' %
                                        pool_name)

    def _create_rbd(self, pool_id, rbd_name):
        LOG.info("Try to create rbd %s" % rbd_name)
        create_rbd = {'name': rbd_name,
                      'object_size': self.params.get('object_size', 10),
                      'capacity': self.params.get('capacity', 1024 * 1024 * 1024)}
        self.rbd_client.create(pool_id, **create_rbd)
        status = self._wait_for_rbd_in_status(pool_id, rbd_name, 'ready')
        if not status:
            raise exceptions.TestFail('Failed to create rbd %s!' % rbd_name)
        resp = self.rbd_client.query(pool_id)
        for i in range(len(resp)):
            if resp[i]['name'] == rbd_name:
                return resp[i]['id']
        raise exceptions.TestError('Create rbd %s failed' % rbd_name)

    def _wait_for_rbd_in_status(self, pool_id, rbd_name, status, timeout=300):
        status_map = {'copying': 6, 'ready': 0}

        def is_rbd_create():
            resp = self.rbd_client.query(pool_id)
            for i in range(len(resp)):
                if resp[i]['name'] == rbd_name:
                    if resp[i]['status'] == status_map[status]:
                        return True
            return False

        return utils_misc.wait_for(is_rbd_create, timeout, first=0, step=5,
                                   text='Waiting for rbd %s create.' %
                                        rbd_name)

    def _migrate_rbd(self, src_pool_id, des_pool_id, rbd_id, rbd_name):
        LOG.info("Try to migrate rbd %s" % rbd_name)
        move_rbd = {'target_pool': des_pool_id}
        resp = self.rbd_client.migrate(src_pool_id, rbd_id, **move_rbd)
        if not resp and utils.verify_response(self.body, resp):
            raise exceptions.TestFail("Migrate rbd failed: %s" % self.body)
        status = self._wait_for_rbd_in_status(des_pool_id, rbd_name, 'ready')
        if not status:
            raise exceptions.TestFail('Failed to migrate rbd %s!' % rbd_name)
        LOG.info('Migrate rbd %s successfully !' % rbd_name)

    def _get_servers_id(self):
        query_server = {'marker': 0, 'pagesize': 100}
        servers = self.servers_client.query(**query_server)
        if not len(servers) > 0:
            raise exceptions.TestFail("No available server found!")
        for server in servers:
            if server['group']['id'] == str(self.host_group_id):
                self.host_group_servers_id.append(server['id'])
            elif server['group']['id'] == str(self.rack_group_id):
                self.rack_group_servers_id.append(server['id'])
        LOG.info('Host group servers: %s' % self.host_group_servers_id)
        LOG.info('Rack group servers: %s' % self.rack_group_servers_id)

    def _get_osd_capacity(self, server_id):
        resp = self.osd_client.get_osd_capacity(server_id)
        if not len(resp) > 0:
            raise exceptions.TestFail("Query osd capacity failed")
        return resp.get('capacityUsed')

    def _get_osd_capacity_within_group(self, group_tag):
        total_capacity_used = 0
        if group_tag in 'host_group_':
            for server_id in self.host_group_servers_id:
                total_capacity_used = total_capacity_used + \
                                      self._get_osd_capacity(server_id)
        elif group_tag in 'rack_group_':
            for server_id in self.rack_group_servers_id:
                total_capacity_used = total_capacity_used + \
                                      self._get_osd_capacity(server_id)
        return total_capacity_used

    def test(self):
        """
        1. Create host group with host level, and add 3 hosts to this group
        2. Create host group with rack level, and add 3 other hosts to this group
        3. Deploy cluster
        4. Create pool in host group, create rbd in this pool,
        and execute FIO r/w, check r/w works ok
        5. Create pool in rack group, create rbd in this pool,
        and execute FIO r/w, check r/w works ok
        6. check osd capacity is changed only in the osd within r/w group
        7. Rbd migration: migrate rbd from pool 1 to pool 2,
        and execute FIO r/w, check r/w works ok
        8. Down one host from one group, and then w/r data in other group
        check data r/w in other group works ok
        """
        # Step 1: Create host group with host level, and add 3 hosts
        self.host_group_id = self._create_group(self.host_group_name, 'host')
        host_bucket_id = self._create_bucket(self.host_group_id)
        self.params['host_group_parent_bucket_1'] = host_bucket_id
        self.params['host_group_parent_bucket_2'] = host_bucket_id
        self.params['host_group_parent_bucket_3'] = host_bucket_id
        self._add_three_hosts("host_group_")
        LOG.info("Added 3 hosts to group %s successfully!"
                 % self.host_group_name)

        # Step 2: Create host group with rack level, and add 3 hosts
        self.rack_group_id = self._create_group(self.rack_group_name, 'rack')
        rack_bucket_id_1 = self._create_bucket(self.rack_group_id)
        rack_bucket_id_2 = self._create_bucket(self.rack_group_id)
        rack_bucket_id_3 = self._create_bucket(self.rack_group_id)
        self.params['rack_group_parent_bucket_1'] = rack_bucket_id_1
        self.params['rack_group_parent_bucket_2'] = rack_bucket_id_2
        self.params['rack_group_parent_bucket_3'] = rack_bucket_id_3
        self._add_three_hosts("rack_group_")
        LOG.info("Added 3 hosts to group %s successfully!"
                 % self.rack_group_name)

        # Step 3: deploy cluster
        self._deploy_cluster()
        self._get_servers_id()

        # Step 4:create pool in host group, rbd, do FIO r/w, check r/w works ok
        self._copy_fio_package_to_host()
        self.host_group_pool_id, self.host_group_pool_name = \
            self._create_pool(self.host_group_id)
        self.host_group_rbd_name = 'cloudtest_' \
                                   + utils_misc.generate_random_string(6)
        self.host_group_rbd_id = self._create_rbd(self.host_group_pool_id,
                                                  self.host_group_rbd_name)
        LOG.info("Create rbd %s in pool %s" % (self.host_group_rbd_name,
                                               self.host_group_pool_id))
        self._write_rbd(self.host_group_pool_name,
                        self.host_group_rbd_name, flag=True)

        # Step 5:create pool in rack group, rbd, do FIO r/w, check r/w works ok
        self.rack_group_pool_id, self.rack_group_pool_name = \
            self._create_pool(self.rack_group_id)
        self.rack_group_rbd_name = 'cloudtest_' \
                                   + utils_misc.generate_random_string(6)
        self.rack_group_rbd_id = self._create_rbd(self.rack_group_pool_id,
                                                  self.rack_group_rbd_name)
        LOG.info("Create rbd %s in pool %s" % (self.rack_group_rbd_id,
                                               self.rack_group_pool_id))
        capacity_used_before = self._get_osd_capacity_within_group('host_group_')
        LOG.info("The previous used capacity is %s" % capacity_used_before)
        self._write_rbd(self.rack_group_pool_name,
                        self.rack_group_rbd_name, flag=False)

        # Step 6:check osd capacity is changed
        # only in the osd within r/w group
        capacity_used_after = self._get_osd_capacity_within_group('host_group_')
        LOG.info("Later used capacity is %s" % capacity_used_after)
        if capacity_used_after < capacity_used_before*0.95:
            raise exceptions.TestFail("Do r/w in the osd of rack group, "
                                      "affect the used capacity of host group!")

        # Step 7:Rbd migration: migrate rbd from pool 1 to pool 2
        self._migrate_rbd(self.rack_group_pool_id, self.host_group_pool_id,
                          self.rack_group_rbd_id, self.rack_group_rbd_name)
        self._write_rbd(self.host_group_pool_name,
                        self.rack_group_rbd_name, flag=False)

        # Step 8:Down one host from one group,
        # and then w/r data in other group
        test_utils.delete_osd(self.rack_group_servers_id[0], self.params)
        self.servers_client.delete_server(self.rack_group_servers_id[0])
        self._write_rbd(self.host_group_pool_name,
                        self.host_group_rbd_name, flag=False)

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        if self.fio_working_path is not None:
            # delete files
            cmd_mid = 'rm -rf %s' % (os.path.join(self.dstpath, self.fio_version))
            cmd1 = 'pkill fio || true; '
            cmd2 = 'rm -rf %s %s' % (os.path.join(self.dstpath, self.fio_version),
                                 os.path.join(self.dstpath, self.fio_working_path))
            cmd = cmd1 + cmd2
            remote.run_cmd_between_remotes(mid_host_ip=self.mid_host_ip,
                                           mid_host_user=self.mid_host_user,
                                           mid_host_password
                                           =self.mid_host_password,
                                           end_host_ip=self.end_host_ip,
                                           end_host_user=self.end_host_user,
                                           end_host_password
                                           =self.end_host_password,
                                           cmd=cmd,
                                           cmd_mid=cmd_mid)
        if self.host_group_pool_id and self.host_group_rbd_id:
            self.rbd_client.delete_rbd(self.host_group_pool_id,
                                       self.host_group_rbd_id)
        if self.host_group_pool_id and self.rack_group_rbd_id:
            self.rbd_client.delete_rbd(self.host_group_pool_id,
                                       self.rack_group_rbd_id)
        if self.host_group_pool_id:
            self.pool_client.delete_pool(self.host_group_pool_id)
        if self.rack_group_pool_id:
            self.pool_client.delete_pool(self.rack_group_pool_id)
