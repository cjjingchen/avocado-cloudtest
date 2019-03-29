import logging
import time
import re

from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib.clusters_client import ClustersClient
from cloudtest.tests.ceph_api.lib.pools_client import PoolsClient
from cloudtest.tests.ceph_api.lib.rbd_client import RbdClient
from cloudtest.tests.ceph_api.lib.servers_client import ServersClient
from cloudtest.tests.ceph_api.lib.groups_client import GroupsClient
from cloudtest.tests.ceph_api.lib.osd_client import OsdClient
from cloudtest.tests.ceph_api.lib.monitors_client import MonitorsClient
from cloudtest.tests.ceph_api.lib.iscsi_client import ISCSIClient
from cloudtest.tests.ceph_api.lib.gateway_client import GatewayClient
from cloudtest.tests.ceph_api.lib.remotebackup_client import RemoteBackupClient
from cloudtest import remote

LOG = logging.getLogger('avocado.test')


def prepare_resource(cluster=False, pool=False):
    pass


def create_cluster(params):
    """
    Prepare env for testing, especially creating cluster, etc

    :param params: the dict-like parameter
    """

    clusters_client = ClustersClient(params)
    cluster_name = 'cloudtest_' + utils_misc.generate_random_string(6)
    LOG.info("Try to create cluster %s" % cluster_name)
    create_cluster = {'name': cluster_name,
                      'addr': params.get('cluster_addr')}
    resp = clusters_client.create(**create_cluster)
    LOG.info(resp)
    return resp.body['id']


def delete_cluster(cluster_id, params):
    LOG.info("Try to delete cluster: %s" % cluster_id)
    clusters_client = ClustersClient(params)
    return clusters_client.delete_cluster(cluster_id)


def create_pool(params, flag=False, vgroup_id=None):
    """
    Prepare env for testing, this method is to create pool in the cluster

    :param params: the dict-like parameter
    """

    pools_client = PoolsClient(params)
    pool_name = 'cloudtest_' + utils_misc.generate_random_string(6)
    LOG.info("Try to create pool %s" % pool_name)
    if not vgroup_id:
        vgroup_id = get_available_vgroup(params)
    if params.get('NO_EC', "true") == "true":
        create_pool = {'name': pool_name,
                       'size': params.get('size', 2),
                       'group_id': params.get('rest_arg_group_id', 1),
                       'pg_num': params.get('rest_arg_pg_num', 64),
                       'vgroup_id': vgroup_id}
    else:
        create_pool = {'name': pool_name,
                       'group_id': params.get('rest_arg_group_id', 1),
                       'pg_num': params.get('rest_arg_pg_num', 64),
                       'vgroup_id': vgroup_id,
                       'safe_type': params.get('safe_type', 0),
                       'data_block_num': params.get('data_block_num', 2),
                       'code_block_num': params.get('code_block_num', 0),
                       'min_size': params.get('min_size', 1),
                       'max_bytes': params.get('max_bytes', 486547056640),
                       'write_mode': params.get("write_mode", "writeback"),
                       }
    pools_client.create(**create_pool)
    status = wait_for_pool_created(pools_client, pool_name)
    if not status:
        raise exceptions.TestFail('Failed to create pool %s' % pool_name)
    LOG.info('Create pool %s successfully !' % pool_name)
    resp = pools_client.query()
    for i in range(len(resp)):
        if resp[i]['name'] == pool_name:
            if flag:
                return resp[i]
            else:
                return resp[i]['id']


def wait_for_pool_created(client, pool_name, timeout=600):
    def is_pool_created():
        resp = client.query()
        for i in range(len(resp)):
            if resp[i]['name'] == pool_name \
                    and resp[i]['state'] == 1:
                return True
        return False

    return utils_misc.wait_for(is_pool_created, timeout, first=0, step=5,
                               text='Waiting for pool %s create.' %
                                    pool_name)


def create_pool_with_replicate_pg(replicate, pg_num, group_id, params):
    """
    Prepare env for testing, this method is to create pool in the cluster

    :param params: the dict-like parameter
    """

    pools_client = PoolsClient(params)
    pool_name = 'cloudtest_' + utils_misc.generate_random_string(6)
    LOG.info("Try to create pool %s" % pool_name)
    create_pool = {'name': pool_name,
                   'size': replicate,
                   'group_id': group_id,
                   'pg_num': pg_num}
    pools_client.create(**create_pool)
    time.sleep(60)
    resp = pools_client.query()
    for i in range(len(resp)):
        if resp[i]['name'] == pool_name:
            return resp[i]['id']


def get_available_pool_name_and_id(params):
    client = PoolsClient(params)
    pools = client.query()
    if not len(pools):
        raise exceptions.TestFail('No pool found!')
    pool_id = pools[0]['id']
    pool_name = pools[0]['name']
    return pool_name, pool_id


def delete_pool(pool_id, params):
    LOG.info("Try to delete pool: %s" % pool_id)
    pools_client = PoolsClient(params)
    return pools_client.delete_pool(pool_id)


def create_rbd(pool_id, params):
    """
      Prepare env for testing, this method is to create rbd in the pool

      :param params: the dict-like parameter
    """

    rbd_client = RbdClient(params)
    rbd_name = params.get('rbd_name',
                          'cloudtest_' + utils_misc.generate_random_string(6))
    LOG.info("Try to create rbd %s" % rbd_name)
    create_rbd = {'name': rbd_name,
                  'object_size': params.get('object_size', 10),
                  'capacity': params.get('capacity', 1024 * 1024 * 10),
                  'num': params.get('num', 1),
                  'shared': params.get('shared', 0)}
    rbd_client.create(pool_id, **create_rbd)
    status = wait_for_rbd_create(rbd_client, pool_id, rbd_name)
    if not status:
        raise exceptions.TestFail('Failed to create rbd %s!' % rbd_name)
    resp = rbd_client.query(pool_id)
    for i in range(len(resp)):
        if resp[i]['name'] == rbd_name:
            return resp[i]['id']
    raise exceptions.TestError('Create rbd %s failed' % rbd_name)


def create_rbd_with_capacity(pool_id, params, capacity, flag=True):
    """
      Prepare env for testing, this method is to create rbd in the pool

      :param params: the dict-like parameter
      :param flag: True/False, with different return value
    """

    rbd_client = RbdClient(params)
    rbd_name = 'cloudtest_' + utils_misc.generate_random_string(6)
    LOG.info("Try to create rbd %s" % rbd_name)
    create_rbd = {'name': rbd_name,
                  'object_size': params.get('object_size', 10),
                  'capacity': params.get('capacity', capacity),
                  'num': params.get('num', 1),
                  'shared': params.get('shared', 0)}
    rbd_client.create(pool_id, **create_rbd)
    status = wait_for_rbd_create(rbd_client, pool_id, rbd_name)
    if not status:
        raise exceptions.TestFail('Failed to create rbd %s!' % rbd_name)
    resp = rbd_client.query(pool_id)
    for i in range(len(resp)):
        if resp[i]['name'] == rbd_name:
            if flag:
                return resp[i]
            else:
                return resp[i]['id']
    raise exceptions.TestError('Create rbd %s failed' % rbd_name)


def wait_for_rbd_create(client, pool_id, rbd_name, timeout=100):
    def is_rbd_create():
        resp = client.query(pool_id)
        for i in range(len(resp)):
            if resp[i]['name'] == rbd_name \
                    and resp[i]['status'] in 'ready':
                return True
        return False

    return utils_misc.wait_for(is_rbd_create, timeout, first=0, step=5,
                               text='Waiting for rbd %s create.' %
                                    rbd_name)


def delete_rbd(pool_id, rbd_id, params):
    LOG.info("Try to delete rbd: %s" % rbd_id)
    rbd_client = RbdClient(params)
    return rbd_client.delete_rbd(pool_id, rbd_id)


def get_available_rbd(pool_id, params):
    rbd_client = RbdClient(params)
    resp = rbd_client.query(pool_id)
    if not len(resp) > 0:
        return create_rbd(pool_id, params)
    return resp[0]['id']


def get_available_disk(server_id, params):
    server_client = ServersClient(params)
    return server_client.get_server_disks(server_id)


def get_available_osd(server_id, params, timeout=300):
    """
    After cluster is deployed,maybe osd_capacity of server is null,
    then need to wait until os_capacity is filled!
    so I used this utils_misc.wait_for.
    """
    osd_client = OsdClient(params)

    def _is_osd_in_server():
        resp = osd_client.get_osd_capacity(server_id)
        if resp.get('osds'):
            return resp
        return False

    resp = utils_misc.wait_for(_is_osd_in_server, timeout, first=0, step=5,
                               text='Waiting for osd in server %s' % server_id)

    for i in range(len(resp['osds'])):
        if resp['osds'][i]['osdStatus'] == 'up':
            return resp['osds'][i]['osdId']


def get_down_osd(server_id, params):
    osd_client = OsdClient(params)
    resp = osd_client.get_osd_capacity(server_id)
    for i in range(len(resp['osds'])):
        if resp['osds'][i]['osdStatus'] == 'down':
            return resp['osds'][i]['osdId']


def _get_servers(server_client, query_server):
    # TCS data format changed
    result = server_client.query(**query_server)
    if isinstance(result, list):
        servers = result
    else:
        servers = result['items']
    return servers


def get_vip1_hostname(params):
    get_vip1_cmd = 'crm resource show VIP1'
    ceph_management_url = params.get('ceph_management_url')
    ceph_server_ip = get_ip_from_string(ceph_management_url)
    ceph_ssh_username = params.get('ceph_server_ssh_username',
                                        'root')
    ceph_ssh_password = params.get('ceph_server_ssh_password')
    session = remote.RemoteRunner(host=ceph_server_ip,
                                  username=ceph_ssh_username,
                                  password=ceph_ssh_password)
    logging.info("cmd of getting vip1 hostname is:%s" % get_vip1_cmd)
    vip1_result = session.run(get_vip1_cmd)
    session.session.close()
    vip1_hostname = vip1_result.stdout.split(':')[1].strip()
    return vip1_hostname


def get_available_server(params):
    vip1_hostname = get_vip1_hostname(params) if params.get('HA_Enable') == 'yes' else ''
    server_client = ServersClient(params)
    query_server = {'marker': 0, 'pagesize': 100}
    servers = _get_servers(server_client, query_server)
    if not len(servers) > 0:
        LOG.error("No available server found!")
        return None
    for server in servers:
        if len(server['mons']) == 0:
            continue
        # server must not be controller and HA's VIP server
        if server['state'] == 3 and server['status'] == 1 \
                and server['mons'][0]['role'] == 'follower' \
                and server['servername'] not in ['controller', vip1_hostname]:
            return server['id']
    return servers[0]['id']


def get_available_server_info(params, cluster_id):
    tmp = params['cluster_id']
    params['cluster_id'] = cluster_id
    query_server = {'marker': 0, 'pagesize': 100}
    server_client = ServersClient(params)
    params['cluster_id'] = tmp
    servers = _get_servers(server_client, query_server)
    if not len(servers) > 0:
        LOG.error("No available server found!")
        return None
    for server in servers:
        if len(server['mons']) == 0:
            continue
        if server['state'] == 3 and server['status'] == 1:
            return server
    return servers[0]


def get_available_host_ip(params):
    server_client = ServersClient(params)
    query_server = {'marker': 0, 'pagesize': 100}
    servers = _get_servers(server_client, query_server)
    if not len(servers) > 0:
        LOG.error("No available server found!")
        return None
    for server in servers:
        if len(server['mons']) == 0:
            continue
        if server['state'] == 3 and server['status'] == 1 \
                and server['mons'][0]['role'] == 'follower':
            return server['publicip']
    return servers[0]['publicip']


def get_server_id_by_name(params, server_name):
    server_client = ServersClient(params)
    query_server = {'marker': 0, 'pagesize': 100}
    servers = _get_servers(server_client, query_server)
    if not len(servers) > 0:
        LOG.error("No available server found!")
        return None

    for server in servers:
        if server['servername'] in server_name:
            return server['id']


def get_available_clusters(params):
    cluster_client = ClustersClient(params)
    clusters = cluster_client.query()
    return clusters


def get_available_group_bucket(params, group_id=None):
    """
    Get an available group id if group_id is None,
    or get an available group id other than group_id

    :param group_id: known group id
    :return:
    """
    group_client = GroupsClient(params)
    groups = group_client.list_groups(extra_url='?underlying=1')
    for group in groups:
        if not group_id or group['id'] != group_id:
            if group.get('items'):
                for item in group['items']:
                    if item.get('id'):
                        return group['id'], item['id']
            else:
                return group['id'], -1
        else:
            continue


def get_specified_targetip(params, target_id, ip_id):
    iscsi_client = ISCSIClient(params)
    targets = iscsi_client.query()
    for target in targets:
        if target['target_id'] == target_id:
            return target['host_ip'].split(',')[ip_id]


def wait_for_cluster_in_status(cluster_id, client, status, timeout=900):
    """
    Wait until the cluster is deployed

    :param cluster_id: the ID of cluster
    :param client: the instance of ClustersClient
    :param status: expected status to wait for
    """
    status_map = {'stopped': 2, 'deployed': 1}

    def _is_cluster_in_status():
        resp = client.query(cluster_id=cluster_id, validate=False)
        if (resp.body.get('status') == status_map.get(status) and
                    resp.body.get('state') == 1):
            return True
        return False

    return utils_misc.wait_for(_is_cluster_in_status, timeout, first=0, step=5,
                               text='Waiting for cluster %d is %s' % (
                               cluster_id,
                               status))


def wait_for_server_in_status(key, value, client, state, status, timeout=600):
    """
    Wait until the server is in expected status

    :param server_name: the name of the server
    :param client: the instance of ServersClient
    :param state: expected status to wait for
    """
    state_map = {'stopped': 0, 'added': 1, 'deploying': 2, 'active': 3,
                 'maintenance': 5}

    def _is_server_in_status():
        query_body = {'marker': 0, 'pagesize': 1024}
        result = client.query(**query_body)
        if isinstance(result, list):
            servers = result
        else:
            servers = result['items']
        for server in servers:
            if server.get(key) == value:
                if (server.get('state') == state_map.get(state) and
                            server.get('status') == status):
                    return True
                else:
                    return False
        return False

    return utils_misc.wait_for(_is_server_in_status, timeout, first=0, step=5,
                               text='Waiting for server %s is %s, '
                                    'and status is %d'
                                    % (value, state, status))


def wait_for_disk_info_in_osd(osd_client, server_id, osd_id, timeout=120):
    """
    Wait until disk info in osd

    :param client: the instance of OsdClient
    :param state: expected state to wait for
    """
    resp = ""
    def _is_disk_info_in_osd():
        try:
            resp = osd_client.get_osd_disk(server_id, osd_id)
            return True
        except:
            pass
        return False
    return utils_misc.wait_for(_is_disk_info_in_osd, timeout, first=0, step=5,
                               text='Waiting for disk info in osd ,server id is %s,osd id %s' % (
                               server_id, osd_id)), resp


def wait_for_pool_in_state(pool_id, client, state, timeout=900):
    """
    Wait until the pool is ready for using

    :param client: the instance of PoolClient
    :param state: expected state to wait for
    """
    status_map = {'adding': 0, 'ready': 1}

    def _is_pool_in_state():
        pools = client.query()
        for pool in pools:
            if pool.get('id') == int(pool_id):
                if pool.get('state') == status_map.get(state):
                    return True
        return False

    return utils_misc.wait_for(_is_pool_in_state, timeout, first=0, step=5,
                               text='Waiting for pool %d is %s' % (
                               pool_id, state))


def wait_for_remote_backup_or_restore_complete(id, client, state, timeout=60):
    """
    Wait until the remote backup or restore complete
    """
    status_map = {'restored': 2, 'backed_up': 2, 'backing_up': 1}

    def _is_in_state():
        extra_url = '/list_rbtasks?count=1024&begin_index=0'
        rbtasks = client.list_rbtasks(extra_url)
        for rbtask in rbtasks:
            if rbtask.get('id') == id:
                if rbtask.get('state') == status_map.get(state):
                    return True
        return False

    return utils_misc.wait_for(_is_in_state, timeout, first=0, step=5,
                               text='Waiting for remote backup or restore to complete!')


def delete_monitor(cluster_id, server_id, params, monitor_id=None):
    client = MonitorsClient(params)
    monitor_ids = []
    if not monitor_id:
        monitors = client.query(cluster_id, server_id)
        if not len(monitors) > 0:
            LOG.info('No monitor can be found on server %d' % server_id)
            return
        else:
            for monitor in monitors:
                monitor_ids.append(monitor.get('id'))

    else:
        monitor_ids.append(monitor_id)

    for id in monitor_ids:
        LOG.info("Try to delete monitor with ID: %s" % id)
        client.delete_monitor(cluster_id, server_id, id)
        time.sleep(5)


def delete_osd(server_id, params, osd_id=None):
    client = OsdClient(params)
    if osd_id:
        LOG.info("Try to delete osd with ID: %s" % osd_id)
        client.delete_osd(server_id, osd_id)
    else:
        resp = client.get_osd_capacity(server_id)
        for i in range(len(resp['osds'])):
            osd_id = resp['osds'][i]['osdId']
            LOG.info("Try to delete osd with ID: %s" % osd_id)
            client.delete_osd(server_id, osd_id)


def _get_disk_partition_list(control_server_ip, control_username,
                             control_password, initiator_ip, initiator_username,
                             initiator_password, is_login, target_name,
                             target_address):
    cmd = ' '
    cmd += 'iscsiadm -m discovery -t st -p %s; ' % target_address
    if is_login:
        cmd += 'iscsiadm -m node -T %s -p %s --login &&' % (target_name,
                                                            target_address)

    cmd += 'sleep 20; lsblk; '

    _, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                     control_password, initiator_ip,
                                     initiator_username, initiator_password,
                                     cmd)
    return buff


def _get_disk(buffer_before, buffer_after):
    pat = '.* disk'
    info = re.findall(pat, buffer_before)
    buffer_before_disk_list = []
    for i in range(len(info)):
        buffer_before_disk_list.append(info[i].split()[0])

    info = re.findall(pat, buffer_after)
    buffer_after_disk_list = []
    for i in range(len(info)):
        buffer_after_disk_list.append(info[i].split()[0])

    if len(buffer_before_disk_list) == len(buffer_after_disk_list):
        return None
    elif buffer_after_disk_list[len(buffer_after_disk_list) - 1] \
            not in buffer_before_disk_list[len(buffer_before_disk_list) - 1]:
        return buffer_after_disk_list[len(buffer_after_disk_list) - 1]
    else:
        for j in range(len(buffer_after_disk_list)):
            if buffer_after_disk_list[j] not in buffer_before_disk_list[j]:
                return buffer_after_disk_list[j]


def _write_data_to_iscsi(control_server_ip, control_username, control_password,
                         initiator_ip, initiator_username, initiator_password,
                         need_mk, create_data, disk, mount_point, file_name):
    time.sleep(10)
    cmd = ''
    if need_mk:
        cmd += 'echo yes | mkfs -t ext3 -c %s; sleep 10; ' % disk

    cmd += 'mount %s %s; sleep 10; ' % (disk, mount_point)

    if create_data:
        cmd += 'touch %s/%s; ' % (mount_point, file_name)

    # cmd += 'ls %s/%s; ' % (mount_point, file_name)
    cmd += 'ls %s' % mount_point

    find, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                        control_password, initiator_ip,
                                        initiator_username, initiator_password,
                                        cmd, file_name)

    if find:
        return True
    else:
        return False


def _logout_iscsi(control_server_ip, control_username, control_password,
                  initiator_ip, initiator_username, initiator_password,
                  mount_point, target_name, target_address):
    time.sleep(10)

    if mount_point is None:
        cmd = ''
    else:
        cmd = 'umount %s; ' % mount_point
    cmd += 'iscsiadm -m node -T %s -p %s --logout; sleep 10; ' % \
           (target_name, target_address)

    _, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                     control_password, initiator_ip,
                                     initiator_username, initiator_password,
                                     cmd)


def operate_iscsi(control_server_ip, control_username, control_password,
                  initiator_ip, initiator_username, initiator_password,
                  target_name, target_address, mount_point, file_name, need_mk,
                  create_data):
    is_login = False
    buff_before_login = _get_disk_partition_list(control_server_ip,
                                                 control_username,
                                                 control_password, initiator_ip,
                                                 initiator_username,
                                                 initiator_password, is_login,
                                                 target_name, target_address)

    is_login = True
    buff_after_login = _get_disk_partition_list(control_server_ip,
                                                control_username,
                                                control_password, initiator_ip,
                                                initiator_username,
                                                initiator_password, is_login,
                                                target_name, target_address)

    disk = _get_disk(buff_before_login, buff_after_login)
    disk = '/dev/%s' % disk

    find = _write_data_to_iscsi(control_server_ip, control_username,
                                control_password, initiator_ip,
                                initiator_username, initiator_password, need_mk,
                                create_data, disk, mount_point, file_name)
    if find:
        LOG.info("Find %s under %s" % (file_name, mount_point))
    else:
        LOG.info("Not found %s under %s" % (file_name, mount_point))

    _logout_iscsi(control_server_ip, control_username, control_password,
                  initiator_ip, initiator_username, initiator_password,
                  mount_point, target_name, target_address)

    return find


def modify_file(control_server_ip, control_username, control_password,
                initiator_ip, initiator_username, initiator_password, file_name,
                old_value_list, new_value_list):
    cmd_before = 'sed -i "s/'
    cmd_after = '/g" %s; ' % file_name
    cmd = ' '

    for i in range(len(old_value_list)):
        cmd += cmd_before + old_value_list[i] + "/" + new_value_list[i] + \
               cmd_after
        LOG.info("cmd is %s" % cmd)

    _, buff = utils.sshclient_execmd(control_server_ip, control_username,
                                     control_password, initiator_ip,
                                     initiator_username, initiator_password,
                                     cmd)
    return True


def iscsi_login_with_account(control_server_ip, control_username,
                             control_password, initiator_ip, initiator_username,
                             initiator_password, target_name, target_address):
    is_login = False
    buff_before_login = _get_disk_partition_list(control_server_ip,
                                                 control_username,
                                                 control_password,
                                                 initiator_ip,
                                                 initiator_username,
                                                 initiator_password, is_login,
                                                 target_name, target_address)
    is_login = True
    buff_after_login = _get_disk_partition_list(control_server_ip,
                                                control_username,
                                                control_password, initiator_ip,
                                                initiator_username,
                                                initiator_password, is_login,
                                                target_name, target_address)

    disk = _get_disk(buff_before_login, buff_after_login)

    if disk is not None:
        return True
    else:
        return False


def get_pool_id(env, params):
    if 'pools' in env:
        pool_id = env['pools']
    else:
        client = PoolsClient(params)
        pools = client.query()
        if not len(pools):
            vgroup_id = env.get('vgroup_id')
            pool_id = create_pool(params, vgroup_id=vgroup_id)
        else:
            pool_id = pools[0]['id']
        env['pools'] = pool_id
    LOG.info("pool_id is %s" % pool_id)
    return pool_id


def wait_for_gateway_created(client, gateway_name, timeout=600):
    def is_gateway_created():
        resp = client.query("gateway")
        for gateway in resp['items']:
            if gateway['name'] == gateway_name and gateway['recovery_mode'] == 'NORMAL' and gateway['node_num'] == \
                    gateway['node_OK_num']:
                return True
        return False

    return utils_misc.wait_for(is_gateway_created, timeout, first=0, step=5,
                               text='Waiting for gateway %s create.' %gateway_name)


def create_gateway(params):
    """
      Prepare env for iscsi test, this method is to create gateway

      :param params: the dict-like parameter
    """
    gateway_client = GatewayClient(params)

    gateway_name = 'cloudtest_gw_' + utils_misc.generate_random_string(6)
    create_gateway = {'name': gateway_name,
                      'services': params.get('services', 'iSCSI'),
                      'public_ip': params.get('public_ip', "192.168.1.50/24")}
    node_list = []
    server_id = get_available_server(params)
    sub_node = {"id": server_id,
                "interface": params.get('create_node_interface', 'eth0')}
    node_list.append(sub_node)

    resp = gateway_client.create(node_list, **create_gateway)

    # wait to make sure gateway created!
    wait_for_gateway_created(gateway_client, gateway_name)
    resp = gateway_client.query("gateway")
    LOG.info("Rest API esponse is: %s" % resp)

    for gateway in resp['items']:
        if gateway['name'] == gateway_name:
            return gateway['id']


def get_available_gateway(params):
    gateway_client = GatewayClient(params)

    resp = gateway_client.query("gateway")
    for gateway in resp['items']:
        if gateway['recovery_mode'] == 'NORMAL':
            return gateway['id']


def delete_gateway(gateway_id, params):
    LOG.info("Try to delete gateway: %s" % gateway_id)
    gateway_client = GatewayClient(params)
    return gateway_client.delete_gateway(gateway_id)


def update_env_vgroup(params, env):
    """
    update vgroup id in env when creating pool;
    """
    group_client = GroupsClient(params)
    group_id = params.get('rest_arg_group_id', 1)
    vgroups = group_client.query_logic_group(group_id)
    if len(vgroups) == 0:
        raise exceptions.TestFail("Failed to test_query_logic_group")
    vgroup_id = vgroups[0]['virtual_group_id']
    env['vgroup_id'] = vgroup_id


def get_available_vgroup(params):
    group_client = GroupsClient(params)
    group_id = params.get('rest_arg_group_id', 1)
    vgroups = group_client.query_logic_group(group_id)
    if len(vgroups) == 0:
        raise exceptions.TestError("No vgroups found in group %s, "
                                   "please check!" % group_id)
    return vgroups[0]['virtual_group_id']


def wait_for_available_vgroup(group_client, group_id, timeout=600):
    def exist_available_vgroup():
        vgroups = group_client.query_logic_group(group_id)
        if len(vgroups) > 0:
                return True
        return False

    return utils_misc.wait_for(exist_available_vgroup, timeout, first=0, step=5,
                               text='Waiting for available logic group.')


def get_available_backup_site(params):
    client = RemoteBackupClient(params)
    resp = client.get_backup_site_list()
    if not len(resp):
        raise exceptions.TestError("No backup client found, please check!")
    return resp[0]["uuid"]


def add_server(server_client, server_name, user_name, passwd, publicip,
               clusterip, managerip, parent_bucket):
    create_server_body = {'servername':server_name,
                          'username': user_name,
                          'passwd': passwd,
                          'publicip': publicip,
                          'clusterip': clusterip,
                          'managerip': managerip,
                          'parent_bucket': parent_bucket}

    resp_body = server_client.create(**create_server_body)
    body = resp_body.body
    status = wait_for_server_in_status('servername', create_server_body['servername'],
                                       server_client, 'added', 1, 1200)
    if not status:
        raise exceptions.TestFail("Failed to add server %s"
                                  % create_server_body['servername'])

    LOG.info('Create server %s successfully!'% body['properties'].get('name'))
    server_name = create_server_body['servername']

    return server_name


def expand_cluster(cluster_client, server_client, cluster_id, server_name):

    cluster_client.expand_cluster(cluster_id)
    status = wait_for_server_in_status('servername', server_name, server_client,
                                       'active', 1, 1200)
    if not status:
        raise exceptions.TestFail("Failed to expand cluster because server"
                                  " %s state wrong!" % server_name)
    LOG.info('Expand cluster successfully!')


def del_server(server_client, server_id):
    server_client.delete_server(server_id)

    body = {}
    servers = server_client.query(**body)
    for server in servers:
        if server.get('id') == server_id:
            raise exceptions.TestFail('Failed to delete server %s' % server_id)
    LOG.info('Delete server successfully !')

def get_osd_id_stateless(server_id, params, timeout=300):
    """
    After cluster is deployed,maybe osd_capacity of server is null,
    then need to wait until os_capacity is filled!
    so I used this utils_misc.wait_for.
    """
    osd_client = OsdClient(params)

    def _is_osd_in_server():
        resp = osd_client.get_osd_capacity(server_id)
        if resp.get('osds'):
            return resp
        return False

    resp = utils_misc.wait_for(_is_osd_in_server, timeout, first=0, step=5,
                               text='Waiting for osd in server %s' % server_id)

    for i in range(len(resp['osds'])):
        return resp['osds'][i]['osdId']


def get_ip_from_string(ceph_management_url):
    pattern_ipv4 = r'(((\d|[1-9]\d|1\d\d|2[0-5]\d)\.){3}(2[' \
                   r'0-5]\d|1\d\d|[1-9]\d|\d))'
    pattern_ipv6 = r'((([\da-fA-F]{1,4}):){7}[\da-fA-F]{1,4})'

    search_ipv4 = re.search(pattern_ipv4, ceph_management_url, re.I)
    if search_ipv4:
        logging.info('-----ipv4 match----------%s' % search_ipv4.group())
        return search_ipv4.group()

    search_ipv6 = re.search(pattern_ipv6, ceph_management_url, re.I)
    if search_ipv6:
        logging.info('-----ipv6 match----------%s' % search_ipv6.group())
        return search_ipv6.group()