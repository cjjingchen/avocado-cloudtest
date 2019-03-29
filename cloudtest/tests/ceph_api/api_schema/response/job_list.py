QUERY_JOB_LIST = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'items': {
            'type': 'array',
            'properties': {
                'context': {'type': 'object'},
            },

            'create_at': {'type': 'string'},
            'start_at': {'type': 'string'},
            'name': {'type': 'string'},
            'log_msg': {'type': 'string'},
            'deleted': {'type': 'bool'},
            'update_at': {'type':   'string'},
            'end_at': {'type': 'string'},
            'state': {'type': 'integer'},
            'current_step': {'type': 'integer'},
            'execute_time': {'type': 'null'},
            'running_steps': {'type': 'array'},
        },

        'pagenum': {'type': 'integer'},
        'preindex': {'type': 'integer'},
        'sufindex': {'type': 'integer'},
    }
}