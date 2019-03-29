%global modulename avocado-cloudtest
%if ! 0%{?commit:1}
 %define commit 98ef0be55b3288036e1d375bfe22f4185f99c22f
%endif
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Summary: Cloud Automated Test Platform
Name: avocado-cloudtest
Version: 2.0
Release: 0%{?dist}
License: GPLv2
Group: Development/Tools
URL: http://gitlab.lenovo.com/cloud/avocado-cloudtest
Source0: http://zhouyf6@gitlab.lenovo.com/cloud/%{name}/archive/%{commit}/%{name}-%{version}-%{shortcommit}.tar.gz
BuildArch: noarch
Requires: python, python-requests, fabric, pyliblzma, libvirt-python, pystache, gdb, gdb-gdbserver, python-stevedore
BuildRequires: python2-devel, python-setuptools, python-docutils, python-mock, python-psutil, python-sphinx, python-requests, python2-aexpect, pystache, yum, python-stevedore, python-lxml, perl-Test-Harness, fabric, python-flexmock, python-testtools

%if 0%{?el6}
Requires: PyYAML
Requires: python-argparse, python-importlib, python-logutils, python-unittest2, procps
BuildRequires: PyYAML
BuildRequires: python-argparse, python-importlib, python-logutils, python-unittest2, procps
%else
Requires: python-yaml, procps-ng
BuildRequires: python-yaml, procps-ng
%endif

%if 0%{?fedora} >= 25
BuildRequires: kmod
%endif
%if 0%{?rhel} >= 7
BuildRequires: kmod
%endif

%description
Avocado-cloudtest is a framework providing cloud automated testing.

%prep
%setup -q -n %{name}-%{commit}

%build
%{__python} setup.py build
%{__make} man

%install
%{__python} setup.py install --root %{buildroot} --skip-build
%{__mkdir} -p %{buildroot}%{_mandir}/man1
%{__install} -m 0644 man/avocado.1 %{buildroot}%{_mandir}/man1/avocado.1
%{__install} -m 0644 man/avocado-rest-client.1 %{buildroot}%{_mandir}/man1/avocado-rest-client.1

%check
selftests/run

%files
%defattr(-,root,root,-)
%doc README.rst LICENSE
%dir /etc/avocado
%dir /etc/avocado/conf.d
%dir /etc/avocado/sysinfo
%dir /etc/avocado/scripts/job/pre.d
%dir /etc/avocado/scripts/job/post.d
%dir /usr/share/avocado-cloudtest
%dir /usr/share/avocado-cloudtest/config
%dir /usr/share/avocado-cloudtest/tests
%dir /usr/share/avocado-cloudtest/tests/vm_reliability_tester
%dir /usr/share/avocado-cloudtest/tests/reliability
%dir /usr/share/avocado-cloudtest/tests/reliability/fault
%dir /usr/share/avocado-cloudtest/tests/reliability/workload
%config(noreplace)/etc/avocado/avocado.conf
%config(noreplace)/etc/avocado/conf.d/README
%config(noreplace)/etc/avocado/sysinfo/commands
%config(noreplace)/etc/avocado/sysinfo/files
%config(noreplace)/etc/avocado/sysinfo/profilers
%config(noreplace)/etc/avocado/scripts/job/pre.d/README
%config(noreplace)/etc/avocado/scripts/job/post.d/README
%{python_sitelib}/avocado*
%{_bindir}/avocado
%{_bindir}/avocado-rest-client
%{_mandir}/man1/avocado.1.gz
%{_mandir}/man1/avocado-rest-client.1.gz
%{_docdir}/avocado/avocado.rst
%{_docdir}/avocado/avocado-rest-client.rst
%{_libexecdir}/avocado/avocado-bash-utils
%{_libexecdir}/avocado/avocado_debug
%{_libexecdir}/avocado/avocado_error
%{_libexecdir}/avocado/avocado_info
%{_libexecdir}/avocado/avocado_warn

%package plugins-output-html
Summary: Avocado HTML report plugin
Requires: avocado == %{version}, pystache

%description plugins-output-html
Adds to avocado the ability to generate an HTML report at every job results
directory. It also gives the user the ability to write a report on an
arbitrary filesystem location.

%files plugins-output-html

%package examples
Summary: Avocado Test Framework Example Tests
Requires: avocado == %{version}

%description examples
The set of example tests present in the upstream tree of the Avocado framework.
Some of them are used as functional tests of the framework, others serve as
examples of how to write tests on your own.

%changelog
* Mon Jul 3 2017 Yingfu Zhou <zhouyf6@lenovo.com> - 2.0_1_g7813c51
-  Change version and spec file

* Mon Jul 3 2017 Yingfu Zhou <zhouyf6@lenovo.com> - 2.0
-  Merge "[SDS REST API Test] Delete use of env for create warning." into
  release-v2.0
-  [SDS REST API Test] Delete use of env for create warning.
-  [SDS REST API Test]Fixed a bug for server delete test
-  Merge "[SDS REST API Test]1.Resolved wrong start time in html report.
  2.Improved the code of get_available_server. 3.Updated create and
  delete server tests. Change-Id:
  I42ae38fa614ec60ccef7a0432334343b8ef8abdd" into release-v2.0
-  [SDS REST API Test]1.Resolved wrong start time in html report.
  2.Improved the code of get_available_server. 3.Updated create and
  delete server tests. Change-Id:
  I42ae38fa614ec60ccef7a0432334343b8ef8abdd
-  [SDS REST API Test] Improvements for rest exceptions
-  Merge "[SDS REST API Test] Assign default params for servers ops test"
  into release-v2.0
-  [SDS REST API Test] Assign default params for servers ops test
-  [SDS REST API Test] Modify a problem of create monitor.
-  [SDS REST API Test] Add sleep time for create rbd warning.
-  [SDS REST API Test]update qos, clustersconf api schema
-  [SDS REST API Test] Modify get follower role monitor.
-  [SDS REST API Test]1.Updated delete server test.
-  [SDS REST API Test] Delete env of snapshot.
-  [SDS REST API Test]1.Modify deploy multi hosts to multi threads mode.
  2.Improved servers tests. 3.Removed create server test. Change-Id:
  I14afd64a9a0dddd198ce1316cdda990946e3529a
-  [SDS REST API Test]update pool & rbd tests for timing issue
-  [SDS REST API Test] Change validation of cluster expand
-  [SDS REST API Test] Improved clusters client due to REST interface
  change
-  [SDS REST API Test] Fixes for clusters test
-  Merge "[SDS REST API Test] Improvements for servers test" into
  release-v2.0
-  Merge "Revert "Get the IP address of slave machine as sysinfo"" into
  release-v2.0
-  [SDS REST API Test] Improvements for servers test
-  Revert "Get the IP address of slave machine as sysinfo"
-  [SDS REST API Test] Modify set_led and delete snapshots params get from
  env.
-  Get the IP address of slave machine as sysinfo
-  Catch more exceptions for ceph REST API test
-  Merge "[SDS REST API Test] Move clusters test after servers test" into
  release-v2.0
-  [SDS REST API Test] Move clusters test after servers test
-  [SDS REST API Test]sort qos cases
-  Merge "[SDS REST API Test]Fix a bug of delete warning." into
  release-v2.0
-  [SDS REST API Test]Fix a bug of delete warning.
-  [SDS REST API Test] Improvements for clusters test
-  Merge "[SDS REST API Test] Improved servers operation tests" into
  release-v2.0
-  [SDS REST API Test] Improved servers operation tests
-  [SDS REST API Test] Modify a bug for get data from env.
-  Merge "[SDS REST API Test] Add code to configure zabbix server" into
  release-v2.0
-  [SDS REST API Test] Add code to configure zabbix server
-  [SDS REST API Test]rbd move rest api interface changed, so update it
  accordingly
-  [SDS REST API Test] Modify stop_monitor validation and delete case
  snapshot_delete.
-  [SDS REST API Test] Improved code to servers test
-  Merge "[SDS REST API Test] Modify warnings config." into release-v2.0
-  [SDS REST API Test] Modify warnings config.
-  [SDS REST API Test]Updated test code for failed group tests and updated
  the test sequence of servers test and improved code to deploy cluster
-  Merge "[SDS REST API Test]Update test code for failed pool & iscsi
  tests" into release-v2.0
-  [SDS REST API Test]Update test code for failed pool & iscsi tests
-  [SDS REST API Test]Modify a bug of snapshot.
-  Merge "[SDS REST API Test] Improved code to deploy cluster" into
  release-v2.0
-  [SDS REST API Test] Improved code to deploy cluster
-  Merge "[SDS REST API Test] Change a parameter of cluster create test"
  into release-v2.0
-  [SDS REST API Test] Change a parameter of cluster create test
-  Merge "[SDS REST API Test] Improved scenario deploy test" into
  release-v2.0
-  [SDS REST API Test] Improved scenario deploy test
-  Merge "[SDS REST API Test]Add thread for create monitor." into
  release-v2.0
-  [SDS REST API Test]Add thread for create monitor.
-  [SDS REST API Test] Add two parameters for delete cluster test
-  Merge "[SDS REST API Test]Modify snapshots test config" into
  release-v2.0
-  [SDS REST API Test]Modify snapshots test config
-  [SDS REST API Test] Improved deploy scenario test
-  Merge "[SDS REST API Test] Improved cluster expand test" into
  release-v2.0
-  Merge "[SDS REST API test]1.Add test_deploy_cluster_with_three_hosts
  scenario test. 2.Updated the tests sequence of ceph api test." into
  release-v2.0
-  Merge "[SDS REST API Test]The id of creating pool changed from pool id
  to job id, update test code accordingly" into release-v2.0
-  [SDS REST API Test] Improved cluster expand test
-  [SDS REST API test]1.Add test_deploy_cluster_with_three_hosts scenario
  test. 2.Updated the tests sequence of ceph api test.
-  [SDS REST API Test]The id of creating pool changed from pool id to job
  id, update test code accordingly
-  [SDS REST API test] remove some params from monitorfun
-  Merge "[SDS REST API Test] Change param name of SDS test type" into
  release-v2.0
-  [SDS REST API Test] Change param name of SDS test type
-  [SDS REST API Test]Add test cases for warning.
-  [SDS REST API Test]Set default parameters for groups tests
-  [SDS REST API Test] Improved some clusters tests
-  [SDS REST API Test]1.Set default parameters for osd, rbd & iscsi tests
  2. Update test code depending on dev code
-  [SDS REST API Test] Improvements for clusters tests
-  Merge "[SDS REST API test]1.Modify add_cephed_server test depending on
  dev code 2.Setup default parameters for parent_bucket and server_id"
  into release-v2.0
-  [SDS REST API Test] Add some new cases for creating cluster
-  [SDS REST API test]1.Modify add_cephed_server test depending on dev
  code 2.Setup default parameters for parent_bucket and server_id
-  [SDS REST API test] Save cluster ID instead of the whole cluster info
-  [SDS REST API test]Set up default parameters for the delayed delete
  time
-  [SDS REST API test]improve code avoid exception
-  Merge "[SDS REST API test]Add warnings test for ceph api." into
  release-v2.0
-  Merge "[SDS REST API test] Fix bugs for monitorfun test for ceph api
  tests" into release-v2.0
-  [SDS REST API test] Fix bugs for monitorfun test for ceph api tests
-  [SDS REST API test]Add warnings test for ceph api.
-  [SDS REST API test] Add query operation log test for ceph api tests.
  And update a default parameter for groups api test.
-  [SDS REST API test]Fix a little issue of iscsi delete target
-  [SDS REST API test]Fix test issue of iscsi depending on dev code
-  Merge "[SDS REST API test] Add monitorfun test for ceph api tests" into
  release-v2.0
-  [SDS REST API test] Add monitorfun test for ceph api tests
-  Merge "[SDS REST API test]Fix some bugs for test_rbd and test iscsi
  tests" into release-v2.0
-  Merge "Fix a bug for qos enable" into release-v2.0
-  [SDS REST API test]Fix some bugs for test_rbd and test iscsi tests
-  Merge "[SDS REST API test]Add set led test for node_info." into
  release-v2.0
-  [SDS REST API test] Fixed a bug for servers stop test
-  [SDS REST API test]Add set led test for node_info.
-  Merge "[SDS REST API test]Add groups tests and update servers tests"
  into release-v2.0
-  [SDS REST API test]Add groups tests and update servers tests
-  Merge "[SDS REST API test]Add iscsi tests and update osd test_delete"
  into release-v2.0
-  Fix a bug for qos enable
-  [SDS REST API test] Add schema validation for monitors query interface.
-  [SDS REST API test]Add iscsi tests and update osd test_delete
-  [SDS REST API test]Make snapshots can delete by snapshots_id and resort
  the test order.
-  [SDS REST API test] Add clusterconf and qos test for ceph api tests
-  Merge "[SDS REST API test]Add node info test for ceph api tests;
  Cpuinfo of server(3.14.2) can get from server detail, so 3.14.1 and
  3.14.2 merge to one test named query_node_detail." into release-v2.0
-  [SDS REST API test]Add node info test for ceph api tests; Cpuinfo of
  server(3.14.2) can get from server detail, so 3.14.1 and 3.14.2 merge
  to one test named query_node_detail.
-  Add more tests for osd and set default parameters for osd tests
-  Add more ceph storagemgmt api automation for rbd and update pool & rbd
  existing tests for default parameters
-  Add default parameters for ceph server api tests. Updated parts of
  tests for ceph group api.
-  Add monitor tests for ceph api test.
-  Merge "[SDS REST API Test] Add iSCSI rest api tests." into release-v2.0
-  Merge "Added Ceph API Test for host and updated parts of group test,
  and fixed a bug for act_to_process." into release-v2.0
-  [SDS REST API Test] Add iSCSI rest api tests.
-  Added Ceph API Test for host and updated parts of group test, and fixed
  a bug for act_to_process.
-  Add snapshots tests for ceph api test.
-  Add osd, pool and rdb test cases for ceph API test
-  Add groups related api test and some framework improvements.
-  Huge improvements for rest client and add groups client.
-  Add parameter body for get method
-  Add tempest conf sample file
-  Merge "Add json schema validation and some other improvements." into
  release-v2.0
-  Add json schema validation and some other improvements.
-  tempest and stability can prepare resources.
-  Merge "Add delete,operation,etc for cluster api test." into
  release-v2.0
-  Merge "Add syntribos install and modify syntribos test." into
  release-v2.0
-  Merge "Add more clusters related api tests." into release-v2.0
-  Add delete,operation,etc for cluster api test.
-  Add more clusters related api tests.
-  Merge "Improvement for ceph mgmt api test framework." into release-v2.0
-  Improvement for ceph mgmt api test framework.
-  Add syntribos install and modify syntribos test.
-  Merge "Network workload using ltp." into release-v2.0
-  Network workload using ltp.
-  Merge "Add pools_client and snapshot_client." into release-v2.0
-  Add pools_client and snapshot_client.
-  Merge "Add snapshots_client for operating snapshots." into release-v2.0
-  Add snapshots_client for operating snapshots.
-  Merge "Modify security module can getting endpoint automatic." into
  release-v2.0
-  Merge "Add support of stopping test plan via ssh method for script"
  into release-v2.0
-  Merge "Add 'api' and 'scenarios' test types support for ceph test."
  into release-v2.0
-  Add 'api' and 'scenarios' test types support for ceph test.
-  Modify security module can getting endpoint automatic.
-  Add support of stopping test plan via ssh method for script
-  Merge changes Ia9f1c95d,Id3ba7a8f into release-v2.0
-  Get items from rally result table and write env.
-  Merge "Improvements for storage management system rest api test." into
  release-v2.0
-  Improvements for storage management system rest api test.
-  Update test fio_io_workload and change the file name from io.py to
  io_workload.py
-  Merge "Add sub framework of Ceph management rest api test." into
  release-v2.0
-  Add sub framework of Ceph management rest api test.
-  1.Update for OpenStack process fault injection, using new
  cloud_management module. 2.Node/Service network partition injection
  fault by iptables rules.
-  Modify network fault using cloud manager module.
-  Remove some parameters to run smartly for syntribos.
-  Merge "Get session with function to avoid hardcode" into release-v2.0
-  Improvement for syntribos test.
-  Get session with function to avoid hardcode
-  Merge "Modify service_fault using cloud_manager module. Modify config"
  into release-v2.0
-  Modify service_fault using cloud_manager module. Modify config
-  Merge "Improvements for script of dispatching test plan." into
  release-v2.0
-  Improvements for script of dispatching test plan.
-  Merge "Catch one more exception for tempest test." into release-v2.0
-  Catch one more exception for tempest test.
-  Merge "Fix a bug in utils_injection module" into release-v2.0
-  Fix a bug in utils_injection module
-  Merge "add node fault module" into release-v2.0
-  Set OpenStack environment variables before running VM_reliability_test.
-  add node fault module
-  Improvements for tempest test and injection module
-  Fix bug that injections should wait for threads to complete
-  Merge "Filter out useless combo reliability test" into release-v2.0
-  Filter out useless combo reliability test
-  Merge "Update IO fault tests and add the tests for ceph" into
  release-v2.0
-  Update IO fault tests and add the tests for ceph
-  Change force injection to false by default
-  Delete unused parameters and improvement for vm_reliability_test.
-  Improvements for injection mechanism
-  Add some miss-submitted files and fix some indent failures
-  Merge "Improvements for injection and cloud management" into
  release-v2.0
-  Improvements for injection and cloud management
-  Improvements for injection and cloud management
-  Little fix for cloud management related modules
-  Add cloud management module and related modifcation.
-  Fix some pylint test failures.
-  Remove unused module for pylint test
-  Merge "Remove sudo from executing make check test" into release-v2.0
-  Remove sudo from executing make check test
-  Merge "Improvements for self tests including pylint" into release-v2.0
-  Improvements for self tests including pylint
-  Merge "Add injection support for reliability test." into release-v2.0
-  Add injection support for reliability test.
-  Merge "Added network fault injection and modified config file Modify
  network fault according to comments" into release-v2.0
-  Added network fault injection and modified config file Modify network
  fault according to comments
-  Merge "Change Makefile to reflect correct framework name" into
  release-v2.0
-  Change Makefile to reflect correct framework name
-  Merge "Add IO workload test cases" into release-v2.0
-  Merge "add stress-ng pkg, add openstack module, update install.sh" into
  release-v2.0
-  Add IO workload test cases
-  add stress-ng pkg, add openstack module, update install.sh
-  Merge "Add log configuration and fixed a bug for get_pids_from_name
  function" into release-v2.0
-  Add IO fault test cases
-  Add log configuration and fixed a bug for get_pids_from_name function
-  Merge "Customized config file to filter reasonable tests" into
  release-v2.0
-  Revert "Add IO fault test cases"
-  Customized config file to filter reasonable tests
-  Add IO fault test cases
-  Remove some servcies from service fault tests
-  Inject OpenStack process fault by signals
-  Modified pylint checking and CI policy
-  Fix a conflict
-  Added service fault injection support and modified config file
-  Improvements for gitlab ci config file
-  Fix a community bug that won't generate sysinfo before/after test
-  Changes to README
-  Remove test from gitlab ci temporarily
-  Temporarily remove test from gitlab ci config file
-  Remove module boundaries check from build checking
-  Changes to gitlab ci config file
-  Add support for setting OpenStack environment variables
-  Delete unused config file
-  Add sudo for gitlab ci config file
-  Changes to Makefile to reflect correct package name
-  Add gitlab ci config file
-  Changes to version file and gitlab ci file
-  Fix a bug introduced during merging conflicts
-  Delete unused config file
-  Update gitreview config file
-  Add benchmarker.py for benchmarking test plugin
-  Update gitlab-ci.yml
-  Add shaker as performance test
-  Merge changes Iff8b7d84,I42e598d3 into release-v2.0
-  Merge "add workload module and stress_ng" into release-v2.0
-  Add perfkitbenchmarker test suite
-  test gitlab
-  add workload module and stress_ng
-  Add gitlab CI script
-  Add CPU fault test
-  Merge "update yamls for start_cidr" into release-v2.0
-  Change gerrit server IP for config file
-  update yamls for start_cidr
-  Merge "update performance and stability yamls" into release-v2.0
-  update performance and stability yamls
-  modify syntribos
-  Added initial openstack module for interacting with ThinkCloud.
-  Switch to use staf to dispatch test plan
-  Update stability cases
-  fix issues in vm reliability test
-  If the src-dir argument is None, get the current running path as
  src-dir
-  Merge "fix a bug in health check" into release-v2.0
-  fix a bug in health check
-  Merge "update health check test module" into release-v2.0
-  Enable pre and post job sysinfo
-  update health check test module
-  update health check and vm reliability
-  Fix some yamls bugs
-  Fix some bug and add timeout for installation.
-  Merge loaders of security and vm_reliability to ct.py
-  Merge "update installation script" into release-v2.0
-  update installation script
-  rename health check related files
-  Merge "fix issue in health check" into release-v2.0
-  Add dependencies as submodule
-  Delete dependencies
-  Port an update about install to release-v2.0 branch
-  fix issue in health check
-  Merge "Update test code issue for install plugin" into release-v2.0
-  Update test code issue for install plugin
-  Merge "Modification to ct loader for tempest test." into release-v2.0
-  Merge "add method to caculate success rate in vm reliability test" into
  release-v2.0
-  Modification to ct loader for tempest test.
-  Merge "Extend install plugin to support add, uninstall and update."
  into release-v2.0
-  Extend install plugin to support add, uninstall and update.
-  add method to caculate success rate in vm reliability test
-  Change mechanism of loading tempest tests.
-  Fix a bug in rally_test to assign err_count.
-  add rally and tempest dependencies, update install.sh
-  optimize health check and vm reliability test
-  update health check config
-  update stability
-  Update health check module to accept a dict parameter from config
  files.
-  Move strategy file as a sample one
-  Merge "modify health check plugin"
-  modify health check plugin
-  Bumped version to v2.0
-  Merge "Improvement for run test strategy script to display more human
  readable test plan log."
-  Improvement for run test strategy script to display more human readable
  test plan log.
-  Update the order of tempest configuration item
-  Merge "Add necessary configuration for tempest.conf"
-  Merge "modified syntribos"
-  Fix a bug that sometimes cannot get correct rally task id.
-  Add necessary configuration for tempest.conf
-  modified syntribos
-  Merge "add health check module"
-  add health check module
-  update some yamls
-  Modification to support ssh login with key pair
-  Add Stability test support in backend.
-  Integrate tempest smoke test to avocado
-  Fix some bugs.
-  Merge "exclude vm_reliability_test folder when list"
-  exclude vm_reliability_test folder when list
-  Add security test - bandit
-  Merge "init vm reliability tester"
-  init vm reliability tester
-  Merge "Change pre-commit to use the internal repo."
-  Change pre-commit to use the internal repo.
-  Fix a bug in health_check and move OpenStack related common parameters
  to functional.cfg.
-  Change two parameter's value for rally test: ports_per_network,
  subnets_per_network.
-  Merge "Integrated health check test support."
-  Integrated health check test support.
-  Add a parameter for rally test: size
-  Add pre-commit support and cleaned up some codes.
-  Add a parameter for rally test: floating_network and remove the network
  keypair in context from nine yamls.
-  Refactorred ct.py.
-  Add switch for copying file to remote
-  add two parameters for rally test: tenants, users_per_tenant
-  Merge "Add some parameters for running rally tests."
-  Add some parameters for running rally tests.
-  add two parameters for rally test: image_location, image_url
-  Add rally-jobs to installation procedure, also remove rally path from
  config file.
-  Merge "a) Fix rally task args yaml. b) add few pkgs to support auto
  installation."
-  a) Fix rally task args yaml. b) add few pkgs to support auto
  installation.
-  Merge changes I10aa6b70,I21b1037e
-  Use Kai's script to install tempest and avocado Add command of install
  avocado in the INSTALL_GUIDE for Kai
-  Update README in avocado-cloudtest framework for CloudTestV1.0 user
-  define four variables in all yaml files: image_name, flavor_name, times
  and concurrency 2nd
-  Merge "Remove unused python module in get_resource.py"
-  Remove unused python module in get_resource.py
-  Update copyright of ct.py
-  Merge "Improvement of analyzing rally test result"
-  Improvement of analyzing rally test result
-  support to set rally deployment
-  Imporve tempest get resource script file
-  define four variables in all yaml files: image_name, flavor_name, times
  and concurrency
-  Merge "Improvement for running rally tests."
-  Improvement for running rally tests.
-  update STAF port to 6500
-  Changing log level of sysinfo plugin
-  add some dependent pkgs
-  Merge "change log level of result analyze"
-  change log level of result analyze
-  Depress the printing of all test cases of rally
-  Improvement for rally test support
-  Merge "Improvement for rally test"
-  Improvement for rally test
-  Merge "Improvement for finding last testr result stream id for tempest"
-  Improvement for finding last testr result stream id for tempest
-  Merge "update stop method"
-  update stop method
-  update installation script
-  Merge "change kill mode to -9, and fix a bug"
-  send job report mail
-  change kill mode to -9, and fix a bug
-  Improvement for sending report email
-  Improvement for automatically send report email
-  Modified some default parameters in tests.cfg
-  Improvement for ct.py and change default job log dir
-  Merge "Change performance test variant name to rally"
-  Change performance test variant name to rally
-  add default job_results_dir, and flush stdout
-  Merge "Add two python library requirements."
-  Merge "send job result report mail automatic"
-  Add two python library requirements.
-  send job result report mail automatic
-  send job result report mail
-  add a new pkg testscenarios
-  Add STAF, update install script and delete unused dependencies.
-  Merge "send job result report mail"
-  Merge "change implement method in avocado stop function"
-  change implement method in avocado stop function
-  Improvement for tempest test to analyze result and job id generating.
-  add error handle in cfg file copy phase
-  Merge "update rally cases to 0.7.1.dev262"
-  update rally cases to 0.7.1.dev262
-  add workdir para in staf process command
-  Fix a little bug in ct.py
-  Move Rally deployment parameter from cloudtest.conf to tests.cfg.
-  Coding Standard improvement for get_resource.py
-  Coding Standard improvement for get_resource.py
-  Merge changes I7ea5c3d5,I5079e4c7
-  Merge "Add automatic installation support."
-  Coding Standard improvement for get_resource.py.
-  Refined get_resource for tempest test.
-  add exception catch
-  Merge "add tempest result process function"
-  Add support for sending results email automatically.
-  Add automatic installation support.
-  add tempest result process function
-  Merge "Add prepare resource mechanism for tempest test."
-  add --mail-to and --job-results-dir CLI arguments
-  Add prepare resource mechanism for tempest test.
-  add result parser function refine avocado-run-test-strategy file
-  Add tempest result analysis and html generation support.
-  Add support for rerun failed cases of tempest
-  Use testr with subunit to run tempest tests
-  Add support to list/run tempest via class or suite
-  Add command line arguments for tempest run type and mode
-  Merge "Add test_timeout parameter into config file for tempest"
-  Merge "Add tempest preparation script to get resource before testing"
-  Merge "Modification to version script to get correct version"
-  Add tempest preparation script to get resource before testing
-  Add test_timeout parameter into config file for tempest
-  Modification to version script to get correct version
-  Merge "Add support for running whole tempest"
-  Add support for running whole tempest
-  add function to copy tests.cfg to remote host
-  Merge "Add support to list/run suite of tempest tests"
-  Merge "Merge plugins of rally and tempest"
-  Add support to list/run suite of tempest tests
-  Merge plugins of rally and tempest
-  update run_test_strategy 1.support subcommand 2.support copy subcommand
  3.move it to scripts folder,make it be a command
-  Improvement for tempest_test plugin
-  Fix a bug in avocado/core/test.py
-  add staf and distribute module
-  Initial push to gerrit
-  Initial empty repository
