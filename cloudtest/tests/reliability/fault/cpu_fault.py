import random
from avocado.core import exceptions
from  cloudtest.remote import RemoteRunner


class CpuFault(object):
    name = 'cpu_fault'

    def __init__(self, session, params, env):
        self.session = session
        self.params = params
        self.env = env

    def setup(self):
        self.cpu_offline_number = self.params.get("cpu_fault_offline")

    def test(self):
        sout = 0
        n = self.cpu_offline_number
        run_result = self.session.run('cat /proc/cpuinfo | grep cores | wc -l')
        sout = int(run_result.stdout)
        print "The cpu core number is : %s" % sout
        if n == "all":
            i = 1
            while i < sout:
                cmd = 'echo 0 > /sys/devices/system/cpu/cpu%s/online |' % i
                self.session.run(cmd)
                print "the cpu%s fault" % i
                i += 1
            current_out = self.session.run('cat /proc/cpuinfo | grep cores | wc -l')
            tmp = int(current_out.stdout)
            print "The current cpu online core number is : %s " % tmp
        elif int(n) >= sout or int(n) <= 0:
            raise exceptions.TestFail("cpu_fault_offline parameter out of range ")
        else:
            l = []
            k = 0
            while k < int(n):
                x = random.randint(1, sout - 1)
                if x in l:
                    continue
                else:
                    l.append(x)
                    k += 1
            for j in l:
                cmd = 'echo 0 > /sys/devices/system/cpu/cpu%s/online |' % j
                resultout = self.session.run(cmd)
            current_out = self.session.run('cat /proc/cpuinfo | grep cores | wc -l')
            tmp = int(current_out.stdout)
            print "The current cpu online core number is : %s " % tmp

    def teardown(self):
        sout = 0
        i = 1
        while True:
            cmd = 'echo 1 > /sys/devices/system/cpu/cpu%s/online |' % i
            self.session.run(cmd)
            i += 1
            current_out = self.session.run('cat /proc/cpuinfo | grep cores | wc -l')
            sout = int(current_out.stdout)
            if i > sout:
                break
        print "start teardown:The current cpu online core number is : %s " % sout


if __name__ == '__main__':
    session = RemoteRunner(client='ssh', host="10.100.4.190", username="root", port="22",
                           password="123456")
    params = {"cpu_fault_offline": "all"}
    cf = CpuFault(session, params)
    cf.setup()
    cf.test()
    cf.teardown()
