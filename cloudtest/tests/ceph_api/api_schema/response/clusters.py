create = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'addr': {'type': 'string'},
            'state': {'type': 'integer'},
            'id': {'type': 'integer'},
            'name': {'type': 'string'},
        }
    }
}


query_single = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'status': {'type': ['integer', 'null']},
            'addr': {'type': 'string'},
            'created_at': {'type': 'string'},
            'state': {'type': 'integer'},
            'version': {'type': ['string', 'null']},
            'id': {'type': 'integer'},
            'name': {'type': 'string'},
        }
    }
}

query = {
    'status_code': [200],
    'response_body': {
        'type': 'array',
        'items': [
            {
                'type': 'object',
            },
        ]
    }
}

query_summary = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'rawTotal': {'type': 'integer'},
            'deleteRatio': {'type': 'integer'},
            'poolActive': {'type': 'integer'},
            'poolTotal': {'type': 'integer'},
            'iopsWrite': {'type': 'integer'},
            'monTotal': {'type': 'integer'},
            'rawUsed': {'type': 'integer'},
            'dataTotal': {'type': 'integer'},
            'bandwidth': {'type': 'integer'},
            'osdTotal': {'type': 'integer'},
            'monActive': {'type': 'integer'},
            'dataUsed': {'type': 'integer'},
            'statusInfo': {'type': 'string'},
            'serversTotal': {'type': 'integer'},
            'serverActive': {'type': 'integer'},
            'osdActive': {'type': 'integer'},
            'rbdNum': {'type': 'integer'},
            'iopsRead': {'type': 'integer'},
        }
    }
}


expand = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'type': {'type': 'string'},
            'properties': {'type': 'object'},
            'start_at': {'type': 'string'},
            'running_steps': {'type': 'null'},
            'id': {'type': 'string'},
        }
    }
}
