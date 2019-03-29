CONF_RBPOLICY = {
    "src_ip": "src_ip",
    "des_cluster_id": "des_cluster_id",
    "src_host_id": "src_host_id",
    "des_host_id": "des_host_id",
    "des_ip": "des_ip",
}

START_RBTASK = {
    "rbd_id": "rbd_id",
}

START_RESTORE = {
    "snap_time": "snap_time",
}

CEPH_SITE = {
    'site_name': 'site_name',
    'configuration': 'configuration',
    'keyring': 'keyring',
    'site_type': 'ceph',
}

S3_SITE = {
    'access_key': 'access_key',
    'endpoint': 'endpoint',
    'site_name': 'site_name',
    'site_type': 'S3',
    'region': 'region',
    'secret_key': 'secret_key'
}

ADD_RBTASK = {
    "min": "",
    "backup_all": False,
    "dest_site": "",
    "pool_id": 1,
    "rbtask_name": "",
    "rbd_list": [],
    "frequency": "daily",
    "end_time": "",
    "startTime": "", #uctime
    "start_time": "",
    "startDt": "",
    "type": "full"
}

MODIFY_RBTASK = {
    "status": 0,
    "dest_site": "",
    "backup_all": False,
    "start_time": "2018/01/04 15:50:48",
    "last_batch": 'null',
    "modalType": "edit",
    "rbd_list": "1",
    # "startTime": "2018-01-04T07:50:48.000Z",
    "dest_site_name": "test",
    "src_pool": "test_pool_1",
    "last_time": "null",
    "endDt": "2018-01-27T00:00:00.000Z",
    "statusConvert": "\u65e0",
    "src_rbds": ["test_rbd_1"],
    "rbtask_name": "task_2_1",
    "created_at": "2018-01-04 01:01:32",
    "pool_id": 1,
    "deleted": False,
    "frequency": "monthly",
    "end_time": "2018/01/27",
    "next_schedule": "2018-01-04 15:50:48",
    # "startDt": "2018-01-04T07:50:48.000Z",
    "type": "full"
}

RBD_REMOTE_BACKUP = {
    "min": "2018-01-03T06:55:47.585Z",
    "backup_all": False,
    "dest_site": "",
    "start_time": "2018/01/04 15:50:48",
    "pool_id": 1,
    "rbd_list": [],
    "frequency": "manual",
    "end_time": "",
    "type": "full"
}

RBD_RESTORE = {
    "snap_time": "20180103145607",
    "dest_site": "",
    "id": "20180103145607",
    "cluster_id": "1",
    "rbd_id": "1",
    "pool_id": "1"
}
