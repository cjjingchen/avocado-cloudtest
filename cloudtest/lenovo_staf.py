import logging
import os
import socket

from PySTAF import STAFHandle
from PySTAF import STAFException


class LenovoSTAF():
    """
    provide method with STAF function
    """

    def __init__(self, host_ip):
        self.staf_logger = logging.getLogger("avocado.test")
        self.handle = self.get_staf_handle(host_ip)
        self.host_ip = host_ip

    def get_staf_handle(self, host_ip):
        """
        init a STAF handle

        :return:
        """
        try:
            handle = STAFHandle(host_ip)
        except STAFException, staf_exception:
            self.staf_logger.debug("Error registering with STAF, RC: %d" % staf_exception.rc)
            raise
        return handle

    def close_staf_handle(self):
        """
        close STAF handle

        :return:
        """
        rc = self.handle.unregister()
        self.staf_logger.debug("close handle, RC: %d" % rc)
        return rc

    def confirm_staf_connection(self):
        """
        confirm STAF connection with PING command

        :return: True if ping success, otherwise False
        """
        result = self.handle.submit(self.host_ip, "ping", "ping")
        self.staf_logger.debug("confirm host connection with ping command, RC: %d" % result.rc)
        if result.rc == 0:
            return True
        else:
            return False

    def copy_file_from(self, source_host_ip, source_loc, dest_loc, is_source_loc_dir=False, is_recurse=True,
                       is_dest_loc_dir=True, err_on_exists=False):
        """
        copy file from a remote host to local with FS command

        :param source_host_ip: source remote host IP address
        :param source_loc: file location in remote host
        :param dest_loc: destination location in local
        :param is_source_loc_dir: boolean, whether source location is a directory
        :param is_recurse: boolean, when source location is a directory, whether to get all files recursively
        :param is_dest_loc_dir: boolean, whether destination location is a directory
        :param err_on_exists:  boolean, whether show error if destination file/directory exists
        :return:
        """
        local_ip = socket.gethostbyname(socket.gethostname())
        if is_source_loc_dir:
            fs_command = "COPY DIRECTORY %s TODIRECTORY %s TOMACHINE %s" % (source_loc, dest_loc, local_ip)
            if is_recurse:
                fs_command += " RECURSE KEEPEMPTYDIRECTORIES"
        else:
            if is_dest_loc_dir:
                if not os.path.exists(dest_loc):
                    os.makedirs(dest_loc)
                fs_command = "COPY FILE %s TODIRECTORY %s TOMACHINE %s" % (source_loc, dest_loc, local_ip)
            else:
                dest_loc_dir = os.path.dirname(dest_loc)
                if not os.path.exists(dest_loc_dir):
                    os.makedirs(dest_loc_dir)
                fs_command = "COPY FILE %s TOFILE %s TOMACHINE %s" % (source_loc, dest_loc, local_ip)
            if err_on_exists:
                fs_command += " FAILIFEXISTS"
        self.staf_logger.debug("copy command: %s" % fs_command)
        result = self.handle.submit(source_host_ip, "FS", fs_command)
        self.staf_logger.debug("copy command RC: %d" % result.rc)
        self.staf_logger.debug("copy command Result: %s" % result.result)
        if result.rc != 0:
            raise Exception(
                "copy file/directory from host %s failed, source path is %s " % (source_host_ip, source_loc))

    def confirm_entry_exists(self, entry_name):
        """
        confirm file or directory exists or not with FS command

        :param entry_name: file or directory path
        :return: True if exists, otherwise False
        """
        fs_command = "QUERY ENTRY %s" % entry_name
        result = self.handle.submit(self.host_ip, "FS", fs_command)
        self.staf_logger.debug("query entry RC: %d" % result.rc)
        self.staf_logger.debug("query entry result: %s" % result.result)
        if result.rc == 0:
            return True
        else:
            return False

    def create_directory(self, dir_path, is_recurse=True, err_on_exists=False):
        """
        create directory in host with FS command

        :param dir_path: path of the directory
        :param is_recurse: boolean, whether to create all the path recursively
        :param err_on_exists: boolean, whether show error if destination directory exists
        :return: True if create successfully, otherwise False
        """
        fs_command = "CREATE DIRECTORY %s" % dir_path
        if is_recurse:
            fs_command += " FULLPATH"
        if err_on_exists:
            fs_command += " FAILIFEXISTS"
        result = self.handle.submit(self.host_ip, "FS", fs_command)
        self.staf_logger.debug("create directory RC: %d" % result.rc)
        self.staf_logger.debug("create directory Result: %s" % result.result)
        if result.rc == 0:
            return True
        else:
            return False

    def copy_file_to(self, source_loc, dest_host_ip, dest_loc, is_source_loc_dir=False, is_recurse=True,
                     is_dest_loc_dir=True, err_on_exists=False):
        """
        copy file to remote host with FS command
        :param source_loc: file/directory location in local
        :param dest_host_ip: remote host IP address
        :param dest_loc: file/directory path in remote host
        :param is_source_loc_dir: boolean, whether source location is a directory
        :param is_recurse: boolean, when source location is a directory, whether to get all files recursively
        :param is_dest_loc_dir: boolean, whether destination location is a directory
        :param err_on_exists: boolean, whether show error if destination file/directory exists
        :return:
        """
        local_ip = socket.gethostbyname(socket.gethostname())
        if is_source_loc_dir:
            fs_command = "COPY DIRECTORY %s TODIRECTORY %s TOMACHINE %s" % (source_loc, dest_loc, dest_host_ip)
            if is_recurse:
                fs_command += " RECURSE KEEPEMPTYDIRECTORIES"
        else:
            if is_dest_loc_dir:
                self.create_directory(dest_host_ip, dest_loc)
                fs_command = "COPY FILE %s TODIRECTORY %s TOMACHINE %s" % (source_loc, dest_loc, dest_host_ip)
            else:
                dest_loc_dir = os.path.dirname(dest_loc)
                if not self.confirm_entry_exists(dest_host_ip, dest_loc_dir):
                    self.create_directory(dest_host_ip, dest_loc)
                fs_command = "COPY FILE %s TOFILE %s TOMACHINE %s" % (source_loc, dest_loc, dest_host_ip)
            if err_on_exists:
                fs_command += " FAILIFEXISTS"
        self.staf_logger.debug("copy command: %s" % fs_command)
        result = self.handle.submit(local_ip, "FS", fs_command)
        self.staf_logger.debug("copy command RC: %d" % result.rc)
        self.staf_logger.debug("copy command Result: %s" % result.result)
        if result.rc != 0:
            raise Exception("copy file/directory to host %s failed, destination path is %s " % (dest_host_ip, dest_loc))

    def exe_staf_command(self, service, command):
        """
        execute STAF command

        :param service: service name, such as "FS"
        :param command: command in service
        :return: True if execute successfully, otherwise False
        """
        self.staf_logger.debug("execute command: %s %s" % (service, command))
        result = self.handle.submit(self.host_ip, service, command)
        self.staf_logger.debug("execute command RC: %d" % result.rc)
        self.staf_logger.debug("execute command Result: %s" % result.result)
        if result.rc == 0:
            return True
        else:
            return False

    def exe_staf_shell_command(self, shell_command, is_gen_log_file=False, log_file_path=None, is_wait_result=True,
                               is_set_timeout=False, timeout=60):
        """
        execute shell command with STAF,using PROCESS START SHELL COMMAND ...

        :param shell_command: shell command, such as "ls -a"
        :param is_gen_log_file: boolean, whether to redirect standout to log file
        :param log_file_path: path of the log file, it will be used when is_gen_log_file is defined
        :param is_wait_result: boolean, whether to wait for execution result
        :param is_set_timeout: boolean, whether to set timeout to this execution
        :param timeout: means that stop the shell command after given "timeout" seconds
        :return: shell command execution result, if don't wait for result, and process not finish,
                 it will return handle id
        """
        process_command = "START SHELL COMMAND \"%s\"" % shell_command
        process_command += " WORKDIR \"/root\""
        if is_gen_log_file and log_file_path is not None:
            process_command += " STDOUT \"%s\" STDERRTOSTDOUT" % log_file_path
        if is_wait_result:
            if is_set_timeout:
                process_command += " WAIT %ss RETURNSTDOUT RETURNSTDERR" % timeout
            else:
                process_command += " WAIT RETURNSTDOUT RETURNSTDERR"
        self.staf_logger.debug("execute shell command: %s" % process_command)
        result = self.handle.submit(self.host_ip, "PROCESS", process_command)
        self.staf_logger.debug("execute shell command RC: %d" % result.rc)
        self.staf_logger.debug("execute shell command Result: %s" % result.result)
        if result.rc == 0:
            if is_wait_result:
                shell_output = result.resultObj["fileList"][0]["data"]
                shell_err = result.resultObj["fileList"][1]["data"]
                self.staf_logger.debug("shell command output stream informantion: %s" % shell_output)
                if shell_err:
                    self.staf_logger.debug("shell command error stream information: %s" % shell_err)
                return shell_output
            else:
                return result.resultObj
        elif result.rc == 37:
            self.staf_logger.debug("shell command timeout, force stop it")
            self.stop_handle_process(result.resultObj)
            return None
        else:
            return None

    def stop_handle_process(self, process_handle_id):
        result = self.handle.submit(self.host_ip, "PROCESS", "STOP HANDLE %s" % process_handle_id)
        self.staf_logger.debug("stop process RC: %d" % result.rc)
        self.staf_logger.debug("stop process Result: %s" % result.result)
        if result.rc == 0:
            return True
        else:
            return False

    def get_defined_process(self, filter_mode=""):
        command = "LIST HANDLES"
        if filter_mode.upper() == "RUNNING":
            command += " RUNNING"
        elif filter_mode.upper() == "COMPLETED":
            command += " COMPLETED"
        result = self.handle.submit(self.host_ip, "PROCESS", command)
        self.staf_logger.debug("get process RC: %d" % result.rc)
        self.staf_logger.debug("get process Result: %s" % result.result)
        handles_info = []
        if len(result.resultObj) != 0:
            for tmp_item in result.resultObj:
                handles_info.append((tmp_item["handle"], tmp_item["command"]))
        return handles_info

    def __del__(self):
        self.close_staf_handle()


if __name__ == '__main__':
    logger = logging.getLogger("avocado.test")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    ct_staf_1 = LenovoSTAF("10.100.3.49")
    ct_staf_1.get_defined_process(filter_mode="running")
    ct_staf_1.close_staf_handle()
