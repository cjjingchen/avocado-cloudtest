#!/bin/bash

set -e
PROG=$(basename "${0}")
BASEDIR=`pwd`

STAF_PORT=6500

# ansi colors for formatting heredoc
ESC=$(printf "\e")
GREEN="$ESC[0;32m"
NO_COLOR="$ESC[0;0m"
RED="$ESC[0;31m"

## Exit status codes (mostly following <sysexits.h>)
# successful exit
EX_OK=0
# wrong command-line invocation
EX_USAGE=64

# Define some default value
MODULE=""
OPERATION=""
ROLE=""
DEBUG="nodebug"

# Define NFS default value
NFS_IP_STR="10.100.109.58"
NFS_URL_STR_SLAVE="${NFS_IP_STR}:/share/cloudtest_job_results"
NFS_URL_STR_MASTER="${NFS_IP_STR}:/share/cloudtest_job_results"
NFS_MOUNT_POINT_SLAVE='/cloudtest_results'
NFS_MOUNT_POINT_MASTER='/cloudtest_results'
FSTAB_FILE="/etc/fstab"
NFS_MOUNT_INFO="10.100.109.58:/share/cloudtest_job_results /cloudtest_results nfs4 defaults"
BASHRC_FILE="/etc/bashrc"
CLOUDTEST_SOURCEDIR="CLOUDTEST_SOURCEDIR"

# Define GIT url
GIT_URL="http://gerrit.lenovo.com/cloud/"

# Functions set here
print_usage () {
	cat <<__EOF__
Usage: $PROG [options]

This script will install avocado-cloudtest, Rally, Tempest, health_check, STAF etc in your system.

Options:
$GREEN  -h, --help                $NO_COLOR Print this help text.
$GREEN  -m, --module MODULE       $NO_COLOR Select a module to install, 
                                            MODULE can be 'avocado', 'rally', 'tempest','syntribos', 'staf', 'all'.
                                            Default: avocado
$GREEN  -r, --role ROLE           $NO_COLOR Select the host role want to be, 
                                            ROLE can be 'master', 'slave'.
                                            Default: master
$GREEN  -o, --operation OPERATION $NO_COLOR Select a operation want to do,
                                            OPEARTION can be 'install', 'update'.
                                            Default: install
$GREEN  --no-color              $NO_COLOR Disable output coloring.
$GREEN  --debug, --nodebug      $NO_COLOR Turn debug model on or off. When it works in debug model, it will give more detail info.

__EOF__
}
# abort RC [MSG]
#
# Print error message MSG and abort shell execution with exit code RC.
# If MSG is not given, read it from STDIN.
#
abort () {
  local rc="$1"
  shift
  (echo -en "$RED$PROG: ERROR: $NO_COLOR";
      if [ $# -gt 0 ]; then echo "$@"; else cat; fi) 1>&2
  exit "$rc"
}

# die RC HEADER <<...
#
# Print an error message with the given header, then abort shell
# execution with exit code RC.  Additional text for the error message
# *must* be passed on STDIN.
#
die () {
  local rc="$1"
  header="$2"
  shift 2
  cat 1>&2 <<__EOF__
$RED==========================================================
$PROG: ERROR: $header
==========================================================
$NO_COLOR
__EOF__
  if [ $# -gt 0 ]; then
	  # print remaining arguments one per line
	  for line in "$@"; do
		  echo "$line" 1>&2;
	  done
  else
	  # additional message text provided on STDIN
	  cat 1>&2;
  fi
  cat 1>&2 <<__EOF__

If the above does not help you resolve the issue, 
please contact by sending an email to pangkai1@lenovo.com 
Include the full output of this script to help us identifying the problem.
$RED
Aborting installation!$NO_COLOR
__EOF__
  exit "$rc"
}

function progressbar () 
{
    SECONDS=1
    STR=$1
    rm -rf done > /dev/null 2>&1
    while [ true ]
    do
        echo -n -e "\r${STR}--"
        sleep ${SECONDS}
        echo -n -e "\r${STR}\\ "
        sleep ${SECONDS}
        echo -n -e "\r${STR}| "
        sleep ${SECONDS}
        echo -n -e "\r${STR}/ "
        sleep ${SECONDS}
        if [ -f done ]
        then
            echo -e "\r${STR}Done "
            break
        fi
    done
}
function pre_NFS_slave()
{
	echo "Prepare the NFS for slave..."
	COUNT_RESULT=`mount | grep ${NFS_IP_STR} | wc -l`
	if [ ${COUNT_RESULT} == 0 ]
	then
		mkdir -p ${NFS_MOUNT_POINT_SLAVE} > /dev/null 2>&1 || true
		mount ${NFS_URL_STR_SLAVE} ${NFS_MOUNT_POINT_SLAVE}
		echo "Mount NFS successfully."
	else
		echo "NFS is already ready."
	fi
}
function pre_NFS_master()
{
	echo "Prepare the NFS master..."
	COUNT_RESULT=`mount | grep ${NFS_IP_STR} | wc -l`
	if [ ${COUNT_RESULT} == 0 ]
	then
		mkdir -p ${NFS_MOUNT_POINT_MASTER} > /dev/null 2>&1 || true
		mount ${NFS_URL_STR_MASTER} ${NFS_MOUNT_POINT_MASTER}
		echo "Mount NFS successfully."
	else
		echo "NFS is already ready."
	fi
}
function pre_NFS()
{
	_role=$1
	if [ "${_role}x" == "slavex" ]
	then
		pre_NFS_slave
        add_auto_mount_NFS
	fi
	if [ "${_role}x" == "masterx" ]
	then
		pre_NFS_master
        add_auto_mount_NFS
	fi
}
function add_auto_mount_NFS()
{
    _need_add=`grep -r "${NFS_MOUNT_INFO}" ${FSTAB_FILE} | wc -l`
    if [ ${_need_add} -eq 0 ]
    then
        echo ${NFS_MOUNT_INFO} >> ${FSTAB_FILE}
    fi
}
function add_env()
{
    _need_add=`grep -r "${CLOUDTEST_SOURCEDIR}" ${BASHRC_FILE} | wc -l`
    if [ ${_need_add} -eq 0 ]
    then
        echo export ${CLOUDTEST_SOURCEDIR}=${BASEDIR} >> ${BASHRC_FILE}
    fi
}

function get_dependencies()
{
    DEPENDENCIES_DIR=dependencies
    mkdir ${DEPENDENCIES_DIR} > /dev/null 2>&1 || true 
    if [ -d ${DEPENDENCIES_DIR} ]
    then
        _howmany=`ls ${DEPENDENCIES_DIR} | wc -l`
        if [ ${_howmany} -eq 0 ]
        then
            echo git clone ${GIT_URL}/cloudtest-dependencies ${DEPENDENCIES_DIR}
            git clone ${GIT_URL}/cloudtest-dependencies ${DEPENDENCIES_DIR}
        fi
    fi
}

function install_rally()
{
	RALLY_SRC_DIR=cloudtest/tests/performance/rally/rally
	RALLY_GIT_URL=${GIT_URL}/rally
	rm -rf ${RALLY_SRC_DIR}
	mkdir -p ${RALLY_SRC_DIR}
	git clone ${RALLY_GIT_URL} ${RALLY_SRC_DIR}
	rm -rf dependencies/Rally/rally
	cp -r  cloudtest/tests/performance/rally/rally dependencies/Rally/
	cd dependencies/Rally/
	./install_rally.sh "--$1"
	cd -
}

function install_tempest()
{
	TEMPEST_SRC_DIR=dependencies/Tempest/tempest/
	TEMPEST_GIT_DIR=${GIT_URL}/tempest
	rm -rf ${TEMPEST_SRC_DIR}
	git clone ${TEMPEST_GIT_DIR} ${TEMPEST_SRC_DIR}
	cd ${TEMPEST_SRC_DIR}/..
	./install_tempest.sh "--$1"
	cd -
}

function install_syntribos()
{
        SYNTRIBOS_SRC_DIR=cloudtest/tests/security/syntribos
        cd ${SYNTRIBOS_SRC_DIR}
        python setup.py install
        cd -
}

function install_staf()
{
	DEPENDENCIES_DIR=dependencies/STAF
	cd ${DEPENDENCIES_DIR}
	./install_staf.sh -o install -p ${STAF_PORT}
	cd -
}
function uninstall_staf()
{
	DEPENDENCIES_DIR=dependencies/STAF
	cd ${DEPENDENCIES_DIR}
	./install_staf.sh -o uninstall
	cd -
}


function install_git()
{
	TIMESTAMP=`date "+%Y%m%d_%H%M%S"`
	DEPENDENCIES_DIR=dependencies/Avocado
	cd ${DEPENDENCIES_DIR}
	mkdir log >/dev/null 2>&1 || true
	echo "Installing git packages ..."
	./git.dependencies.install $1 $TIMESTAMP
	cd -
}
function install_avocado()
{
	workdir=$PWD
	TIMESTAMP=`date "+%Y%m%d_%H%M%S"`
	LOGFILE_SYS=log/sys.dependencies.${TIMESTAMP}.log
	LOGFILE_DEP=log/avocado.dependencies.${TIMESTAMP}.log
	LOGFILE_SET=dependencies/Avocado/log/avocado.setup.${TIMESTAMP}.log
	cd dependencies/Avocado/
	mkdir log >/dev/null 2>&1 || true
	echo "Installing system packages for Avocado ... "
	./sys.dependencies.install $1 $TIMESTAMP	
	if [ "${1}x" == "debugx" ]
	then
		echo "Installing dependencies for Avocado ... "
		./avocado.dependencies.install $workdir 2>&1 | tee ${LOGFILE_DEP}
		cd -
		echo "Installing Avocado ... "
		python setup.py install 2>&1 | tee ${LOGFILE_SET}
	else
		./avocado.dependencies.install $workdir > ${LOGFILE_DEP} 2>&1 &
		progressbar "Installing dependencies for Avocado ... "
		rm -rf done
		cd -
		echo "Installing Avocado ... "
		python setup.py install > ${LOGFILE_SET} 2>&1 
	fi
}
function update_avocado()
{
	TIMESTAMP=`date "+%Y%m%d_%H%M%S"`
	LOGFILE_SET=dependencies/Avocado/log/avocado.setup.${TIMESTAMP}.log
	mkdir -p dependencies/Avocado/log >/dev/null 2>&1 || true
	if [ "${1}x" == "debugx" ]
	then
		echo "Installing Avocado ... "
		python setup.py install 2>&1 | tee ${LOGFILE_SET}
	else
		echo "Installing Avocado ... "
		python setup.py install > ${LOGFILE_SET} 2>&1 
	fi
}
function uninstall_avocado()
{
    make clean
    yes | pip uninstall -r requirements.txt
    yes | pip uninstall  avocado-cloudtest
}

function do_staf()
{
    _ROLE=$1
    _OPERATION=$2
    _DEBUG=$3
    if [ "${_OPERATION}x" == "installx" ]
    then
		pre_NFS ${_ROLE}
        get_dependencies
        add_env
        install_staf ${_DEBUG}
    else
        if [ "${_OPERATION}x" == "uninstallx" ]
        then
            get_dependencies
            uninstall_staf ${_DEBUG}
        fi
    fi
}
function do_rally()
{
    _ROLE=$1
    _OPERATION=$2
    _DEBUG=$3
    if [ "${_OPERATION}x" == "installx" ]
    then
		pre_NFS $ROLE
        get_dependencies
        add_env
		install_git ${DEBUG}
        install_rally ${_DEBUG}
    fi
}
function do_syntribos()
{
    _ROLE=$1
    _OPERATION=$2
    _DEBUG=$3
    if [ "${_OPERATION}x" == "installx" ]
    then
                pre_NFS $ROLE
        install_syntribos ${_DEBUG}
    fi
}
function do_tempest()
{
    _ROLE=$1
    _OPERATION=$2
    _DEBUG=$3
    if [ "${_OPERATION}x" == "installx" ]
    then
		pre_NFS $ROLE
        get_dependencies
        add_env
		install_git ${DEBUG}
        install_tempest ${_DEBUG}
    fi
}
function do_avocado()
{
    _ROLE=$1
    _OPERATION=$2
    _DEBUG=$3
    if [ "${_OPERATION}x" == "installx" ]
    then
		pre_NFS $ROLE
        get_dependencies
        add_env
        install_avocado ${_DEBUG}
    else
        if [ "${_OPERATION}x" == "updatex" ]
        then
            get_dependencies
            update_avocado ${_DEBUG}
        else
            if [ "${_OPERATION}x" == "uninstallx" ]
            then
                uninstall_avocado ${_DEBUG}
            fi
        fi
    fi
}
### Main program ###
short_opts='m:,h,r:,o:'
long_opts='module:,help,role:,operation:,no-color,debug,nodebug'

set +e
if [ "x$(getopt -T)" = 'x' ]; then
	# GNU getopt
	args=$(getopt --name "$PROG" --shell sh -l "$long_opts" -o "$short_opts" -- "$@")
	if [ $? -ne 0 ]; then
		abort 1 "Type '$PROG --help' to get usage information."
	fi
	# use 'eval' to remove getopt quoting
	eval set -- "$args"
else
	# old-style getopt, use compatibility syntax
	args=$(getopt "$short_opts" "$@")
	if [ $? -ne 0 ]; then
		abort 1 "Type '$PROG -h' to get usage information."
	fi
	eval set -- "$args"
fi
set -e
#echo args:$args
# Command line parsing
while true
do
	case "$1" in
		-o|--operation)
			shift
			OPERATION=$1
			#VENVDIR=$(readlink -m "$1")
            case $OPERATION in
                install|update|uninstall);;
                *)
                    print_usage | die $EX_USAGE \
                        "An invalid option has been detected."
                    ;;
            esac
			;;
		-m|--module)
			shift
			MODULE=$1
			#VENVDIR=$(readlink -m "$1")
            case $MODULE in
                avocado|rally|tempest|syntribos|staf|all);;
                *)
                    print_usage | die $EX_USAGE \
                        "An invalid option has been detected."
                    ;;
            esac
			;;
		-h|--help)
			print_usage
			exit $EX_OK
			;;
		-r|--role)
			shift
			ROLE=$1
            case $ROLE in
                master|slave|openstack);;
                *)
                    print_usage | die $EX_USAGE \
                        "An invalid option has been detected."
                    ;;
            esac
			;;
		--no-color)
			RED=""
			GREEN=""
			NO_COLOR=""
			;;
		--debug)
			DEBUG="debug"
			;;
		--nodebug)
			DEBUG="nodebug"
			;;
		--)
			shift
			break
			;;
		*)
			print_usage | die $EX_USAGE "An invalid option has been detected."
	esac
	shift
done

if [ "${OPERATION}x" == "x" ]
then
    abort 1  "Miss to specify the operation"
fi

if [ "${ROLE}x" == "masterx" ] 
then
	case "${MODULE}x" in
		stafx)
			echo To ${OPERATION} ${MODULE} ...
			do_staf ${ROLE} ${OPERATION} ${DEBUG}
			;;
		avocadox)	
			echo To ${OPERATION} ${MODULE} ...
			do_avocado ${ROLE} ${OPERATION} ${DEBUG}
			;;
		allx)
			echo To ${OPERATION} all Modules ...
			echo "(1/2) To ${OPERATION} STAF ..."
			do_staf ${ROLE} ${OPERATION} ${DEBUG}
			echo "(2/2) To ${OPERATION} Avocado-cloudtest ..."
			do_avocado ${ROLE} ${OPERATION} ${DEBUG}
			;;
		*)
            abort 1 "Please to specify the modules, they can be avocado, staf or all."
            
	esac
else if [ "${ROLE}x" == "openstackx" ] 
	then
		case "${MODULE}x" in
			stafx)
				echo To ${OPERATION} ${MODULE} ...
				do_staf ${ROLE} ${OPERATION} ${DEBUG}
				;;
			avocadox)	
				echo To ${OPERATION} ${MODULE} ...
				do_avocado ${ROLE} ${OPERATION} ${DEBUG}
				;;
			allx)
				echo To ${OPERATION} all Modules ...
				echo "(1/2) To ${OPERATION} STAF ..."
				do_staf ${ROLE} ${OPERATION} ${DEBUG}
				echo "(2/2) To ${OPERATION} Avocado-cloudtest ..."
				do_avocado ${ROLE} ${OPERATION} ${DEBUG}
				;;
			*)
                abort 1 "Please to specify the modules, they can be avocado, staf or all."
		esac
	else if [ "${ROLE}x" == "slavex" ] 
	    then
			case "${MODULE}x" in
				rallyx)
					echo To ${OPERATION} ${MODULE} ...
					do_rally ${ROLE} ${OPERATION} ${DEBUG}
					;;
				tempestx)
					echo To ${OPERATION} ${MODULE} ...
					do_tempest ${ROLE} ${OPERATION} ${DEBUG}
					;;
                                syntribosx)
                                        echo To ${OPERATION} ${MODULE} ...
                                        do_syntribos ${ROLE} ${OPERATION} ${DEBUG}
                                        ;;
				stafx)
					echo To ${OPERATION} ${MODULE} ...
					do_staf ${ROLE} ${OPERATION} ${DEBUG}
					;;
				avocadox)	
					echo To ${OPERATION} ${MODULE} ...
					do_avocado ${ROLE} ${OPERATION} ${DEBUG}
					;;
				allx)
					echo To ${OPERATION} all Modules ...
					echo "(1/5) To ${OPERATION} Rally ..."
					do_rally ${ROLE} ${OPERATION} ${DEBUG}
					echo "(2/5) To ${OPERATION} STAF ..."
					do_staf ${ROLE} ${OPERATION} ${DEBUG}
					echo "(3/5) To ${OPERATION} Tempest ..."
					do_tempest ${ROLE} ${OPERATION} ${DEBUG}
                                        echo "(4/5) To ${OPERATION} Syntribos ..."
                                        do_syntribos ${ROLE} ${OPERATION} ${DEBUG}
					echo "(5/5) To ${OPERATION} Avocado-cloudtest ..."
					do_avocado ${ROLE} ${OPERATION} ${DEBUG}
					;;
				*)
                    abort 1  "Please to specify the modules, they can be avocado, staf, rally, tempest or all."
			esac
        else
            abort 1  "Miss to specify the role."
	    fi
    fi
fi

