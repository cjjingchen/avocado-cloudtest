QUERY_SUMMARY = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'item': {
                'type': 'array',
                'properties': {
                    'username': {'type': 'string'},
                    'ram_usage': {'type': 'integer'},
                    'cpu_usage': {'type': 'integer'},
                    'group': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'name': {'type': 'string'},
                        }
                    },
                    'servername': {'type': 'string'},
                    'passwd': {'type': 'string'},
                    'rack_id': {'type': 'integer'},
                    'created_at': {'type': 'string'},
                    'clusterid': {'type': 'string'},
                    'backup_node': {'type': 'string'},
                    'publicip': {'type': 'string'},
                    'clusterip': {'type': 'string'},
                    'state': {'type': 'integer'},
                    'status': {'type': 'integer'},
                    'mons': {'type': 'array',
                             'item': {
                                 'type': 'object',
                                 'properties': {
                                     'state': {'type': 'string'},
                                     'role': {'type': 'string'},
                                     'id': {'type': 'integer'},
                                     'name': {'type': 'string'},
                                 }
                             }
                             },
                    'parent_bucket': {'type': 'array',
                                      'items': {
                                          'type': 'object',
                                          'properties': {
                                              'id': {'type': 'integer'},
                                              'name': {'type': 'string'},
                                          }
                                      }
                                      },
                    'mds': {'type': 'array'},
                    'os': {'type': 'string'},
                    'id': {'type': 'integer'},
                }
            },
            'pagenum': {'type': 'integer'},
            'preindex': {'type': 'integer'},
            'sufindex': {'type': 'integer'},

        }
    }
}
CREATE_SUMMARY = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'properties': {
                'name': {'type': 'string'},
                'context': {'type': 'object',
                            'properties': {
                                'username': {'type': 'string'},
                                'password': {'type': 'string'},
                                'backup': {'type': 'string'},
                                "servername": {'type': 'string'},
                                'clusterid': {'type': 'integer'},
                                'publicip': {'type': 'string'},
                                'clusterip': {'type': 'string'},
                                'group_id': {'type': 'integer'},
                                'rack_id': {'type': 'integer'},
                            }
                            }
            },
            'start_at': {'type': 'string'},
            'log_msg': {'type': 'null'},
            'running_steps': {'type': 'null'},
            'create_at': {'type': 'string'},
            'update_at': {'type': 'string'},
            'execute_time': {'type': 'null'},
            'state': {'type': 'integer'},
            'current_step': {'type': 'null'},
            'end_at': {'type': 'null'},
            'type': {'type': 'string'},
            'id': {'type': 'string'},
        }

    }
}

SERVER_OPERATION_SUMMARY = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'result': {'type': 'string'},
        }
    }
}

SERVER_START_MAINTENANCE = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'created_at': {'type': 'string'},
            'current_step': {'type': ['string', 'null']},
            'end_at': {'type': ['string', 'null']},
            'execute_time': {'type': ['string', 'null']},
            'id': {'type': 'string'},
            'start_at': {'type': 'string'},
            'type': {'type': 'string'},
            'update_at': {'type': 'string'},
            'state': {'type': 'integer'},
        }
    }
}

SERVER_DISK_SUMMARY = {
    'status_code': [200],
    'response_body': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'capacity': {'type': 'string'},
                'type': {'type': 'integer'},
                'name': {'type': 'string'},
                'uuid': {'type': 'string'},
            }
        }
    }
}

SERVER_NETWORK_SUMMARY = {
    'status_code': [200],
    'response_body': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'hw_address': {'type': 'string'},
                'id': {'type': 'integer'},
                'ipv4_address': {'type': 'string'},
                'name': {'type': 'string'},
            }
        }
    }
}

ADD_CEPHED_SERVER_SUMMARY = {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'cluster_id': {'type': 'string'},
            'start_at': {'type': 'string'},
            'create_at': {'type': 'string'},
            'update_at': {'type': 'string'},
            'state': {'type': 'integer'},
            'type': {'type': 'string'},
            'context': {
                'username': {'type': 'string'},
                'passwd': {'type': 'string'},
                'clusterid': {'type': 'string'},
                'publicip': {'type': 'string'},
                'state': {'type': 'integer'},
                'clusterip': {'type': 'string'},
            }

        }
    }
}