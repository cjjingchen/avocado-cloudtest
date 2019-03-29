import os
import re
import logging

from avocado.core import test
from avocado.core import exceptions
from cloudtest import utils_misc
from cloudtest import remote
from cloudtest import data_dir
from cloudtest.tests.ceph_api.lib.pools_client import PoolsClient
from cloudtest.tests.ceph_api.lib.rbd_client import RbdClient
from cloudtest.tests.ceph_api.lib.qos_client import QosClient
from cloudtest.tests.ceph_api.lib import utils
from cloudtest.tests.ceph_api.lib import test_utils

LOG = logging.getLogger('avocado.test')
RBD_CAPACITY = 1024*1024


class TestRbdQos(test.Test):
    def __init__(self, params, env):
        self.params = params
        self.env = env
        self.pool_client = PoolsClient(params)
        self.dstpath = '/root'
        self.workload_path = data_dir.COMMON_TEST_DIR
        self.fio_version = self.params.get('fio_version')
        self.fio_working_path = \
            self.fio_version[0:len(self.fio_version) - len('.tar.gz')]

    def setup(self):
        ceph_server_ip = self.params.get('ceph_management_url')
        self.mid_host_ip = ceph_server_ip.split(':')[1].strip('/')
        self.cluster_id = self.params.get('cluster_id')
        self.mid_host_user = self.params.get('ceph_server_ssh_username')
        self.mid_host_password = self.params.get('ceph_server_ssh_password')
        self.end_host_user = self.params.get('ceph_node_ssh_username')
        self.end_host_password = self.params.get('ceph_node_ssh_password')

        self.end_host_ip = test_utils.get_available_host_ip(self.params)
    def test(self):
        LOG.info('Copy file %s from local to %s' % (self.fio_version,
                                                    self.mid_host_ip))
        remote.scp_to_remote(host=self.mid_host_ip,
                             port=22,
                             username=self.mid_host_user,
                             password=self.mid_host_password,
                             local_path=os.path.join(self.workload_path,
                                                     self.fio_version),
                             remote_path=self.dstpath)
        LOG.info('Copy file %s from %s to %s' % (self.fio_version,
                                                 self.mid_host_ip,
                                                 self.end_host_ip))
        remote.scp_between_remotes(src=self.mid_host_ip,
                                   dst=self.end_host_ip,
                                   port=22,
                                   s_passwd=self.mid_host_password,
                                   d_passwd=self.end_host_password,
                                   s_name=self.mid_host_user,
                                   d_name=self.end_host_user,
                                   s_path=os.path.join(self.dstpath,
                                                       self.fio_version),
                                   d_path=self.dstpath)

        self.pool_response = test_utils.create_pool(self.params, flag=True)
        self.pool_name = self.pool_response.get('name')
        self.pool_id = self.pool_response.get('id')

        self.rbd_response = test_utils.create_rbd_with_capacity(self.pool_id,
                                                                self.params,
                                                                RBD_CAPACITY)
        self.rbd_id = self.rbd_response.get('id')
        self.rbd_name = self.rbd_response.get('name')

        self.rbd_client = RbdClient(self.params)

        self.params['rbds_id'] = self.rbd_id
        self.params['pool_id'] = self.pool_id
        self.qos_client = QosClient(self.params)

        self.__test_operation(property_type='iops', rw='randwrite', flag=True)
        self.__test_operation(property_type='iops', rw='randread')
        self.__test_operation(property_type='iops', rw='randrw',
                              rw_type='rwmixread', rw_value=70)
        self.__test_operation(property_type='bw', rw='randwrite')
        self.__test_operation(property_type='bw', rw='randread')
        self.__test_operation(property_type='bw', rw='randrw',
                              rw_type='rwmixread', rw_value=70)

    def __test_operation(self, property_type, rw, rw_type=None, rw_value=None, flag=False):
        """
        Run test according to different params.
        :param property_type: iops/bw
        :param rw: randread/read/randwrite/write/randrw/rw
        :param rw_type: rwmixread when rw is randrw/rw
        :param rw_value: 70 mains 7:3 r/w
        :param flag: mark is the first time call this method.
        """
        self.__disable_qos()
        bs = '8k'
        iodepth = 128
        if 'bw' in property_type:
            bs = '1024k'
            iodepth = 512
        LOG.info('******%s rbd before enable qos!******' % rw)
        stdout_msg = self.__write_rbd(rw=rw, rw_type=rw_type,
                                      rw_value=rw_value, bs=bs,
                                      iodepth=iodepth, runtime=120,
                                      flag=flag)
        result_before = self.__get_iops_or_bw(stdout_msg, property_type)
        body = self.__get_qos_body(operation=rw,
                                   property_type=property_type,
                                   value=result_before/2)
        self.__enable_qos(body)
        LOG.info('******%s rbd after enable qos!******' % rw)
        stdout_msg = self.__write_rbd(rw=rw, rw_type=rw_type,
                                      rw_value=rw_value, bs=bs,
                                      iodepth=iodepth, runtime=120)
        result_after = self.__get_iops_or_bw(stdout_msg, property_type)
        self.__check_result(result_before/2, result_after)

    @staticmethod
    def __check_result(before, after):
        """
        :param before: value before update qos
        :param after: 
        :return: 
        """
        temp_value = abs(before - after)
        result = temp_value*100/after
        if result > 10:
            LOG.error('******IOPS Value %s after enabled qos is greater than 10 '
                'percentage, compare with IOPS value %s before enabled qos!******'
                      % (after, before))
        else:
            LOG.info('******Check result successfully******')

    def __get_qos_body(self, operation, property_type, value):
        """
        Return body for update qos.
        :param operation: randread/read/randwrite/write/randrw/rw
        :param property_type: iops/bw
        :param value: value return by analyze msg return by fio
        :return: body
        """
        if 'bw' in property_type:
            if 'KB/s' in self.bw_unit:
                TIMES = 1024
            elif 'MB/s' in self.bw_unit:
                TIMES = 1024*1024
            else:
                raise exceptions.TestFail('Network is too slow '
                                          'because qos cannot set '
                                          'bw value under 100M!')
            if 'read' in operation:
                return {"rbw": value*TIMES}
            elif 'write' in operation:
                return {"wbw": value*TIMES}
            else:
                return {"bw": value*TIMES}
        else:
            if 'read' in operation:
                return {"riops": value}
            elif 'write' in operation:
                return {"wiops": value}
            else:
                return {"iops": value}

    def __disable_qos(self):
        LOG.info('******Disable qos******')
        resp = self.qos_client.disable()
        body = resp.body
        if not body.get('success'):
            raise exceptions.TestFail("Disable qos failed: %s" % body)

    def __enable_qos(self, body):
        LOG.info('******Enable qos******')
        resp = self.qos_client.enable(**body)
        if not utils.verify_response(body, resp.body.get('results')):
            raise exceptions.TestFail("Enable qos failed: %s" % body)

    def __get_iops_or_bw(self, msg, value_type='iops'):
        """
        Analyze msg return by fio.
        :param msg: msg return by fio
        :param value_type: iops/bw
        :return: 
        """
        iops_read = 0
        iops_write = 0
        bw_read = 0
        bw_write = 0
        pat_read = 'read : (.*)'
        pat_write = 'write: (.*)'
        read_msg_list = re.findall(pat_read, msg)
        write_msg_list = re.findall(pat_write, msg)
        if not len(read_msg_list) and not len(write_msg_list):
            raise exceptions.TestError('Msg data or pattern error, '
                                       'please check!')
        if 'bw' in value_type:
            if len(read_msg_list):
                temp = read_msg_list[0].split(',')[1].split('=')[1]
                bw_read = temp[:-4]
                self.bw_unit = temp[-4:]
            if len(write_msg_list):
                temp = write_msg_list[0].split(',')[1].split('=')[1]
                bw_write = temp[:-4]
                self.bw_unit = temp[-4:]
            bw_total = int(float(bw_read)) + int(float(bw_write))
            if bw_write and bw_read:
                return bw_total
            elif bw_read:
                return int(float(bw_read))
            else:
                return int(float(bw_write))
        else:
            if len(read_msg_list):
                iops_read = read_msg_list[0].split(',')[2].split('=')[1]
            if len(write_msg_list):
                iops_write = write_msg_list[0].split(',')[2].split('=')[1]
            iops_total = int(iops_read) + int(iops_write)
            if iops_read and iops_write:
                return int(iops_total)
            elif iops_read:
                return int(iops_read)
            else:
                return int(iops_write)

    def __get_pool_name_and_id(self):
        pools = self.pool_client.query()
        if not len(pools):
            raise exceptions.TestSetupFail('No pool found!')
        self.pool_id = pools[0]['id']
        self.pool_name = pools[0]['name']

    def __write_rbd(self, rw, rw_type, rw_value, bs, iodepth, runtime,
                    flag=False):
        """
        Write rbd via fio
        :param rw: randread/read/randwrite/write/randrw/rw
        :param rw_type: rwmixread/None
        :param rw_value: rw_type value
        :param bs: 
        :param iodepth: 
        :param runtime: 
        :param flag: True/False mains if need tar file
        :return: 
        """
        cmd1 = 'cd %s;' % self.fio_working_path
        cmd2 = './fio -ioengine=rbd -clientname=admin -pool=%s ' % \
               self.pool_name
        if rw_type and rw_value:
            cmd3 = '-rw=%s -%s=%s -bs=%s -iodepth=%s -numjobs=1 -direct=1 ' % \
                   (rw, rw_type, rw_value, bs, iodepth)
        else:
            cmd3 = '-rw=%s -bs=%s -iodepth=%s -numjobs=1 -direct=1 ' % \
                   (rw, bs, iodepth)

        cmd4 = '-runtime=%s -group_reporting -rbdname=%s -name=mytest' % \
               (runtime, self.rbd_name)
        cmd = cmd1 + cmd2 + cmd3 + cmd4
        if flag:
            cmd = 'tar -xzvf %s;' % self.fio_version + cmd
        out_msg = remote.run_cmd_between_remotes(
             mid_host_ip=self.mid_host_ip,
             mid_host_user=self.mid_host_user,
             mid_host_password=self.mid_host_password,
             end_host_ip=self.end_host_ip,
             end_host_user=self.end_host_user,
             end_host_password=self.end_host_password,
             cmd=cmd,
             timeout=1000)
        return out_msg

    def teardown(self):
        # delete files
        cmd_mid = 'rm -rf %s' % (os.path.join(self.dstpath, self.fio_version))
        cmd1 = 'pkill fio || true; '
        cmd2 = 'rm -rf %s %s' % (os.path.join(self.dstpath, self.fio_version),
                                 os.path.join(self.dstpath, self.fio_working_path))
        cmd = cmd1 + cmd2
        remote.run_cmd_between_remotes(mid_host_ip=self.mid_host_ip,
                                       mid_host_user=self.mid_host_user,
                                       mid_host_password
                                       =self.mid_host_password,
                                       end_host_ip=self.end_host_ip,
                                       end_host_user=self.end_host_user,
                                       end_host_password
                                       =self.end_host_password,
                                       cmd=cmd,
                                       cmd_mid=cmd_mid)