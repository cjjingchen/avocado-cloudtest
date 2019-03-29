LOGS_SUMMARY = {
    'status_code': [200],
    'response_body': {
        'type': 'string',
        'items': {
            'type': 'array',
            'properties': {
                'category': {'type': 'string'},
                'cluster': {'type': 'string'},
                'end_time': {'type': 'string'},
                'msg': {'type': 'object',
                        'properties': {
                            'entity': {
                                'type': 'object',
                                'properties': {
                                    'initiator_ips': {'type': 'string'},
                                    'multipath': {'type': 'string'},
                                    'target_name': {'type': 'string'},
                                }
                            }
                        }
                        },
                'object': {'type': 'string'},
                'operation': {'type': 'string'},
                'start_time': {'type': 'string'},
                'state': {'type': 'string'},
                'user': {'type': 'string'},
            }
        },

        'pagenum': {'type': 'integer'},
        'preindex': {'type': 'integer'},
        'sufindex': {'type': 'integer'},

    }
}
