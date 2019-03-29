import time
import logging
import os_client_config
from aodhclient import client as aodhclient
from keystoneauth1 import loading
from keystoneauth1 import session


from common import Common


LOG = logging.getLogger('avocado.test')


class Ceilometer(Common):
    def __init__(self, params):
        super(Ceilometer, self).__init__(params)
        self.ceilometerclient = os_client_config.make_client('metering',
                                                             **self.ceilometer_credential)
        self.alarm_utils = self.ceilometerclient.alarms
        self.query_alarms_utils = self.ceilometerclient.query_alarms
        self.query_alarm_history_utils = self.ceilometerclient.query_alarm_history

    def get_alarm_list(self):
        return self.alarm_utils.list()

    def get_alarms_by_instance_name(self, instance_name=None, step=3, timeout=360):
        """
        only alarms belongs to current user
        the important parameters od alarm is : name/ timestamp / state / alarm_id
        :param instance_name: vm_host_name
        :return: alarm or exception
        """
        end_time = time.time() + timeout
        current_time = time.time()
        while time.time() < end_time:
            alarm_list = self.alarm_utils.list()
            target_alarms = []
            for alarm in alarm_list:
                alarm_name = alarm.name.split(':')[0].strip()
                if alarm_name in instance_name:
                    target_alarms.append(alarm)
            alarms_length = len(target_alarms)
            LOG.info('Target alarm list length is %s' % alarms_length)
            # target_alarms.sort()
            if alarms_length > 0:
                for alarm in target_alarms:
                    LOG.info('Alarm id : %s, name : %s, state : %s, timestamp : %s ' %
                             (alarm.alarm_id, alarm.name, alarm.state,
                              alarm.timestamp))
                if alarm.timestamp > current_time:
                    return target_alarms[0]
                else:
                    time.sleep(step)
            else:
                time.sleep(step)
        else:
            LOG.error('Can not get alarms by instance name.')
            return False

    def get_failure_detection_recovery_time(self, alarm_id=None, step=3, timeout=360):
        end_time = time.time() + timeout

        while time.time() < end_time:
            alarm_list = self.alarm_utils.get_history(alarm_id)
            detection_time = None
            recovery_time = None
            for alarm in alarm_list:
                alarm_state = alarm.detail
                if type(alarm_state) == type(u'unicode'):
                    # alarm_state = alarm_state.encode('utf-8')
                    alarm_state = eval(alarm_state)
                if type(alarm_state) == type({}):
                    alarm_state = alarm_state['state']
                if alarm_state in 'ok':
                    recovery_time = alarm.timestamp
                if alarm_state in 'alarm':
                    detection_time = alarm.timestamp
            LOG.info('Failure detection time is %s, recovery time is %s ' % (detection_time, recovery_time))
            if detection_time and recovery_time:
                return detection_time, recovery_time
            else:
                time.sleep(step)
        else:
            LOG.error('Can not get failure detection time or recovery time.')
            return False


class AodhClient(Common):
    def __init__(self, params):
        super(AodhClient, self).__init__(params)
        self.params = params
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(**self.aodh_credential)
        sess = session.Session(auth)
        version = self.params.get('version', 2)
        self.aodhclient = aodhclient.Client(version, sess)
        self.alarm_utils = self.aodhclient.alarm

    def get_alarm_list(self, alarm_type='threshold'):
        alarm_list = self.alarm_utils.list(filters={'type': alarm_type})
        return alarm_list