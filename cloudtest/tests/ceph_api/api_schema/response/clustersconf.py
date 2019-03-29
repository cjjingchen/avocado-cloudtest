query = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'zabbix_password': {'type': 'string'},
            'zabbix_user': {'type': 'string'},
            'daylight_end': {'type': 'string'}, 
            'ntp_server_ip': {'type': 'string'}, 
            'daylight_begin': {'type': 'string'},
            'max_mdx_count':  {'type': 'integer'},
            'max_mon_count': {'type': 'integer'}, 
            'night_recover_bw': {'type': 'integer'}, 
            'day_recover_bw': {'type': 'integer'}, 
            'zabbix_server_ip': {'type': 'string'},
        }
    }
}

set = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'max_mdx_count':  {'type': 'integer'},
            'max_mon_count': {'type': 'integer'},
            'zabbix_password':  {'type': 'string'},
            'zabbix_user': {'type': 'string'},
            'daylight_begin': {'type': 'string'},
            'daylight_end': {'type': 'string'},
            'zabbix_kpi_status': {'type': 'string'},
            'ntp_server_ip': {'type': 'string'},
            'day_recover_bw': {'type': 'integer'},
            'night_recover_bw': {'type': 'integer'},
            'zabbix_server_ip': {'type': 'string'},
        }
    }
}
