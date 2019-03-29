import logging

from avocado.core import test
from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest.tests.ceph_api.lib import test_utils
from cloudtest.tests.ceph_api.lib.groups_client import GroupsClient

LOG = logging.getLogger('avocado.test')


class TestGroups(test.Test):
    """
    Groups related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.body = {}
        self.env = env
        self.cluster_id = ""

    def setup(self):
        """
        Set up before executing test
        """
        if 'cluster' in self.env:
            self.cluster_id = self.env.get('cluster')
        elif self.params.get('cluster_id'):
            self.cluster_id = int(self.params.get('cluster_id'))
            self.env['cluster'] = self.cluster_id
        else:
            raise exceptions.TestSetupFail(
                'Please set cluster_id in config first')

        self.params['cluster_id'] = self.cluster_id
        self.client = GroupsClient(self.params)

        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

    def test_create_group(self):
        create_body = {'name':
                           'cloudtest_group_'
                           + utils_misc.generate_random_string(6),
                       'max_size':
                           self.params.get('rest_arg_max_size', 10),
                       'leaf_firstn':
                           self.params.get('rest_arg_leaf_firstn', 'host'),
                       'cluster_id': self.cluster_id}
        resp_body = self.client.create_group(**create_body)
        body = resp_body.body
        if 'cluster_id' not in body:
            raise exceptions.TestFail("Create group policy failed")
        LOG.info("Created group '%s' with id: %s"
                 % (body['name'], body['id']))
        self.env['group_id'] = body['id']

    def test_list_groups(self):
        if 'group_id' in self.env:
            group_id = self.env.get('group_id')
        elif self.params.get('group_id'):
            group_id = int(self.params.get('group_id'))
        else:
            raise exceptions.TestSetupFail(
                'Please set group_id in config first')

        groups = self.client.list_groups()
        for group in groups:
            if group_id == group['id']:
                return
        raise exceptions.TestFail(
            "Failed to find previously created group")

    def test_rename_group(self):
        if 'group_id' in self.env:
            group_id = self.env.get('group_id')
        elif self.params.get('group_id'):
            group_id = int(self.params.get('group_id'))
        else:
            raise exceptions.TestSetupFail(
                'Please set group_id in config first')

        rename_body = {'name': 'cloudtest_group_'
                               + utils_misc.generate_random_string(6)}
        resp_body = self.client.rename_group(group_id, **rename_body)
        body = resp_body.body
        groups = self.client.list_groups(extra_url=None)
        for group in groups:
            if group_id == group['id']:
                if rename_body['name'] == body['name']:
                    LOG.info('Rename group to %s successfully!'
                             % rename_body['name'])
                else:
                    raise exceptions.TestFail(
                        'Failed to rename group to %s!'
                        % rename_body['name'])
                break

    def test_delete_group(self):
        if 'group_id' in self.env:
            group_id = self.env.get('group_id')
        elif self.params.get('group_id'):
            group_id = int(self.params.get('group_id'))
        else:
            raise exceptions.TestSetupFail(
                'Please set group_id in config first')

        self.client.delete_group(group_id)
        groups = self.client.list_groups()
        for group in groups:
            if group_id in group.values():
                raise exceptions.TestFail(
                    "Failed to delete group: %s" % group_id)
        del self.env['group_id']

    def _find_bucket_id(self, items, bucket_id, result):
        for item in items:
            if len(item.get('items')) > 0:
                self._find_bucket_id(item.get('items'),
                                     bucket_id, result)
                if item.get('id') == bucket_id:
                    result.append(True)
                else:
                    result.append(False)
            elif item.get('id') == bucket_id:
                result.append(True)
            else:
                result.append(False)

        return result

    def _find_bucket_name(self, items, bucket_name, result):
        for item in items:
            if len(item.get('items')) > 0:
                self._find_bucket_name(item.get('items'),
                                     bucket_name, result)
                if item.get('name') == bucket_name:
                    result.append(True)
                else:
                    result.append(False)
            elif item.get('name') == bucket_name:
                result.append(True)
            else:
                result.append(False)

        return result

    def _verify_modify_bucket(self, modify_body,
                              parent_id, bucket_id):
        # Verify the bucket id can be found in specified group
        groups = self.client.list_groups(extra_url='?underlying=1')
        result = []
        for group in groups:
            if group['id'] == modify_body['target_group']:
                if parent_id or parent_id != -1:
                    self._find_bucket_id(group.get('items'),
                                         bucket_id,
                                         result)
                else:
                    for item in group['items']:
                        if item['id'] == bucket_id:
                            LOG.info("id = %d True" % bucket_id)
                            result.append(True)
                        else:
                            LOG.info("id = %d False" % bucket_id)
                            result.append(False)
                break
        if any(result):
            LOG.info("Modify the bucket to group %s successfully!"
                     % modify_body['target_group'])
        else:
            raise exceptions.TestFail(
                "Failed to modify the bucket to group %s!"
                % modify_body['target_group'])

    def test_create_bucket(self):
        group_id, parent_id = \
            test_utils.get_available_group_bucket(self.params)
        create_body = {'name':
                           'cloudtest_bucket_'
                           + utils_misc.generate_random_string(6),
                       'type':
                           self.params.get('rest_arg_type', 'rack')}
        if self.params.get('request_body') in 'full':
            create_body.update({'parent_id': int(parent_id)})
        resp_body = self.client.create_bucket(group_id, **create_body)
        body = resp_body.body
        if 'id' not in body:
            raise exceptions.TestFail("Create bucket failed")
        LOG.info("Created bucket '%s' with id: %s"
                 % (body['name'], body['id']))
        self.env['bucket_id'] = body['id']
        self.env['group_id'] = group_id

    def test_rename_bucket(self):
        if 'group_id' in self.env:
            group_id = self.env.get('group_id')
        elif self.params.get('group_id'):
            group_id = int(self.params.get('group_id'))
        else:
            raise exceptions.TestSetupFail(
                'Please set group_id in config first')

        if 'bucket_id' in self.env:
            bucket_id = self.env.get('bucket_id')
        elif self.params.get('bucket_id'):
            bucket_id = int(self.params.get('bucket_id'))
        else:
            raise exceptions.TestSetupFail(
                'Please set bucket_id in config first')

        rename_body = {'name': 'cloudtest_bucket_'
                               + utils_misc.generate_random_string(6)}
        resp_body = self.client.rename_bucket(group_id,
                                              bucket_id, **rename_body)
        body = resp_body.body
        if body['name'] != rename_body['name']:
            raise exceptions.TestFail("Failed to rename the bucket to %s!"
                                      % rename_body['name'])
        # Verify the bucket name can be found in list
        groups = self.client.list_groups(extra_url='?underlying=1')
        result = []
        for group in groups:
            if group_id == group['id']:
                self._find_bucket_name(group.get('items'),
                                             rename_body['name'], result)
                break
        if any(result):
            LOG.info("Rename the bucket to %s successfully!"
                     % rename_body['name'])
        else:
            raise exceptions.TestFail(
                "Failed to rename the bucket to %s!"
                % rename_body['name'])

    def test_modify_bucket(self):
        if 'group_id' in self.env:
            group_id = self.env.get('group_id')
        elif self.params.get('group_id'):
            group_id = int(self.params.get('group_id'))
        else:
            raise exceptions.TestSetupFail(
                'Please set group_id in config first')

        if 'bucket_id' in self.env:
            bucket_id = self.env.get('bucket_id')
        elif self.params.get('bucket_id'):
            bucket_id = int(self.params.get('bucket_id'))
        else:
            raise exceptions.TestSetupFail(
                'Please set bucket_id in config first')

        # test not specified optional parameter parent_id
        target_group_id = self.params.get('rest_arg_target_group')
        if not target_group_id:
            target_group_id, parent_id = \
                test_utils.get_available_group_bucket(self.params,
                                                      group_id)
        modify_body = {'target_group': int(target_group_id)}
        self.client.modify_bucket(group_id, bucket_id, **modify_body)
        self._verify_modify_bucket(modify_body, None, bucket_id)
        group_id = target_group_id
        # test specified optional parameter parent_id
        parent_id = self.params.get('rest_arg_parent_id')
        if not parent_id:
            target_group_id, parent_id = \
                test_utils.get_available_group_bucket(self.params)
        modify_body.update({'target_group': int(target_group_id),
                            'parent_id': int(parent_id)})
        self.client.modify_bucket(group_id, bucket_id, **modify_body)
        self._verify_modify_bucket(modify_body, parent_id, bucket_id)

        self.env['group_id'] = modify_body['target_group']
        self.env['bucket_id'] = bucket_id

    def test_delete_bucket(self):
        if 'group_id' in self.env:
            group_id = self.env.get('group_id')
        elif self.params.get('group_id'):
            group_id = int(self.params.get('group_id'))
        else:
            raise exceptions.TestSetupFail(
                'Please set group_id in config first')

        if 'bucket_id' in self.env:
            bucket_id = self.env.get('bucket_id')
        elif self.params.get('bucket_id'):
            bucket_id = int(self.params.get('bucket_id'))
        else:
            raise exceptions.TestSetupFail(
                'Please set bucket_id in config first')

        self.client.delete_bucket(group_id, bucket_id)
        # Verify the deleted bucket_id cannot be found in list
        groups = self.client.list_groups(extra_url='?underlying=1')
        result = []
        for group in groups:
            if group_id == group['id']:
                self._find_bucket_id(group.get('items'),
                                           bucket_id, result)
                break
        if any(result):
            raise exceptions.TestFail("Failed to delete bucket %d!"
                                      % bucket_id)
        else:
            LOG.info("Delete the bucket %d successfully!" % bucket_id)

        del self.env['bucket_id']

    def test_query_logic_group(self):
        """
        query logic group in default group
        :return: logic group id
        """
        group_id = self.params.get('rest_arg_group_id', 1)
        test_utils.wait_for_available_vgroup(self.client, group_id, timeout=600)
        vgroups = self.client.query_logic_group(group_id)
        if len(vgroups) == 0:
            raise exceptions.TestFail("Failed to test_query_logic_group")
        vgroup_id = vgroups[0]['virtual_group_id']
        self.env['vgroup_id'] = vgroup_id

    def teardown(self):
        pass
