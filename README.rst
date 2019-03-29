Avocado Cloudtest Test Framework
================================

Avocado Cloudtest is a OpenStack-powered cloud automated test framework which
will cover functional, reliability, performance, security, upgrade tests. Each
test type will be added as a test submodule to this framework. And more types of
test will be added in future.

Avocado-cloudtest is based on an open source project named Avocado which is
a general test framework. We developed cloudtest plugin and test module to
extend it as a cloud automated test framework according to our requirements.

Avocado-cloudtest will provide following:

- A powerful test runner;
- diverse test submodules including reliability, functional, performance,
  security, upgrade, etc;
- Test APIs for test writers;
- A database for results, with a web interface;
- A scheduler for setting up a test grid
- Three kinds of interfaces: Web UI, Command line, REST APi


Setup tempest slave
===================

For CloudTestV1.0 users

Check openstack resource
------------------------

When you get openstack(ThinkCloud) enviroment， you can check resources with the
list below to make sure avocado-cloudtest invoke script file for tempest.

1. admin project exist.
2. User admin can log on admin project.
3. You know the password of admin.
4. There is public network in admin project. And the expected name of the public
   network is public_net.
5. Create a network in admin project, and the expected name for the network is
   share_net.
6. Create a router in admin project to connect share_net and public_net. And the
   expected name of router is share_router.
7. Create two cirros images in admin project, the expected name for both image
   and image_alt is TestVM. User ’cirros’ with password 'cubswin:)' can log in
   instance created by TestVM.

Comments: If you want avocado-cloudtest call scripts to get resource id and
generate configuration file for tempest running, you have to create share_net,
share_router and TestVM. You can only change the name for share_net,
share_router and TestVM in /avocado-cloudtest/cloudtest/openstack/
get_resource.py. Just using share_net, share_router and TestVM as names is
recommended.

Install tempest and avocado
---------------------------

git server: 10.100.4.211

1. Download avocado
   git clone ssh://10.100.4.211:29418/avocado-cloudtest
2. Download tempest
   git clone ssh://10.100.4.211:29418/tempest
3. Install tempest
   ./install.sh -r slave -m tempest

tips: If you encounter any issue, when you install tempest. You can always find
some of tempest dependencies in the folder
/tempest/dependencies/tempest. dependencies.

4. Install avocado
   ./install.sh -r slave -m avocado
5. List tempest test cases
   avocado list

Config tests.cfg
-----------------

The path of tests.cfg is /avocado-cloudtest/cloudtest/config/tests.cfg. You have
to finish tests.cfg configuration instead of tempest.conf, before you run
tempest test cases.
The following is all the items related to tempest.
For CloudTestV1.0, you must not update admin_project = admin and
admin_username = admin, except you set prepare_resource false. In this case, the
latest five items do not work. If you set prepare_resource false, you have to
check openstack resource yourself, and generate tempest.conf by hand.

report_send_to_email = zhouyf6@lenovo.com
thinkstack_version = 4.0
identity_uri_ip  = 10.100.4.163
openstack_ssh_username = root
openstack_ssh_password = 123456

- tempest:
        # Some common parameters here
        post_command =
        tempest_path = /root/tempest     #Tempest installation path
        ct_type = integrate
        test_types = "tempest.api tempest.scenario"
        tests = all
        # run_type could be 'case', 'class', 'suite', or 'whole'
        tempest_run_type = whole
        tempest_test_timeout = 1200
        tempest_run_mode = serial
        auto_rerun_on_failure = false
        auto_rerun_times = 1
        prepare_resource = true      #Run script to prepare resource for tempest
                                      running or not. setting it true means to
                                      run the script.
        # OpenStack environment related parameters
        #require parameters
        admin_project = admin
        admin_username = admin
        admin_password = admin
        identity_port = 5000
        project_network_cidr = 192.168.114.0/24  #The ip address of network
                                                  created by tempest test cases.

Using avocado
=============

The most straightforward way of `using` avocado is to install packages
available for your distro:

1) Fedora/RHEL

   Avocado is not yet officially packed in Fedora/RHEL, but you can use avocado
   yum repositories by putting corresponding file into ``/etc/yum.repos.d``.

   *  `Fedora repo <https://repos-avocadoproject.rhcloud.com/static/avocado-fedora.repo>`__
   *  `RHEL repo <https://repos-avocadoproject.rhcloud.com/static/avocado-el.repo>`__

   and install it by ``yum install avocado`` (or using ``dnf``)

Once you install it, you can start exploring it by checking the output of
``avocado --help`` and the test runner man-page, accessible via ``man avocado``.

If you want to `develop` avocado, or run it directly from the git repository,
you have a couple of options:

1) The avocado test runner was designed to run in tree, for rapid development
   prototypes. After running::

    $ make develop

   Just use::

    $ scripts/avocado --help

2) Installing avocado in the system is also an option, although remember that
   distutils has no ``uninstall`` functionality::

    $ sudo python setup.py install
    $ avocado --help

Documentation
-------------

Avocado comes with in tree documentation about the most advanced features and
its API. It can be built with ``sphinx``, but a publicly available build of
the latest master branch documentation and releases can be seen on `read the
docs <https://readthedocs.org/>`__:

http://avocado-framework.readthedocs.org/

If you want to build the documentation yourself:

1) Make sure you have the package ``python-sphinx`` installed. For Fedora::

    $ sudo yum install python-sphinx

2) For Mint/Ubuntu/Debian::

    $ sudo apt-get install python-sphinx

3) Optionally, you can install the read the docs theme, that will make your
   in-tree documentation look just like the online version::

    $ sudo pip install sphinx_rtd_theme

4) Build the docs::

    $ make -C docs html

5) Once done, point your browser to::

    $ [your-browser] docs/build/html/index.html
