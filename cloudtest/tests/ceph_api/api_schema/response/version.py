QUERY_SOFTWARE_VERSION = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'bundles': [{
            'release': {'type': 'string'},
            'version': {'type': 'string'},
            'id': {'type': 'integer'},
            'components': {'type': 'array'},
            'name': {'type': 'string'},
        }
        ],

        'software': {
            'release': {'type': 'string'},
            'version': {'type': 'string'},
            'name': {'type': 'string'},

        }
    }
}