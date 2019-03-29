CREATE_GROUP = {
    'name': 'name',
    'max_size': 'max_size',
    'leaf_firstn': 'leaf_firstn',
}


RENAME_SUMMARY = {
    'name': 'name'
}


CREATE_BUCKET = {
    'name': 'name',
    'type': 'type',
    # 'parent_id' is optional in request.
}

MODIFY_BUCKET = {
    'target_group': 'target_group',
    # 'parent_id' is optional in request.
}