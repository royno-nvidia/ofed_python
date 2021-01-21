# pytest /swgwork/royno/Full/Python_work_place/pydriller/tests/test_commit.py   -s --disable-warnings -v --capture=no  --no-print-logs -k test_equa
import argparse
import datetime
import os
import re
import logging
import time

import json
import git
from colorlog import ColoredFormatter
from pydriller import RepositoryMining
from pydriller import Commit
from scripts.utils import Common

git_path = ""
is_ofed = False
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
s_formatter = ColoredFormatter('%(log_color)s%(asctime)s[%(filename)s +%(lineno)s] - %(levelname)s - %(message)s%(reset)s')
f_formatter = logging.Formatter('%(asctime)s[%(filename)s +%(lineno)s] - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('analyzer.log')
file_handler.setFormatter(f_formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(s_formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def logger_legend():
    logger.debug("A quirky message only developers care about")
    logger.info("Curious users might want to know this")
    logger.warn("Something is wrong and any user should be informed")
    logger.error("Serious stuff, this is red for a reason")
    logger.critical("OH NO everything is on fire")


def parse_args():
    parser = argparse.ArgumentParser(description="OFED pre-rebase")
    # parser.add_argument("-hosts", nargs='+', type=str, required=True, help="the host to map GPU/HCA")
    parser.add_argument("-path", type=str, default="", required=True, help="Git path")
    parser.add_argument("-start_tag", type=str, default="",
                        help="Script will process only commits from tag and above [must be valid tag in -path repo]")
    parser.add_argument("-end_tag", type=str, default="",
                        help="Script will process only commits up to tag [must be valid tag in -path repo]")
    parser.add_argument("-ofed_repo", action='store_true',
                        help="Script will analyze git repo as OFED repo")
    # parser.add_argument("-hca", nargs='+', type=int, required=True,
    #                     help="Hca numbers example \"-hca 0 1 2 3 4 5 6 7\" ")
    # parser.add_argument("-server_hca", default=1, type=int,
    #                     help="choosing the server hca ")
    # parser.add_argument("-json", action='store_true', help="create a json file")
    # parser.add_argument("-xml", action='store_true', help="create a xml file (must be 8 gpu and 8 hca)")
    options = parser.parse_args()
    return options


def is_git_repo(path: str) -> bool:
    """
    determine whether path is git repo root
    :param path:
    :return: bool
    """
    try:
        _ = git.Repo(path).git_dir
        return True
    except git.exc.InvalidGitRepositoryError:
        return False


def process_kernel_repo(git_repo: RepositoryMining) -> list:
    """

    :param git_repo:
    :return:
    """
    # info_dict = {}
    changed_methods = []
    overall_commits = 0
    for commit in git_repo.traverse_commits():
        overall_commits += 1
        for mod in commit.modifications:
            if len(mod.changed_methods) > 0:
                for method in mod.changed_methods:
                    changed_methods.append(method.name)
    logger.info(f"over all commits parsed: {overall_commits}")
    return list(dict.fromkeys(changed_methods))


def process_ofed_repo(git_repo: RepositoryMining) -> dict:
    """
    iterate over all commits in given OFED RepositoryMining,
    parsing each commit and fill data about it from metadata
    :param git_repo:
    :return:
    """
    feature_method_changed_dict = {}
    patches_info_dict = {}
    overall_commits = 0
    for commit in git_repo.traverse_commits():
        overall_commits += 1
        info = get_patch_info(commit)
        if info is None:
            logger.error(f"Fail to process commit {commit.hash}")
            continue
        patches_info_dict[commit.hash] = info
        curr_feature = info['feature']
        print_data(commit, patches_info_dict)
        for mod in commit.modifications:
            if len(mod.changed_methods) > 0:
                for method in mod.changed_methods:
                    if curr_feature in feature_method_changed_dict.keys():
                        feature_method_changed_dict[curr_feature].append(method.name)
                    else:
                        feature_method_changed_dict[curr_feature] = []
                        feature_method_changed_dict[curr_feature].append(method.name)
    logger.info(f"over all commits parsed: {overall_commits}")
    return patches_info_dict, feature_method_changed_dict


def print_data(commit, patches_info_dict):
    logger.debug("")
    logger.debug('Hash {}, author {}, feature {}'.format(commit.hash, commit.author.name, patches_info_dict[commit.hash]['feature']))
    for mod in commit.modifications:
        if len(mod.changed_methods) == 0:
            continue
        print_filename(mod)
        [logger.debug(f"\t{meth.name}") for meth in mod.changed_methods]


def print_filename(mod):
    filename = f'in file: {mod.filename}'
    logger.debug(filename)


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
        logger.exception(f"Fail get_patch_changeID in {commit.hash}: {e}")
        return None


def generate_author_file(author: str) -> str:
    """
    get commit author name and return the author metadata file
    :param author: str
    :return: filename: str
    """
    return f"{author.replace(' ', '_')}.csv"


def get_line_from_csv(author_file, change_id):
    """
    return line from metadata matching change_id and author
    :param author_file: str
    :param change_id: str
    :return: line: str
    """
    try:
        with open(author_file, "r") as handle:
            csv = handle.read()
            list_lines = re.findall(rf".*{change_id}.*", csv, re.M)
            return list_lines[0]
    except Exception as e:
        logger.exception(f"Fail get_line_from_csv for file {author_file}, changeID {change_id}: {e}")
        return None


def get_patch_info(commit: Commit) -> dict:
    """
    parse OFED patch info from metadata
    :param commit: Commit
    :return: patch_info: dict
    """
    global git_path
    change_id = get_patch_changeID(commit)
    if change_id is None:
        return None
    author_file = f"{git_path}/metadata/{generate_author_file(commit.author.name)}"
    if not os.path.isfile(author_file):
        logger.error(f"File {author_file} not exist, please check commit {commit.hash} manually")
        return None
    line_for_changeID = get_line_from_csv(author_file, change_id)
    if line_for_changeID is None:
        return None
    patch_info_dict = Common.parse_patch_info(line_for_changeID)[1]
    return patch_info_dict


def show_objects_changed_by_features(objects_changed_by_features: dict):
    """
    print all information script analyzed about which functions each OFED feature changing
    :param objects_changed_by_features:
    :return:
    """
    title = "show_feature_functions"
    logger.info(f"{title}")
    logger.info('='*len(title))
    for key in objects_changed_by_features:
        logger.info(f"Feature '{key}':")
        [logger.info(f"\t'{x}'") for x in objects_changed_by_features[key]]


def show_runtime(end_time, start_time):
    runtime = end_time - start_time
    msg = f"Script run time:  {str(datetime.timedelta(seconds=runtime//1))}"
    logger.info('-' * len(msg))
    logger.info(msg)
    logger.info('-' * len(msg))


def create_dict_from_json(file_path: str) -> dict:
    """
    build dict from Json file path
    :param file_path: str
    :return: dict
    """
    try:
        with open(file_path) as json_file:
            ret = json.load(json_file)
        return ret
    except Exception as e:
        logger.exception(f"Could not read from json file '{file_path}':\n{e}")


def save_dict_to_json(metadata: dict, features: dict):
    """
    extract script data dicts into json files
    :param metadata:
    :param features:
    :return:
    """
    try:
        filename = "feature_objects_changed.txt"
        with open(filename, 'w') as handle:
            json.dump(features, handle, indent=4)
        filename = "metadata_commits.txt"
        with open(filename, "w") as handle:
            json.dump(metadata, handle, indent=4)
    except Exception as e:
        logger.exception(f"Could not save dict into {filename}:\n{e}")


def verify_ofed_dir(git_path):
    if not os.path.isdir(f"{git_path}/metadata"):
        return False
    return True


def show_changed_list(kernel_commits_info: list, from_version: str, to_version: str):
    print(f"Methods changed between kernel {from_version} to kernel {to_version}:")
    [print(meth) for meth in sorted(kernel_commits_info)]


def parse_input_args(args):
    """
    עretrieve args from parser
    :return:
    """
    return args.path, args.ofed_repo, args.start_tag, args.end_tag


def main():
    global git_path
    global is_ofed
    logger_legend()
    start_time = time.time()
    args = parse_args()
    logger.debug(args)
    git_path, is_ofed, from_version, to_version = parse_input_args(args)
    if git_path.endswith('/'):
        git_path = git_path[:-1]  # remove last '/' if exist
    if not os.path.isdir(git_path):
        logger.critical(f'Path {git_path} is not a directory')
        exit(1)
    if not is_git_repo(git_path):
        logger.critical(f'Path {git_path} is not a git repo')
        exit(1)
    if is_ofed:
        if not verify_ofed_dir(git_path):
            logger.critical(f'Path {git_path} is not an OFED repo [-ofed_repo used in command]')
            exit(1)
    if is_ofed:
        git_repo = RepositoryMining(git_path, from_tag='vmlnx-ofed-5.2-0.6.3')
        # git_repo = RepositoryMining(git_path)
    else:
        if from_version == '' or to_version == '':
            logger.critical('For kernel analyze script must get both -start_tag, -end_tag')
            exit(1)
        git_repo = RepositoryMining(git_path, from_tag=from_version, to_tag=to_version)
    if is_ofed:
        metadata_commit_info, objects_changed_by_features = process_ofed_repo(git_repo)
    else:
        try:
            kernel_commits_info = process_kernel_repo(git_repo)
        except Exception as e:
            logger.critical(f"Could not create RepositoryMining,\n{e}")
    end_time = time.time()
    if is_ofed:
        show_objects_changed_by_features(objects_changed_by_features)
        save_dict_to_json(metadata_commit_info, objects_changed_by_features)
    else:
        show_changed_list(kernel_commits_info, from_version, to_version)
    show_runtime(end_time, start_time)


if __name__ == '__main__':
    main()
