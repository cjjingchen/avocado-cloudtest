create = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'write_bytes_sec': {'type': 'number'},
            'name': {'type': 'string'},
            'deduplication': {'type': 'boolean'},
            'read_op_per_sec': {'type': 'number'},
            'size_kb': {'type': 'integer'},
            'write_op_per_sec': {'type': 'number'},
            'rbd_count': {'type': 'integer'},
            'crush_ruleset': {'type': 'integer'},
            'pg_num': {'type': 'integer'},
            'dedup_rate': {'type': 'integer'},
            'read_bytes_sec': {'type': 'number'},
            'group_id': {'type': 'integer'},
            'id': {'type': 'integer'},
            'size': {'type': 'integer'},
        }
    }
}

query = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'crush_ruleset': {'type': 'integer'},
            'dedup_rate': {'type': 'integer'},
            'deduplication': {'type': 'boolean'},
            'group_id': {'type': 'integer'},
            'id': {'type': 'integer'},
            'name': {'type': 'string'},
            'pg_num': {'type': 'integer'},
            'rbd_count': {'type': 'integer'},
            'read_bytes_sec': {'type': 'number'},
            'read_op_per_sec': {'type': 'number'},
            'size': {'type': 'integer'},
            'size_kb': {'type': 'integer'},
            'write_bytes_sec': {'type': 'number'},
            'write_op_per_sec': {'type': 'number'}
        }
    }
}
