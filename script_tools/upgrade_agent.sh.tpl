typeset -l OS_INFO
OS_INFO=""
OS_TYPE=""
RC_LOCAL_FILE=/etc/rc.d/rc.local

get_cpu_arch () {{
    local cmd=$1
    CPU_ARCH=$($cmd)
    CPU_ARCH=$(echo $CPU_ARCH | tr 'A-Z' 'a-z')
    # compatible ksh regex syntax, watch out bash syntax
    if echo "$CPU_ARCH" | egrep -q "x86_64"; then
        return 0
    elif $(echo "$CPU_ARCH" | egrep -q "x86") || $(echo "$CPU_ARCH" | egrep -q '^i[3456]86'); then
        CPU_ARCH="x86"
        return 0
    elif echo "$CPU_ARCH" | egrep -q "aarch"; then
        return 0
    elif echo "$CPU_ARCH" | egrep -q "powerpc"; then
        return 0
    else
        return 1
    fi
}}

get_cpu_arch "uname -p" || get_cpu_arch "uname -m" || get_cpu_arch "arch" || echo "Failed to get CPU arch, please contact the developer."

get_os_info () {{
    if [ -f "/proc/version" ]; then
        OS_INFO="$OS_INFO $(cat /proc/version)"
    fi
    if [ -f "/etc/issue" ]; then
        OS_INFO="$OS_INFO $(cat /etc/issue)"
    fi
    OS_INFO="$OS_INFO $(uname -a)"
}}

get_os_type () {{
    get_os_info
    if [[ "$OS_INFO" == *ubuntu* ]]; then
        OS_TYPE="ubuntu"
        RC_LOCAL_FILE="/etc/rc.local"
    elif [[ "$OS_INFO" == *centos* ]]; then
        OS_TYPE="centos"
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    elif [[ "$OS_INFO" == *tlinux* ]]; then
        OS_TYPE="tlinux"
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    elif [[ "$OS_INFO" == *coreos* ]]; then
        OS_TYPE="coreos"
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    elif [[ "$OS_INFO" == *freebsd* ]]; then
        OS_TYPE="freebsd"
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    elif [[ "$OS_INFO" == *debian* ]]; then
        OS_TYPE="debian"
        RC_LOCAL_FILE="/etc/rc.local"
    elif [[ "$OS_INFO" == *suse* ]]; then
        OS_TYPE="suse"
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    elif [[ "$OS_INFO" == *hat* ]]; then
        OS_TYPE="redhat"
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    elif [[ "$OS_INFO" == *aix* ]]; then
        OS_TYPE="aix"
        RC_LOCAL_FILE="/etc/inittab"
    else
        OS_TYPE="centos"
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    fi
}}

check_rc_file () {{
    get_os_type
    if [ -f $RC_LOCAL_FILE ]; then
        return 0
    elif [ -f "/etc/rc.d/rc.local" ]; then
        RC_LOCAL_FILE="/etc/rc.d/rc.local"
    else
        RC_LOCAL_FILE="/etc/rc.local"
    fi
}}

setup_startup_scripts () {{
    check_rc_file
    local rcfile=$RC_LOCAL_FILE

    if [ $OS_TYPE == "ubuntu" ]; then
        sed -i "\|\#\!/bin/bash|d" $rcfile
        sed -i "1i \#\!/bin/bash" $rcfile
    fi

    if [ $OS_TYPE == "aix" ]; then
        mkitab "gse_agent:2:once:{setup_path}/{node_type}/bin/gsectl start >/var/log/gse_start.log 2>&1"
    else
        chmod +x $rcfile
        # 先删后加，避免重复!/
        sed -i "\|{setup_path}/{node_type}/bin/gsectl|d" $rcfile
        echo "[ -f {setup_path}/{node_type}/bin/gsectl ] && {setup_path}/{node_type}/bin/gsectl start >/var/log/gse_start.log 2>&1" >>$rcfile
    fi
}}

remove_crontab () {{
    if [ $OS_TYPE == "aix" ]; then
        local datatemp=$(date +%s)
        crontab -l | grep -v "{setup_path}/{node_type}/bin/gsectl" > /tmp/cron.$datatemp
        crontab /tmp/cron.$datatemp && rm -f /tmp/cron.$datatemp

        # 下面这段代码是为了确保修改的crontab能立即生效
        ps -eo pid,comm | grep cron |awk '{{print$1}}' | xargs kill -9
    else
        local tmpcron
        tmpcron=$(mktemp "$TMP_DIR"/cron.XXXXXXX)

        crontab -l | grep -v "{setup_path}/{node_type}/bin/gsectl"  >"$tmpcron"
        crontab "$tmpcron" && rm -f "$tmpcron"

        # 下面这段代码是为了确保修改的crontab能立即生效
        if pgrep -x crond &>/dev/null; then
            pkill -HUP -x crond
        fi
    fi
}}

if [ {pkg_cpu_arch} == $CPU_ARCH ]; then
        echo "cpu arch check is ok"
else
        echo "Package cpu arch is {pkg_cpu_arch} but os exact cpu arch is $CPU_ARCH, not match!"
        echo "Please check/modify cpu arch in cmdb/nodeman"
        exit 1
fi

{process_pull_configuration_cmd}

cd "{setup_path}"
for file in `lsattr -R |egrep "i-" |awk "{{print $NF}}"`;do echo "--- $file" && chattr -i $file ;done
tar xf "{temp_path}/{package_name}" || echo "tar xf {temp_path}/{package_name} failed"
{reload_cmd}
