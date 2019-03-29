import json
import urllib2
import logging

from cloudtest.tests.ceph_api.common import CephMgmtClient

LOG = logging.getLogger('avocado.test')


class ZabbixClient(CephMgmtClient):
    def __init__(self, params):
        self.params = params
        super(ZabbixClient, self).__init__(params)
        self.url = self.base_url.split(':9999')[0] + '/zabbix/api_jsonrpc.php'
        self.header = {"Content-Type": "application/json-rpc"}
        self.authID = self.user_login()

    def user_login(self):
        data = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "user.login",
                    "params": {
                        "user": "Admin",
                        "password": "zabbix"
                        },
                    "id": 0
                    })
        request = urllib2.Request(self.url,data)
        for key in self.header:
            request.add_header(key,self.header[key])
        try:
            result = urllib2.urlopen(request)
        except urllib2.URLError as e:
            LOG.error("Auth Failed, Please Check Your Name And Password: % s"
                      % e.code)
        else:
            response = json.loads(result.read())
            result.close()
            authID = response['result']
            LOG.info("Login to zabbix successfully, auth id: %s" % authID)
            return authID

    def get_data(self, data):
        request = urllib2.Request(self.url,data)
        for key in self.header:
            request.add_header(key,self.header[key])
        try:
            result = urllib2.urlopen(request)
        except urllib2.URLError as e:
            if hasattr(e, 'reason'):
                LOG.error('We failed to reach a server.'
                          'Reason: %s' % e.reason)
            elif hasattr(e, 'code'):
                LOG.error('The server could not fulfill the request.'
                          'Error code: %s' % e.code)
            return 0
        else:
            response = json.loads(result.read())
            result.close()
            return response

    def get_host_id_by_group_id(self, group_id):
        data = json.dumps(
            {
               "jsonrpc":"2.0",
               "method":"host.get",
               "params":{
                   "output":["hostid","name","status","host"],
                   "groupids":group_id,
               },
               "auth": self.authID, 
               "id":1,
            })
        res = self.get_data(data)
        if 'result' in res.keys():
            res = res['result']
            if (res !=0) or (len(res) != 0):
                for host in res:
                    return host['hostid']
        else:
            LOG.error("The group id does not exist, please check!")

    def get_host_group(self, host_group_name):
        data = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "hostgroup.get",
                "params": {
                    "output": "extend",
                },
                "auth": self.authID,
                "id": 1,
            })
        res = self.get_data(data)
        if 'result' in res.keys():
            res = res['result']
            if (res != 0) or (len(res) != 0):
                for host in res:
                    if host['name'] == host_group_name:
                        return host['groupid']
        else:
            LOG.error("Get HostGroup Error,please check !")

    def get_item_id(self, host_id, item_name):
        data = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "item.get",
                "params": {
                    "output": ["itemids", "key_"],
                    "hostids": host_id,
                },
                "auth": self.authID,
                "id": 1,
            })
        res = self.get_data(data)
        if 'result' in res.keys():
            res = res['result']
            if (res != 0) or (len(res) != 0):
                for item in res:
                    if item['key_'] == item_name:
                        return item['itemid']
        else:
            LOG.error("Get Item ID Error,please check !")

    def get_item_history(self, item_id, limit):
        data = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "history.get",
                "params": {
                    "output": "extend",
                    "history": 3,  # history object types to return: numeric unsigned
                    "itemids": item_id,
                    "limit": limit
                },
                "auth": self.authID,
                "id": 1,
            })
        res = self.get_data(data)
        if 'result' in res.keys():
            res = res['result']
            if (res != 0) or (len(res) != 0):
                return res
        else:
            LOG.error("Failed to get history for item %s ,please check !"
                      % item_id)
