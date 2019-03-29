import logging
import time
import string

from avocado.core import test
from avocado.core import exceptions
#from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib.monitorfun_client import MonitorfunClient
from cloudtest.tests.ceph_api.lib import test_utils
#from cloudtest import utils_misc


LOG = logging.getLogger('avocado.test')


class TestMonitorfun(test.Test):
    """
    Monitorfun related tests.
    """
    def __init__(self, params, env):
        self.params = params
        self.client = ""
        self.body = {}
        self.env = env

    def get_time(self):
        year = time.strftime("%Y" , time.localtime(time.time()))
        month = time.strftime("%m" , time.localtime(time.time()))
        day = time.strftime("%d" , time.localtime(time.time()))
        hour = string.atoi(time.strftime("%H" , time.localtime(time.time())))
        return {"year":year,"month":month,"day":day,"hour":hour}

    def setup(self):
        """
        Set up before executing test
        """
        if 'cluster' in self.env:
            self.cluster_id = self.env['cluster']
            self.params['cluster_id'] = self.cluster_id
        elif self.params.get('cluster_id'):
            self.cluster_id = self.params.get('cluster_id')
        if 'granularity' in self.env:
            self.granularity = self.env['granularity']
            self.params['granularity'] = self.granularity
        elif self.params.get('granularity'):
            self.granularity = self.params.get('granularity')
        if 'time_from' in self.env:
            self.time_from = self.env['time_from']
            self.params['time_from'] = self.time_from
        elif self.params.get('time_from'):
            self.time_from = self.params.get('time_from')
        else:
            _from = self.get_time()
            _from["hour"] = _from["hour"] - 1
            self.time_from = ("%s-%s-%s+%d:00:00" % 
                              (_from["year"], _from["month"], 
                               _from["day"], _from["hour"]))
            self.params['time_from'] = self.time_from
        if 'time_till' in self.env:
            self.time_till = self.env['time_till']
            self.params['time_till'] = self.time_till
        elif self.params.get('time_till'):
            self.time_till = self.params.get('time_till')
        else:
            _till = self.get_time()
            self.time_till = ("%s-%s-%s+%d:00:00" % 
                              (_till["year"], _till["month"], 
                               _till["day"], _till["hour"]))
            self.params['time_till'] = self.time_till

        for k, v in self.params.items():
            if 'rest_arg_' in k:
                new_key = k.split('rest_arg_')[1]
                self.body[new_key] = v

        self.client = MonitorfunClient(self.params)

    def test_query_occupancy(self):
        # Test query cpu or mem occupancy rate
        query_type = self.params.get('query_type')
        self.body['query_type'] = query_type
        LOG.info("Try to query %s occupancy rate" % (query_type))
        resp = self.client.query_occupancy(**self.body)
        if not len(resp) > 0:
            raise exceptions.TestFail("Query occupancy rate failed")
        else:
            LOG.info("Got %s occupancy rate: %s" % (query_type,resp))

    def test_query_storage(self):
        # Test query storage system total, used, available capacity
        kpi = self.params.get('kpi')
        self.body['kpi'] = kpi
        LOG.info("Try to query storage system %s" % (kpi))
        resp = self.client.query_storage(**self.body)
        if not len(resp) > 0:
            raise exceptions.TestFail("Query storage system failed")
        else:
            LOG.info("Got %s storage system: %s" % (kpi,resp))

    def test_query_cephdisk(self):
        # Test query ceph disk total, used, available capacity
        kpi = self.params.get('kpi')
        self.body['kpi'] = kpi
        LOG.info("Try to query ceph disk %s" % (kpi))
        resp = self.client.query_cephdisk(**self.body)
        if not len(resp) > 0:
            raise exceptions.TestFail("Query ceph disk failed")
        else:
            LOG.info("Got %s ceph disk: %s" % (kpi,resp))

    def test_query_phdiskparams(self):
        # Test query physics disk parameters like read or write bw
        # and read or write iops, io await
        kpi = self.params.get('kpi')
        self.body['kpi'] = kpi
        LOG.info("Try to query physics disk %s" % (kpi))
        resp = self.client.query_phydiskparams(**self.body)
        if not len(resp) > 0:
            raise exceptions.TestFail("Query physics disk failed")
        else:
            LOG.info("Got physics disk %s: %s" % (kpi,resp))

    def test_query_poolparams(self):
        # Test query pool parameters like read or write bw and read or
        # write iops, io await, recovering rate, recovered bytes
        self.body['poolid'] = test_utils.get_pool_id(self.env, self.params)
        kpi = self.params.get('kpi')
        self.body['kpi'] = kpi
        LOG.info("Try to query pool %s" % (kpi))
        resp = self.client.query_poolparams(**self.body)
        if not len(resp) > 0:
            raise exceptions.TestFail("Query pool failed")
        else:
            LOG.info("Got pool %s: %s" % (kpi,resp))

    def test_query_rbdparams(self):
        # Test query rbd parameters like read or write bw and read or
        # write iops, io await
        pool_id = test_utils.get_pool_id(self.env, self.params)
        self.body['rbdid'] = test_utils.get_available_rbd(pool_id, self.params)
        kpi = self.params.get('kpi')
        self.body['kpi'] = kpi
        LOG.info("Try to query rbd %s" % (kpi))
        resp = self.client.query_rbdparams(**self.body)
        if not len(resp) > 0:
            raise exceptions.TestFail("Query rbd failed")
        else:
            LOG.info("Got rbd %s: %s" % (kpi,resp))

    def teardown(self):
        """
        Some clean up work will be done here.
        """
        pass
