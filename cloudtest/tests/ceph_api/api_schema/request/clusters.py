CREATE_CLUSTER = {
    "name": "name",
    "addr": "addr",
}

START_CLUSTER = {
    'entity': {
        'operation': 'start',
    }
}

RESTART_CLUSTER = {
    'entity': {
        'operation': 'restart',
    }
}

STOP_CLUSTER = {
    'entity': {
        'operation': 'shutdown',
    }
}

DEPLOY_CLUSTER = {
    'entity': {
        'operation': 'deploy',
    }
}

EXPAND_CLUSTER = {
    'entity': {
        'operation': 'expand',
    }
}

UPGRADE_CLUSTER = {
    'entity': {
        'operation': 'upgrade',
    }
}
