"""
Rest client for monitorfun
"""
import json
#import copy

from cloudtest.tests.ceph_api.common import CephMgmtClient
from cloudtest.tests.ceph_api.lib.rest_client import ResponseBody


class MonitorfunClient(CephMgmtClient):
    """
    The REST client of monitorfun.
    """
    def __init__(self, params):
        self.params = params
        super(MonitorfunClient, self).__init__(params)
        self.cluster_id = self.params.get('cluster_id')
        self.granularity = self.params.get('granularity')
        self.time_from = self.params.get('time_from')
        self.time_till = self.params.get('time_till')
        self.url = '/%s/kpi?clusterid=%s' % (params.get('version', 'v1'),
                                              self.cluster_id)

    def query_occupancy(self, **args):
        """
        Query node occupancy rate

        """
        if len(args) > 0:
            url = self.url + ("&serverid=%s&target=%s"
            "&kpi=usage_percent&granularity=%s"
            "&time_from=%s&time_till=%s"
            % (args.get('serverid'), args.get('query_type'),
               self.granularity, self.time_from,
               self.time_till))
        else:
            url = self.url
        resp, body = self.get(url)
        if body:
            return json.loads(body)
        return ResponseBody(resp)


    def query_storage(self, **args):
        """
        Query storage total, used, available capacity

        """
        if len(args) > 0:
            url = self.url + ("&target=cluster"
            "&kpi=%s&granularity=%s"
            "&time_from=%s&time_till=%s"
            % (args.get('kpi'), self.granularity,
               self.time_from, self.time_till))
        else:
            url = self.url
        resp, body = self.get(url)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def query_cephdisk(self, **args):
        """
        Query ceph disk total, used, available capacity

        """
        if len(args) > 0:
            url = self.url + ("&serverid=%s&diskid=%s"
            "&target=disk&kpi=%s&granularity=%s"
            "&time_from=%s&time_till=%s"
            % (args.get('serverid'), args.get('diskid'),
               args.get('kpi'), self.granularity,
               self.time_from, self.time_till))
        else:
            url = self.url
        resp, body = self.get(url)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def query_phydiskparams(self, **args):
        """
        Query phycics disk parameters like read or write bw and read or
        write iops, io await

        """
        if len(args) > 0:
            url = self.url + ("&serverid=%s&phydiskid=%s"
            "&target=phydisk&kpi=%s&granularity=%s"
            "&time_from=%s&time_till=%s"
            % (args.get('serverid'), args.get('diskid'),
               args.get('kpi'), self.granularity,
               self.time_from, self.time_till))
        else:
            url = self.url
        resp, body = self.get(url)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def query_poolparams(self, **args):
        """
        Query pool paramters like read or write bw and read or write iops,
        io await

        """
        if len(args) > 0:
            url = self.url + ("&poolid=%s&target=pool&kpi=%s"
            "&granularity=%s&time_from=%s&time_till=%s"
            % (args.get('poolid'), args.get('kpi'), self.granularity,
               self.time_from, self.time_till))
        else:
            url = self.url
        resp, body = self.get(url)
        if body:
            return json.loads(body)
        return ResponseBody(resp)

    def query_rbdparams(self, **args):
        """
        Query rbd paramters like read or write bw and read or write iops,
        io await

        """
        if len(args) > 0:
            url = self.url + ("&rbdid=%s&target=rbd&kpi=%s"
            "&granularity=%s&time_from=%s&time_till=%s"
            % (args.get('rbdid'), args.get('kpi'), self.granularity,
               self.time_from, self.time_till))
        else:
            url = self.url
        resp, body = self.get(url)
        if body:
            return json.loads(body)
        return ResponseBody(resp)
