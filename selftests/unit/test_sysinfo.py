import os
import sys
import tempfile
import shutil

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import sysinfo


class SysinfoTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="sysinfo_unittest")

    def testLoggablesEqual(self):
        cmd1 = sysinfo.Command("ls -l")
        cmd2 = sysinfo.Command("ls -l")
        self.assertEqual(cmd1, cmd2)
        file1 = sysinfo.Logfile("/proc/cpuinfo")
        file2 = sysinfo.Logfile("/proc/cpuinfo")
        self.assertEqual(file1, file2)

    def testLoggablesNotEqual(self):
        cmd1 = sysinfo.Command("ls -l")
        cmd2 = sysinfo.Command("ls -la")
        self.assertNotEqual(cmd1, cmd2)
        file1 = sysinfo.Logfile("/proc/cpuinfo")
        file2 = sysinfo.Logfile("/etc/fstab")
        self.assertNotEqual(file1, file2)

    def testLoggablesSet(self):
        container = set()
        cmd1 = sysinfo.Command("ls -l")
        cmd2 = sysinfo.Command("ls -l")
        cmd3 = sysinfo.Command("ps -ef")
        cmd4 = sysinfo.Command("uname -a")
        file1 = sysinfo.Command("/proc/cpuinfo")
        file2 = sysinfo.Command("/etc/fstab")
        file3 = sysinfo.Command("/etc/fstab")
        file4 = sysinfo.Command("/etc/fstab")
        # From the above 8 objects, only 5 are unique loggables.
        container.add(cmd1)
        container.add(cmd2)
        container.add(cmd3)
        container.add(cmd4)
        container.add(file1)
        container.add(file2)
        container.add(file3)
        container.add(file4)

        self.assertEqual(len(container), 5)

    def test_logger_job_hooks(self):
        jobdir = os.path.join(self.tmpdir, 'job')
        sysinfo_logger = sysinfo.SysInfo(basedir=jobdir)
        sysinfo_logger.start_job_hook()
        self.assertTrue(os.path.isdir(jobdir))
        self.assertGreaterEqual(len(os.listdir(jobdir)), 1,
                                "Job does not have 'pre' dir")
        job_predir = os.path.join(jobdir, 'pre')
        self.assertTrue(os.path.isdir(job_predir))
        sysinfo_logger.end_job_hook()
        job_postdir = os.path.join(jobdir, 'post')
        self.assertTrue(os.path.isdir(job_postdir))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
