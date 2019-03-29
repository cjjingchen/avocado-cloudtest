QUERY_PHYDISKS = {
    'status_code': [200],
    'response_body': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'diskName': {'type': 'string'},
                'rotate': {'type': 'integer'},
                'capacity': {'type': 'string'},
                'diskuuid': {'type': 'string'},
                'controllerID': {'type': 'integer'},
                'slotID': {'type': 'integer'},
                'disktype': {'type': 'string'},
                'enclosureID': {'type': 'integer'},
                'seriaNo': {'type': 'string'},
                'location_led': {'type': 'integer'},
                'health': {'type': 'string'},
                'mode': {'type': 'string'},
                'manufacID': {'type': 'string'},
                'diskid': {'type': 'integer'}
            }
        }
    }
}

QUERY_DISKS = {
    'status_code': [200],
    'response_body': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'diskUsed': {'type': 'integer'},
                'diskTotal': {'type': 'integer'},
                'diskName': {'type': 'string'},
                'diskUuid': {'type': 'string'},
                'diskId': {'type': 'integer'}
            }
        }
    }
}

GROUP = {
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'},
        'name': {'type': 'string'}
    }
}

PARENT_BUCKET = {
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'},
        'name': {'type': 'string'}
    }
}

CPU = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
               'id': {'type': 'integer'},
               'cache': {'type': 'string'},
               'cores': {'type': 'integer'},
               'frequency': {'type': 'string'},
               'model_name': {'type': 'string'},
               'physical_id': {'type': 'integer'}
        }
    }
}

QUERY_NODE_DETAIL = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'status': {'type': 'integer'},
            'group': GROUP,
            'ram_usage': {'type': 'number'},
            'cpu_usage': {'type': 'number'},
            'phy_cpu_nm': {'type': 'integer'},
            'ram_size': {'type': 'string'},
            'servername': {'type': 'string'},
            'clusterid': {'type': 'integer'},
            'zabbixhostid': {'type': 'integer'},
            'publicip': {'type': 'string'},
            'parent_bucket': PARENT_BUCKET,
            'state': {'type': 'integer'},
            'logi_cpu_nm': {'type': 'integer'},
            'role': {'type': 'string'},
            'clusterip': {'type': 'string'},
            'cpu': CPU,
        }
    }
}

#'ram_usage': {'type': 'float'},
#'cpu_usage': {'type': 'float'},
