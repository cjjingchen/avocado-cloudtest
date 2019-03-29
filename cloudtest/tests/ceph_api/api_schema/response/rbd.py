create = {
    'status_code': [200],
    'response_body': {
        "type": "object",
        "properties": {
            "properties": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "context": {
                        "type": "object",
                        "properties": {
                            "poolName": {"type": "string"},
                            "num": {"type": "integer"},
                            "clusterId": {"type": "string"},
                            "name": {"type": "string"},
                            "size": {"type": "integer"}
                        }
                    }
                }
            },
            "start_at": {"type": "string"},
            "name": {"type": "string"},
            "log_msg": {"type": "null"},
            "deleted": {"type": "integer"},
            "running_steps": {"type": "null"},
            "created_at": {"type": "string"},
            "update_at": {"type": "string"},
            "end_at": {"type": "null"},
            "state": {"type": "integer"},
            "cluster_id": {"type": "string"},
            "current_step": {"type": "null"},
            "execute_time": {"type": "null"},
            "id": {"type": "string"}
        }
    }
}

query = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'clients': {'type': 'null'},
            'create_time': {'type': 'string'},
            'format': {'type': 'integer'},
            'id': {'type': 'integer'},
            'is_backup': {'type': 'integer'},
            'is_rb_policy_setting': {'type': 'integer'},
            'name': {'type': 'string'},
            'objects': {'type': 'integer'},
            'order': {'type': 'integer'},
            'parent': {'type': 'integer'},
            'pool': {'type': 'string'},
            'pool_id': {'type': 'integer'},
            'size': {'type': 'integer'},
            'snapshot_count': {'type': 'integer'},
            'status': {'type': 'integer'},
            'used': {'type': 'integer'},
        }
    }
}

query_list = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'items': {
            'type': 'array',
            'properties': {
                'clients': {'type': 'null'},
                'create_time': {'type': 'string'},
                'format': {'type': 'integer'},
                'id': {'type': 'integer'},
                'is_backup': {'type': 'integer'},
                'is_rb_policy_setting': {'type': 'integer'},
                'name': {'type': 'string'},
                'objects': {'type': 'integer'},
                'order': {'type': 'integer'},
                'parent': {'type': 'integer'},
                'pool': {'type': 'string'},
                'pool_id': {'type': 'integer'},
                'size': {'type': 'integer'},
                'snapshot_count': {'type': 'integer'},
                'status': {'type': 'integer'},
                'used': {'type': 'integer'},
            }
        },
        'pagenum': {'type': 'string'},
        'preindex': {'type': 'string'},
        'sufindex': {'type': 'string'},
    }
}

delay_delete_list = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'pool_name': {'type': 'string'},
            'used': {'type': 'integer'},
            'name': {'type': 'string'},
            'pool_id': {'type': 'integer'},
            'delayed_time': {'type': 'string'},
            'id': {'type': 'integer'},
            'size': {'type': 'integer'},
        }
    }
}
