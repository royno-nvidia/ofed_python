#!/bin/bash

# this script will install modules required for scripts run
sys_py_ver="$(ls  /usr/bin/  | grep -oE "python[0-9]\.*[0-9]*" | sort -r | uniq |head -1)"
DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")")

sudo /usr/bin/${sys_py_ver} -m  pip install pydriller==2.0
sudo /usr/bin/${sys_py_ver} -m  pip install pandas
sudo /usr/bin/${sys_py_ver} -m  pip install xlsxwriter
sudo /usr/bin/${sys_py_ver} -m  pip install colorlog

echo "---------------------------------------------"
echo "Dependency modules install over ${sys_py_ver}"
echo "---------------------------------------------"
echo "Please run [Enable run from command line]:"
echo "'export PYTHONPATH="\${PYTHONPATH}:${DIR}"'"
