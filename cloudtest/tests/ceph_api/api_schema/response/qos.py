enable = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            "wbw": {'type': 'integer'}, 
            "enable": {'type': 'string'}, 
            "riops": {'type': 'integer'}, 
            "wiops": {'type': 'integer'}, 
            "rbd_id": {'type': 'string'}, 
            "rbw": {'type': 'integer'}, 
            "created_at": {'type': 'string'}, 
            "pool_id": {'type': 'string'}, 
            "updated_at": {'type': 'string'}, 
            "deleted": {'type': 'integer'}, 
            "iops": {'type': 'integer'}, 
            "cluster_id": {'type': 'string'}, 
            "bw": {'type': 'integer'}, 
            "time": {'type': 'integer'}, 
            "id": {'type': 'integer'},
        }
    }
}

get_qos = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            "wbw": {'type': 'integer'}, 
            "enable": {'type': 'string'}, 
            "riops": {'type': 'integer'}, 
            "wiops": {'type': 'integer'}, 
            "rbd_id": {'type': 'integer'}, 
            "rbw": {'type': 'integer'}, 
            "created_at": {'type': 'string'}, 
            "pool_id": {'type': 'integer'}, 
            "updated_at": {'type': 'string'}, 
            "deleted": {'type': 'string'}, 
            "iops": {'type': 'integer'}, 
            "cluster_id": {'type': 'integer'}, 
            "bw": {'type': 'integer'}, 
            "id": {'type': 'integer'},
        }
    }
}

update = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            "wbw": {'type': 'integer'}, 
            "enable": {'type': 'string'}, 
            "riops": {'type': 'integer'}, 
            "wiops": {'type': 'integer'}, 
            "rbd_id": {'type': 'string'}, 
            "rbw": {'type': 'integer'}, 
            "created_at": {'type': 'string'}, 
            "pool_id": {'type': 'string'}, 
            "updated_at": {'type': 'string'}, 
            "deleted": {'type': 'integer'}, 
            "iops": {'type': 'integer'}, 
            "cluster_id": {'type': 'string'}, 
            "bw": {'type': 'integer'}, 
            "time": {'type': 'integer'}, 
            "id": {'type': 'integer'},
        }
    }
}

get_current_qos = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            "wbw": {'type': 'string'}, 
            "riops": {'type': 'string'}, 
            "rdelay": {'type': 'string'}, 
            "rbw": {'type': 'string'}, 
            "wdelay": {'type': 'string'}, 
            "iops": {'type': 'string'}, 
            "bw": {'type': 'string'}, 
            "wiops": {'type': 'string'}, 
        }
    }
}

disable = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            "success": {'type' :'boolean'}, 
        }
    }
}
