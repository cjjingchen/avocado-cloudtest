CREATE_POOL_NO_EC = {
    'name': 'pool_name',
    'pg_num': 'pg_num',
    'size': 'size',
    'group_id': 'group_id',
    'vgroup_id': 'vgroup_id',
}

CREATE_POOL = {
    'name': 'pool_name',
    'pg_num': 'pg_num',
    'group_id': 'group_id',
    'vgroup_id': 'vgroup_id',
    'safe_type': 'safet_type',
    'data_block_num': 'data_block_num',
    'code_block_num': 'code_block_num',
    'min_size': 'min_size',
    'max_bytes': 'max_bytes',
    'write_mode': 'write_mode',
}

UPDATE_POOL_NO_EC = {
    'name': 'pool_name',
    'pg_num': 'pg_num',
    'size': 'size',
    'group_id': 'group_id',
    'vgroup_id': 'vgroup_id'
}

UPDATE_POOL = {
    'name': 'pool_name',
    'pg_num': 'pg_num',
    'group_id': 'group_id',
    'vgroup_id': 'vgroup_id',
    'safe_type': 'safe_type',
    'data_block_num': 'data_block_num',
    'code_block_num': 'code_block_num',
    'min_size': 'min_size',
    'max_bytes': 'max_bytes',
    'write_mode': 'write_mode',
}

SET_CACHE = {
    'cache_pool_id': 'cache_pool_id',
    'cache_pool_name': 'cache_pool_name',
    'cache_size': 'cache_size',
    'target_dirty_radio': 'target_dirty_radio',
    'target_full_radio': 'target_full_radio',
    'option': 'option',
    'caching_mode': 'caching_mode',
}

UNSET_CACHE = {
    'cache_pool_id': 'cache_pool_id',
    'cache_pool_name': 'cache_pool_name',
    'option': 'option',
}