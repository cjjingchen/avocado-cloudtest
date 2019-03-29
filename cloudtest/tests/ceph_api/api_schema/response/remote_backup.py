CONF_RBPOLICY = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'des_ip': {'type': 'string'},
            'des_host_id': {'type': 'integer'},
            'src_cluster_id': {'type': 'integer'},
            'src_ip': {'type': 'string'},
            'des_cluster_id': {'type': 'integer'},
            'src_host_id': {'type': 'integer'},
            'id': {'type': ['integer', 'null']},
            'src_pool_id': {'type': 'integer'},
        }
    }
}

DELETE_RBPOLICY = {
    'status_code': [200],
}

QUERY_RBPOLICY = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'des_ip': {'type': 'string'},
            'des_host_id': {'type': 'integer'},
            'src_ip': {'type': 'string'},
            'des_cluster_id': {'type': 'integer'},
            'src_host_id': {'type': 'integer'},
            'des_cluster_name': {'type': 'string'},
        }
    }
}

START_RBTASK = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'created_at': {'type': 'string'},
            'current_step': {'type': 'null'},
            'end_at': {'type': 'null'},
            'execute_time': {'type': 'null'},
            'running_steps': {'type': 'null'},
            'start_at': {'type': 'string'},
            'state': {'type': 'integer'},
            'type': {'type': 'string'},
            'update_at': {'type': 'string'},
        }
    }
}

RBTASK_LIST = {
    'status_code': [200],
    'response_body': {
        'type': 'array',
        'properties': {
            'created_at': {'type': 'string'},
            'current_step': {'type': ['integer', 'null']},
            'end_at': {'type': ['string', 'null']},
            'execute_time': {'type': ['string', 'null']},
            'running_steps': {'type': ['array', 'null']},
            'start_at': {'type': 'string'},
            'state': {'type': 'integer'},
            'type': {'type': 'string'},
            'update_at': {'type': 'string'},
        }
    }
}

RESTORE_LIST = {
    'status_code': [200],
    'response_body': {
        'type': 'array',
        'properties': {
            'time': {'type': 'string'},
        }
    }
}

START_RESTORE = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'created_at': {'type': 'string'},
            'current_step': {'type': 'null'},
            'end_at': {'type': 'null'},
            'execute_time': {'type': 'null'},
            'id': {'type': 'string'},
            'running_steps': {'type': 'null'},
            'start_at': {'type': 'string'},
            'state': {'type': 'integer'},
            'type': {'type': 'string'},
            'update_at': {'type': 'string'},
        }
    }
}

BACKUP_SITE_LIST = {
    'status_code': [200],
    'response_body': {
        'type': 'array',
        'properties': {
            'time': {'type': 'string'},
            'uuid': {'type': 'string'},
            'deleted': {'type': 'boolean'},
            'type': {'type': 'string'},
            'created_at': {'type': 'string'},
            'external_site': {'type': 'boolean'},
            'key': {'type': 'string'},
            'config': {'type': 'string'},
            'id': {'type': 'integer'},
            'name': {'type': 'string'},

        }
    }
}
