import json
import os
import subprocess
from collections import Counter
import pandas as pd

from utils.setting_utils import show_runtime, save_to_json
import argparse
import time
import re

GREP_DEF_CMD = 'git grep -w --color=never {} | grep -v backports'


def parse_args():
    parser = argparse.ArgumentParser(description="OFED post-rebase script\n"
                                                 "Compare and alert functions")
    parser.add_argument("-ofed-repo", type=str, default=None, required=True,
                        help="Path for last OFED repo")
    parser.add_argument("-rebase-repo", type=str, default=None, required=True,
                        help="Path for current rebase repo")
    # parser.add_argument("-output", type=str, default=None, required=True,
    #                     help="Result Excel name")
    options = parser.parse_args()
    return options


def get_defines_from_file(file):
    pattern = 'HAVE.*_[A-Z0-9]+'

    try:
        with open(file, 'r') as handle:
            def_set = set(re.findall(pattern, handle.read()))
            return def_set
    except Exception as e:
        print(f"Fail to open {file}: {e}")
        exit(1)


def run_shell_cmd_and_get_output(cmd):
    try:
        return subprocess.check_output(cmd, shell=True).decode("utf-8")
    except Exception as e:
        print(f"Failed execute: '{cmd}'")
        return ""


def filter_list_using_regex(list, regex):
    return [i for i in list
            if not regex.match(i) and i]  # throw away all noted use and empty lines

def get_file_names_only(grep_list):
    return [re.split(':', i)[0] for i in grep_list]

def get_defines_stats(defines_set, dir_path):
    define_dict = {}
    regex = re.compile(".*/\*.*\*/.*")  # search note
    os.chdir(dir_path)
    print(f'inside {dir_path}')
    for define in defines_set:
        ret = run_shell_cmd_and_get_output(GREP_DEF_CMD.format(define))
        filtered_list = filter_list_using_regex(ret.splitlines(), regex)
        splited = get_file_names_only(filtered_list)
        define_dict[define] = Counter(splited)
    print(define_dict)
    return define_dict


def is_backports_applied(repo):
    if not os.path.isfile(f'{repo}/backports_applied'):
        print(f'-E- Backports are missing in {repo}')
        return False
    return True


def find_difs_in_counters(ofed_counters, rebase_counters):
    difs_dict = {}
    for define in ofed_counters.keys():
        difs_dict[define] = Counter({key: rebase_counters[define].get(key, 0) - value for key, value in ofed_counters[define].items()})
    return difs_dict

def remove_empty_counters(counters):
    non_zero = {}
    for define, counter in counters.items():
        corrent = dict()
        for file, count in counter.items():
            if count != 0:
                    corrent[file] = count
        if corrent:
            non_zero[define] = corrent
    return non_zero

def json_to_dict(my_json):
    return json.loads(my_json)

def export_to_excel(df, path):
    df.to_excel(path, index=False)
    print(f'Results saved in: {path}')

def create_list_for_dataframe(results_json):
    results_dict = json_to_dict(results_json)
    list = []
    for define, files in results_dict.items():
        for file, count in files.items():
            list.append({
                "Define name": define,
                "File": file,
                "Count": count
            })
    return list


def create_excel_for_review(results_list):
    df = pd.DataFrame(results_list)
    export_to_excel(df, '/swgwork/royno/Full/backports_review.xlsx')

def main():
    args = parse_args()
    defines_set = set()
    files = ['compat/config/rdma.m4', 'compat/configure.ac']

    if not is_backports_applied(args.ofed_repo) or not is_backports_applied(args.rebase_repo):
        print('Aborting')
        exit(1)

    for file in files:
        defines_set |= get_defines_from_file(f'{args.ofed_repo}/{file}')
    print(f'len = {len(defines_set)} | {defines_set}')
    ofed_defs_counters = get_defines_stats(defines_set, args.ofed_repo)
    rebase_defs_counters = get_defines_stats(defines_set, args.rebase_repo)
    difs_dict = find_difs_in_counters(ofed_defs_counters, rebase_defs_counters)
    results_dict = remove_empty_counters(difs_dict)
    print(f'{json.dumps(results_dict, indent=4)}')
    print(f'Found {len(results_dict.keys())} problematic defines')
    # save_to_json(results_dict, 'backports_reviewer')
    results_list_for_df = create_list_for_dataframe(json.dumps(results_dict, indent=4))
    create_excel_for_review(results_list_for_df)



if __name__ == '__main__':
    main()
