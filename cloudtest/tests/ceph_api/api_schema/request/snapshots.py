create_snapshot = {
    'cluster_id': 'id',
    'pool_id': 'pool_id',
    'rbd_id': 'rbd_id',
    'snapshot_name': 'name',
}

clone_snapshot = {
    'standalone': 'true',
    'dest_pool': '',
    'dest_rbd': 'rbd2'
}

rollback_snapshot = {
    'to_snapshot': 0,
    'rbd_id': 0
}