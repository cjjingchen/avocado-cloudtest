QUERY_SERVER = {
    "marker": "marker",
    "pagesize": "pagesize",
}

CREATE_SERVER = {
    "servername": "servername",
    "publicip": "publicip",
    "clusterip": "clusterip",
    "managerip": "managerip",
    "username": "username",
    "passwd": "passwd",
    "parent_bucket": "parent_bucket",
}

START_MAINTENANCE= {
    'entity': {
        'operation': 'start_maintenance',
    }
}

STOP_MAINTENANCE= {
    'entity': {
        'operation': 'stop_maintenance',
    }
}

START_SERVER= {
    'entity': {
        'operation': 'start',
    }
}

STOP_SERVER= {
    'entity': {
        'operation': 'shutdown',
    }
}

RESTART_SERVER= {
    'entity': {
        'operation': 'restart',
    }
}

ADD_CEPHED_SERVER = {
    "username": "username",
    "passwd": "passwd",
    "publicip": "publicip",
    "managerip": "managerip",
}