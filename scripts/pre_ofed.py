# pytest /swgwork/royno/Full/Python_work_place/pydriller/tests/test_commit.py   -s --disable-warnings -v --capture=no  --no-print-logs -k test_equa
import argparse
import datetime
import os
import re
import logging
import time

from pydriller import RepositoryMining
from pydriller import Commit
from scripts import Common

git_path=""

def parse_args():
    parser = argparse.ArgumentParser(description="OFED pre-rebase")
    # parser.add_argument("-hosts", nargs='+', type=str, required=True, help="the host to map GPU/HCA")
    parser.add_argument("-path", type=str, default="", required=True, help="path git")
    # parser.add_argument("-json_file_name", type=str, default="topo_file.json",
    #                     help="json file name to save (default='topo_file.json')")
    # parser.add_argument("-xml_file_name", type=str, default="nccl_system.xml",
    #                     help="xml file name to save (default='nccl_system.xml')")
    # parser.add_argument("-gpu", nargs='+', type=int, required=True,
    #                     help="Gpu numbers example \"-gpu 0 1 2 3 4 5 6 7\" ")
    # parser.add_argument("-hca", nargs='+', type=int, required=True,
    #                     help="Hca numbers example \"-hca 0 1 2 3 4 5 6 7\" ")
    # parser.add_argument("-server_hca", default=1, type=int,
    #                     help="choosing the server hca ")
    # parser.add_argument("-json", action='store_true', help="create a json file")
    # parser.add_argument("-xml", action='store_true', help="create a xml file (must be 8 gpu and 8 hca)")
    options = parser.parse_args()
    return options


def get_metadata_patches_info(git_repo: RepositoryMining) -> dict:
    """
    iterate over all commits in given OFED RepositoryMining,
    parsing each commit and fill data about it from metadata
    :param git_repo:
    :return:
    """
    feature_method_changed_dict = {}
    patches_info_dict = {}
    for commit in git_repo.traverse_commits():
        info = get_patch_info(commit)
        patches_info_dict[commit.hash] = info
        curr_feature = info['feature']
        # print_data(commit, patches_info_dict)
        for mod in commit.modifications:
            if len(mod.changed_methods) > 0:
                for method in mod.changed_methods:
                    if curr_feature in feature_method_changed_dict.keys():
                        feature_method_changed_dict[curr_feature].append(method.name)
                    else:
                        feature_method_changed_dict[curr_feature] = []
                        feature_method_changed_dict[curr_feature].append(method.name)
        # feature_method_changed_dict[info['feature']] =
        # list(dict.fromkeys(feature_method_changed_dict[info['feature']])) #remove duplicates
    return patches_info_dict, feature_method_changed_dict


def print_data(commit, patches_info_dict):
    print(patches_info_dict[commit.hash]['feature'])
    print()
    print('Hash {}, author {}'.format(commit.hash, commit.author.name))
    for mod in commit.modifications:
        if len(mod.changed_methods) == 0:
            continue
        print_filename(mod)
        [print(meth.name) for meth in mod.changed_methods]


def print_filename(mod):
    filename = f'in file: {mod.filename}'
    print('-' * len(filename))
    print(filename)
    print('-' * len(filename))


def get_patch_changeID(commit: Commit):
    """
    parse OFED commit unique change-id
    :param commit: Commit
    :return: change-id: str
    """
    msg = commit.msg
    try:
        list_data = re.findall(r"\s*Change-Id:\s+(\w+)", msg, re.M)
        return list_data[0]
    except Exception as e:
        print(f"Fail get_patch_changeID in {commit.hash}: {e}")
        return None


def generate_author_file(author: str) -> str:
    """
    get comit author name and return the author metadata file
    :param author: str
    :return: filename: str
    """
    splited = author.split(' ')
    string_builder = ""
    for name in splited:
        string_builder += f"_{name}"
    filename = f"{string_builder}.csv"
    return filename[1:]


def get_line_from_csv(author_file, change_id):
    """
    return line from metadata matching change_id and author
    :param author_file: str
    :param change_id: str
    :return: line: str
    """
    with open(author_file, "r") as handle:
        csv = handle.read()
        try:
            list_lines = re.findall(rf".*{change_id}.*", csv, re.M)
            return list_lines[0]
        except Exception as e:
            print(f"Fail get_line_from_csv for file {author_file}, changeID {change_id}: {e}")
            return None


def get_patch_info(commit: Commit) -> dict:
    """
    parse OFED patch info from metadata
    :param commit: Commit
    :return: patch_info: dict
    """
    global git_path
    change_id = get_patch_changeID(commit)
    author_file = f"{git_path}/metadata/{generate_author_file(commit.author.name)}"
    if not os.path.isfile(author_file):
        print(f"File {author_file} not exist, please check commit {commit.hash} manually")
    line_for_changeID = get_line_from_csv(author_file, change_id)
    patch_info_dict = Common.parse_patch_info(line_for_changeID)[1]
    return patch_info_dict


def show_objects_changed_by_features(objects_changed_by_features: dict):
    """
    print all information script analyzed about which functions each OFED feature changing
    :param objects_changed_by_features:
    :return:
    """
    title = "show_feature_functions"
    print(title)
    print('='*len(title))
    for key in objects_changed_by_features:
        print()
        print()
        print(f"Feature '{key}':")
        [print(x) for x in objects_changed_by_features[key]]


def main():
    global git_path

    start_time = time.time()
    args = parse_args()
    # print(args)
    git_path = args.path
    if git_path.endswith('/'):
        git_path = git_path[:-1]  # remove last '/' if exist
    if not os.path.isdir(git_path):
        print(f'Path {args.path} is not a directory')
        exit(1)
    curr_path = '/swgwork/royno/OFED_WORK_AREA/mlnx_ofed_5_2/mlnx-ofa_kernel-4.0'
    # git_repo = RepositoryMining(curr_path, from_tag='vmlnx-ofed-5.2-0.6.3')
    git_repo = RepositoryMining(git_path)
    metadata_commit_info, objects_changed_by_features = get_metadata_patches_info(git_repo)
    end_time = time.time()

    show_objects_changed_by_features(objects_changed_by_features)
    show_runtime(end_time, start_time)


def show_runtime(end_time, start_time):
    runtime = end_time - start_time
    msg = f"Script run time:  {str(datetime.timedelta(seconds=runtime//1))}"
    print('-' * len(msg))
    print(msg)
    print('-' * len(msg))


if __name__ == '__main__':
    main()
