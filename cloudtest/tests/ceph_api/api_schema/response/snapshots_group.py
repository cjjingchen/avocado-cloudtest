CREATE = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'cluster_id': {'type': 'string'},
            'create_at': {'type': 'string'},
            'delete_at': {'type': 'null'},
            'id': {'type': 'integer'},
            'name': {'type': 'string'},
            'rbd_count': {'type': 'integer'},
            'status': {'type': 'integer'},
            'size': {'type': 'integer'},
        }
    }
}