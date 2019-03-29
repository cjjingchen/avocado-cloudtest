VALIDATE = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'max_server': {'type': 'integer'},
            'state': {'type': 'string',
                      'enum': ['valid', 'invalid']},
            'max_cluster': {'type': 'integer'},
            'max_capacity': {'type': 'integer'},
            'type': {'type': 'string',
                     'enum': ['official', 'trial']},
            'company': {'type': 'string'},
            'product': {'type': 'string'},
            'expiration': {'type': 'string'}
        }
    }
}

UPDATE = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'max_server': {'type': 'integer'},
            'state': {'type': 'string',
                      'enum': ['valid', 'invalid']},
            'max_cluster': {'type': 'integer'},
            'max_capacity': {'type': 'integer'},
            'type': {'type': 'string',
                     'enum': ['official', 'trial']},
            'company': {'type': 'string'},
            'product': {'type': 'string'},
            'expiration': {'type': 'string'}
        }
    }
}


GET_LICENSE = {
    'status_code': [200],
    'response_body': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'max_server': {'type': 'integer'},
                'state': {'type': 'string',
                          'enum': ['valid', 'invalid']},
                'max_cluster': {'type': 'integer'},
                'max_capacity': {'type': 'integer'},
                'type': {'type': 'string',
                         'enum': ['official', 'trial']},
                'company': {'type': 'string'},
                'product': {'type': 'string'},
                'expiration': {'type': 'string'}
            }
        }
    }
}
