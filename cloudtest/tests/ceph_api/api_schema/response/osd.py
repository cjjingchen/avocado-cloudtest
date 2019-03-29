osd_disk = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'diskUsed': {'type': 'integer'},
            'diskName': {'type': 'string'},
            'diskTotal': {'type': 'integer'},
            'diskId': {'type': 'integer'},
        }
    }
}

query = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'used': {'type': 'integer'},
            'name': {'type': 'string'},
            'clusterid': {'type': 'integer'},
            'avail': {'type': 'integer'},
            'host': {'type': 'string'},
            'serverid': {'type': 'integer'},
            'id': {'type': 'integer'},
        }
    }
}
