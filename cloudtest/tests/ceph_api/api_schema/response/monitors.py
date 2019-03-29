CREATE = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'server_id': {'type': 'integer'},
            'id': {'type': 'integer'},
            'running': {'type': 'string'},
            'name': {'type': 'string'},
            'state': {'type': 'string'}
        }
    }
}

QUERY = {
    'status_code': [200],
    'response_body': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'clusterid': {'type': 'integer'},
                'state': {'type': 'string'},
                'running': {'type': 'string'},
                'role': {'type': 'string'},
                'id': {'type': 'integer'}
            }
        }
    }
}