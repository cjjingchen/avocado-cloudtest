notification = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'auth_pass': {'type': 'string'},
            'auth_user': {'type': 'string'},
            'enable_mailalert': {'type': 'integer'},
            'enable_trap': {'type': 'integer'},
            'mail_sender': {'type': 'string'},
            'smtp_auth': {'type': 'integer'},
            'smtp_port': {'type': 'integer'},
            'smtp_server': {'type': 'integer'},
            'smtp_starttls': {'type': 'integer'},
            'smtp_tlsssl': {'type': 'integer'}
        }
    }
}

warning = {
    'status_code': [200],
    'response_body': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'default_alertenabled': {'type': 'integer'},
                'default_period': {'type': 'integer'},
                'default_severity': {'type': 'integer'},
                'default_threshold': {'type': 'integer'},
                'default_trapenabled': {'type': 'integer'},
                'description': {'type': 'string'},
                'entity_type': {'type': 'integer'},
                'id': {'type': 'integer'},
                'threshold_type': {'type': 'integer'},
                'unit': {'type': 'integer'}
            }
        }
    }
}
