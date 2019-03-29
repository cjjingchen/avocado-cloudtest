import logging
import os

import aexpect

from avocado.utils import process as avocado_process
from cloudtest import error_context

# try:
#     import PIL.Image
# except ImportError:
#     logging.warning('No python imaging library installed. PPM image '
#                     'conversion to JPEG disabled. In order to enable it, '
#                     'please install python-imaging or the equivalent for your '
#                     'distro.')

_screendump_thread = None
_screendump_thread_termination_event = None


def process_command(test, params, env, command, command_timeout,
                    command_noncritical):
    """
    Pre- or post- custom commands to be executed before/after a test is run

    :param test: An Autotest test object.
    :param params: A dict containing all VM and image parameters.
    :param env: The environment (a dict-like object).
    :param command: Command to be run.
    :param command_timeout: Timeout for command execution.
    :param command_noncritical: If True test will not fail if command fails.
    """
    # Export environment vars
    for k in params:
        os.putenv("KVM_TEST_%s" % k, str(params[k]))
    # Execute commands
    try:
        avocado_process.system("cd %s; %s" % (test.bindir, command), shell=True)
    except avocado_process.CmdError, e:
        if command_noncritical:
            logging.warn(e)
        else:
            raise


def process(test, params, env, image_func, vm_func, vm_first=False):
    """
    Pre- or post-process VMs and images according to the instructions in params.
    Call image_func for each image listed in params and vm_func for each VM.

    :param test: An Autotest test object.
    :param params: A dict containing all VM and image parameters.
    :param env: The environment (a dict-like object).
    :param image_func: A function to call for each image.
    :param vm_func: A function to call for each VM.
    :param vm_first: Call vm_func first or not.
    """
    def _call_vm_func():
        for vm_name in params.objects("vms"):
            vm_params = params.object_params(vm_name)
            vm_func(test, vm_params, env, vm_name)

    def _call_image_func():
        if params.get("skip_image_processing") == "yes":
            return

    if not vm_first:
        _call_image_func()

    _call_vm_func()

    if vm_first:
        _call_image_func()


@error_context.context_aware
def preprocess(test, params, env):
    """
    Preprocess all VMs and images according to the instructions in params.
    Also, collect some host information, such as the KVM version.

    :param test: An Autotest test object.
    :param params: A dict containing all VM and image parameters.
    :param env: The environment (a dict-like object).
    """
    error_context.context("preprocessing")

    # For KVM to work in Power8 systems we need to have SMT=off
    # and it needs to be done as root, here we do a check whether
    # we satisfy that condition, if not try to make it off
    # otherwise throw TestError with respective error message
    #cmd = "grep cpu /proc/cpuinfo | awk '{print $3}' | head -n 1"
    #cpu_output = avocado_process.system_output(cmd, shell=True).strip().upper()
    #if "POWER8" in cpu_output:
    #    test_setup.disable_smt()

    ## First, let's verify if this test does require root or not. If it
    ## does and the test suite is running as a regular user, we shall just
    ## throw a TestSkipError exception, which will skip the test.
    #if params.get('requires_root', 'no') == 'yes':
    #    utils_misc.verify_running_as_root()

    ## throw a TestSkipError exception if command requested by test is not
    ## installed.
    #if params.get("cmds_installed_host"):
    #    for cmd in params.get("cmds_installed_host").split():
    #        try:
    #            path.find_command(cmd)
    #        except path.CmdNotFoundError, msg:
    #            raise exceptions.TestSkipError(msg.message)

    ## enable network proxies setting in urllib2
    #if params.get("network_proxies"):
    #    proxies = {}
    #    for proxy in re.split(r"[,;]\s*", params["network_proxies"]):
    #        proxy = dict([re.split(r"_proxy:\s*", proxy)])
    #        proxies.update(proxy)
    #    handler = urllib2.ProxyHandler(proxies)
    #    opener = urllib2.build_opener(handler)
    #    urllib2.install_opener(opener)

    #vm_type = params.get('vm_type')

    #setup_pb = False
    #ovs_pb = False
    #for nic in params.get('nics', "").split():
    #    nic_params = params.object_params(nic)
    #    if nic_params.get('netdst') == 'private':
    #        setup_pb = True
    #        params_pb = nic_params
    #        params['netdst_%s' % nic] = nic_params.get("priv_brname", 'atbr0')
    #        if nic_params.get("priv_br_type") == "openvswitch":
    #            ovs_pb = True

    #if setup_pb:
    #    if ovs_pb:
    #        brcfg = test_setup.PrivateOvsBridgeConfig(params_pb)
    #    else:
    #        brcfg = test_setup.PrivateBridgeConfig(params_pb)
    #    brcfg.setup()

    #base_dir = data_dir.get_data_dir()
    #if params.get("storage_type") == "iscsi":
    #    iscsidev = qemu_storage.Iscsidev(params, base_dir, "iscsi")
    #    params["image_name"] = iscsidev.setup()
    #    params["image_raw_device"] = "yes"

    #if params.get("storage_type") == "lvm":
    #    lvmdev = qemu_storage.LVMdev(params, base_dir, "lvm")
    #    params["image_name"] = lvmdev.setup()
    #    params["image_raw_device"] = "yes"
    #    env.register_lvmdev("lvm_%s" % params["main_vm"], lvmdev)

    #if params.get("storage_type") == "nfs":
    #    image_nfs = nfs.Nfs(params)
    #    image_nfs.setup()
    #    image_name_only = os.path.basename(params["image_name"])
    #    params['image_name'] = os.path.join(image_nfs.mount_dir,
    #                                        image_name_only)
    #    for image_name in params.objects("images"):
    #        name_tag = "image_name_%s" % image_name
    #        if params.get(name_tag):
    #            image_name_only = os.path.basename(params[name_tag])
    #            params[name_tag] = os.path.join(image_nfs.mount_dir,
    #                                            image_name_only)

    ## Start tcpdump if it isn't already running
    ## The fact it has to be started here is so that the test params
    ## have to be honored.
    #env.start_tcpdump(params)

    ## Add migrate_vms to vms
    #migrate_vms = params.objects("migrate_vms")
    #if migrate_vms:
    #    vms = list(set(params.objects("vms") + migrate_vms))
    #    params["vms"] = ' '.join(vms)

    ## Destroy and remove VMs that are no longer needed in the environment
    #requested_vms = params.objects("vms")
    #for key in env.keys():
    #    vm = env[key]
    #    if not isinstance(vm, virt_vm.BaseVM):
    #        continue
    #    if vm.name not in requested_vms:
    #        vm.destroy()
    #        del env[key]

    #if (params.get("auto_cpu_model") == "yes" and
    #        vm_type == "qemu"):
    #    if not env.get("cpu_model"):
    #        env["cpu_model"] = utils_misc.get_qemu_best_cpu_model(params)
    #    params["cpu_model"] = env.get("cpu_model")

    #kvm_ver_cmd = params.get("kvm_ver_cmd", "")

    #if kvm_ver_cmd:
    #    try:
    #        kvm_version = avocado_process.system_output(kvm_ver_cmd).strip()
    #    except avocado_process.CmdError:
    #        kvm_version = "Unknown"
    #else:
    #    # Get the KVM kernel module version and write it as a keyval
    #    if os.path.exists("/dev/kvm"):
    #        try:
    #            kvm_version = open("/sys/module/kvm/version").read().strip()
    #        except Exception:
    #            kvm_version = os.uname()[2]
    #    else:
    #        warning_msg = "KVM module not loaded"
    #        if params.get("enable_kvm", "yes") == "yes":
    #            raise exceptions.TestSkipError(warning_msg)
    #        logging.warning(warning_msg)
    #        kvm_version = "Unknown"

    #logging.debug("KVM version: %s" % kvm_version)
    #test.write_test_keyval({"kvm_version": kvm_version})

    ## Get the KVM userspace version and write it as a keyval
    #kvm_userspace_ver_cmd = params.get("kvm_userspace_ver_cmd", "")

    #if kvm_userspace_ver_cmd:
    #    try:
    #        kvm_userspace_version = avocado_process.system_output(
    #            kvm_userspace_ver_cmd).strip()
    #    except avocado_process.CmdError:
    #        kvm_userspace_version = "Unknown"
    #else:
    #    qemu_path = utils_misc.get_qemu_binary(params)
    #    version_output = avocado_process.system_output("%s -help" % qemu_path,
    #                                                   verbose=False)
    #    version_line = version_output.split('\n')[0]
    #    matches = re.findall("[Vv]ersion .*?,", version_line)
    #    if matches:
    #        kvm_userspace_version = " ".join(matches[0].split()[1:]).strip(",")
    #    else:
    #        kvm_userspace_version = "Unknown"

    #logging.debug("KVM userspace version: %s" % kvm_userspace_version)
    #test.write_test_keyval({"kvm_userspace_version": kvm_userspace_version})

    #libvirtd_inst = utils_libvirtd.Libvirtd()

    #if params.get("setup_hugepages") == "yes":
    #    h = test_setup.HugePageConfig(params)
    #    suggest_mem = h.setup()
    #    if suggest_mem is not None:
    #        params['mem'] = suggest_mem
    #    if vm_type == "libvirt":
    #        libvirtd_inst.restart()

    #if params.get("setup_thp") == "yes":
    #    thp = test_setup.TransparentHugePageConfig(test, params)
    #    thp.setup()

    #if params.get("setup_ksm") == "yes":
    #    ksm = test_setup.KSMConfig(params, env)
    #    ksm.setup(env)

    #if params.get("setup_egd") == "yes":
    #    egd = test_setup.EGDConfig(params, env)
    #    egd.setup()

    #if vm_type == "libvirt":
    #    if params.get("setup_libvirt_polkit") == "yes":
    #        pol = test_setup.LibvirtPolkitConfig(params)
    #        try:
    #            pol.setup()
    #        except test_setup.PolkitWriteLibvirtdConfigError, e:
    #            logging.error(str(e))
    #        except test_setup.PolkitRulesSetupError, e:
    #            logging.error(str(e))
    #        except Exception, e:
    #            logging.error("Unexpected error: '%s'" % str(e))
    #        libvirtd_inst.restart()

    #if vm_type == "libvirt":
    #    connect_uri = params.get("connect_uri")
    #    connect_uri = libvirt_vm.normalize_connect_uri(connect_uri)
    #    # Set the LIBVIRT_DEFAULT_URI to make virsh command
    #    # work on connect_uri as default behavior.
    #    os.environ['LIBVIRT_DEFAULT_URI'] = connect_uri

    ## Execute any pre_commands
    #if params.get("pre_command"):
    #    process_command(test, params, env, params.get("pre_command"),
    #                    int(params.get("pre_command_timeout", "600")),
    #                    params.get("pre_command_noncritical") == "yes")

    #kernel_extra_params_add = params.get("kernel_extra_params_add", "")
    #kernel_extra_params_remove = params.get("kernel_extra_params_remove", "")
    #if params.get("disable_pci_msi"):
    #    disable_pci_msi = params.get("disable-pci_msi")
    #    if disable_pci_msi == "yes":
    #        if "pci=" in kernel_extra_params_add:
    #            kernel_extra_params_add = re.sub("pci=.*?\s+", "pci=nomsi ",
    #                                             kernel_extra_params_add)
    #        else:
    #            kernel_extra_params_add += " pci=nomsi"
    #        params["ker_remove_similar_pci"] = "yes"
    #    else:
    #        kernel_extra_params_remove += " pci=nomsi"

    #if kernel_extra_params_add or kernel_extra_params_remove:
    #    global kernel_cmdline, kernel_modified
    #    image_filename = storage.get_image_filename(params,
    #                                                data_dir.get_data_dir())
    #    grub_file = params.get("grub_file", "/boot/grub2/grub.cfg")
    #    kernel_cfg_pos_reg = params.get("kernel_cfg_pos_reg",
    #                                    r".*vmlinuz-\d+.*")

    #    disk_obj = utils_disk.GuestFSModiDisk(image_filename)
    #    kernel_config_ori = disk_obj.read_file(grub_file)
    #    kernel_config = re.findall(kernel_cfg_pos_reg, kernel_config_ori)
    #    if not kernel_config:
    #        raise exceptions.TestError("Cannot find the kernel config, reg "
    #                                   "is %s" % kernel_cfg_pos_reg)
    #    kernel_config = kernel_config[0]
    #    kernel_cmdline = kernel_config

    #    kernel_need_modify = False
    #    kernel_config_set = kernel_config
    #    debug_msg = "Guest cmdline extra_params setting:"
    #    if kernel_extra_params_add:
    #        debug_msg += " added '%s'" % kernel_extra_params_add
    #        kernel_extra_params = kernel_extra_params_add.split()
    #        for kernel_extra_param in kernel_extra_params:
    #            param_tag = kernel_extra_param.split("=")[0]
    #            params_kernel = params.object_params(param_tag)
    #            rm_s = params_kernel.get("ker_remove_similar", "no") == "yes"
    #            kernel_config_set = utils_misc.add_ker_cmd(kernel_config_set,
    #                                                       kernel_extra_param,
    #                                                       rm_s)
    #    if kernel_extra_params_remove:
    #        debug_msg += " removed '%s'" % kernel_extra_params_remove
    #        kernel_extra_params = kernel_extra_params_remove.split()
    #        for kernel_extra_param in kernel_extra_params:
    #            kernel_config_set = utils_misc.rm_ker_cmd(kernel_config_set,
    #                                                      kernel_extra_param)

    #    if kernel_config_set.strip() != kernel_cmdline.strip():
    #        kernel_need_modify = True

    #    if kernel_need_modify:
    #        for vm in env.get_all_vms():
    #            if vm:
    #                vm.destroy()
    #                env.unregister_vm(vm.name)
    #        disk_obj.replace_image_file_content(grub_file, kernel_config,
    #                                            kernel_config_set)
    #        kernel_modified = True
    #    del disk_obj
    #    params["check_kernel_cmd_line_from_serial"] = "yes"
    #    if kernel_extra_params_add:
    #        params['kernel_options_exist'] = kernel_extra_params_add
    #    if kernel_extra_params_remove:
    #        params['kernel_options_not_exist'] = kernel_extra_params_remove
    #    logging.debug(debug_msg)

    ## Clone master image from vms.
    #base_dir = data_dir.get_data_dir()
    #if params.get("master_images_clone"):
    #    for vm_name in params.get("vms").split():
    #        vm = env.get_vm(vm_name)
    #        if vm:
    #            vm.destroy()
    #            env.unregister_vm(vm_name)

    #        vm_params = params.object_params(vm_name)
    #        for image in vm_params.get("master_images_clone").split():
    #            image_obj = qemu_storage.QemuImg(params, base_dir, image)
    #            image_obj.clone_image(params, vm_name, image, base_dir)

    ## Preprocess all VMs and images
    #if params.get("not_preprocess", "no") == "no":
    #    process(test, params, env, preprocess_image, preprocess_vm)

    ## Start the screendump thread
    #if params.get("take_regular_screendumps") == "yes":
    #    global _screendump_thread, _screendump_thread_termination_event
    #    _screendump_thread_termination_event = threading.Event()
    #    _screendump_thread = threading.Thread(target=_take_screendumps,
    #                                          name='ScreenDump',
    #                                          args=(test, params, env))
    #    _screendump_thread.start()

    ## Start the register query thread
    #if params.get("store_vm_register") == "yes" and\
    #   params.get("vm_type") == "qemu":
    #    global _vm_register_thread, _vm_register_thread_termination_event
    #    _vm_register_thread_termination_event = threading.Event()
    #    _vm_register_thread = threading.Thread(target=_store_vm_register,
    #                                           name='VmRegister',
    #                                           args=(test, params, env))
    #    _vm_register_thread.start()

    return params


@error_context.context_aware
def postprocess(test, params, env):
    """
    Postprocess all VMs and images according to the instructions in params.

    :param test: An Autotest test object.
    :param params: Dict containing all VM and image parameters.
    :param env: The environment (a dict-like object).
    """
    error_context.context("postprocessing")
    err = ""

    # Terminate the tcpdump thread
    env.stop_tcpdump()

    # Kill all aexpect tail threads
    aexpect.kill_tail_threads()

    # Execute any post_commands
    if params.get("post_command"):
        try:
            process_command(test, params, env, params.get("post_command"),
                            int(params.get("post_command_timeout", "600")),
                            params.get("post_command_noncritical") == "yes")
        except Exception, details:
            err += "\nPostprocess command: %s" % str(details).replace('\n',
                                                                      '\n  ')
            logging.error(details)


def postprocess_on_error(test, params, env):
    """
    Perform postprocessing operations required only if the test failed.

    :param test: An Autotest test object.
    :param params: A dict containing all VM and image parameters.
    :param env: The environment (a dict-like object).
    """
    params.update(params.object_params("on_error"))
