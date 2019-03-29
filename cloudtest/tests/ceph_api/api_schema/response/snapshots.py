create = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'rbd_id': {'type': 'integer'},
            'pool_id': {'type': 'integer'},
            'cluster_id': {'type': 'integer'},
            'id': {'type': 'integer'},
            'name': {'type': 'string'},
            'size': {'type': 'integer'}
        }
    }
}