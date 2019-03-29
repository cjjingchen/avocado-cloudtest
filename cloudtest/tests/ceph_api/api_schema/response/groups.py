NEW_GROUP = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'deleted': {'type': 'integer'},
            'leaf_firstn': {'type': 'string'},
            'cluster_id': {'type': 'integer'},
            'deployed': {'type': 'integer'},
            'id': {'type': 'integer'},
            'max_size': {'type': 'integer'},
        }
    }
}


LIST_GROUPS = {
    'status_code': [200],
    'response_body': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'data_capacity_total': {'type': 'integer'},
                'data_capacity_used': {'type': 'integer'},
                'id': {'type': 'integer'},
                'leaf_firstn': {'type': 'string'},
                'logic_group': {'type': 'array'},
                'name': {'type': 'string'},
                'physical_capacity_total': {'type': 'integer'},
                'physical_capacity_used': {'type': 'integer'},
            }
        }
    }
}


DELETE_GROUP = {
    'status_code': [204],
}


NEW_BUCKET = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'name': {'type': 'string'},
            'parent_id': {'type': 'integer'},
            'type': {'type': 'string'},
            'type_id': {'type': 'integer'},
        }
    }
}
