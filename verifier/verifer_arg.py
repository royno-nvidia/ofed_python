import logging
import os
from os.path import dirname

import git

from utils.setting_utils import get_logger, JSON_LOC, EXCEL_LOC

logger = get_logger('Verifier', 'Verifier.log')


def functions_diff_checks(args) -> bool:
    """
    Verify user arguments for script
    :param args: user input
    :return:
    """
    if not is_git_repo(args.src):
        logger.critical(f'Path {args.src} is not a git repo')
        return False
    if not is_git_repo(args.dst):
        logger.critical(f'Path {args.dst} is not a git repo')
        return False
    if not os.path.isfile(f'{JSON_LOC}{args.kernel_methods_info}'):
        logger.critical(f'Path {args.kernel_methods_info} is not a file')
        return False
    if os.path.isfile(f'{JSON_LOC}{args.output}.json'):
        logger.critical(f'{JSON_LOC}{args.output} already exists, please change -output argument')
        return False
    if not os.path.isfile(f'{JSON_LOC}{args.ofed_methods_info}'):
        logger.critical(f'Path {args.ofed_methods_info} is not a file')
        return False
    return True


def extract_ofed_checks(args) -> bool:
    """
    Verify user arguments for script
    :param args: user input
    :return:
    """
    if not is_git_repo(args.src):
        logger.critical(f'Path {args.src} is not a git repo')
        return False
    if os.path.isfile(f'{JSON_LOC}{args.output}.json'):
        logger.critical(f'{JSON_LOC}{args.output} already exists, please change -output argument')
        return False
    if not os.path.isfile(f'{JSON_LOC}{args.ofed_methods_info}'):
        logger.critical(f'Path {args.ofed_methods_info} is not a file')
        return False
    return True


def checks_for_processor(args) -> bool:
    """
    Verify user arguments for script
    :param args: user input
    :return:
    """
    if not os.path.isdir(args.path):
        logger.critical(f'Path {args.path} is not a directory')
        return False
    if not is_git_repo(args.path):
        logger.critical(f'Path {args.path} is not a git repo')
        return False
    return True


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


def checks_for_analyzer(loc_list: list, output: str):
    """
    Verify user arguments for 'pre_rebase_analyzer.py' script
    :param args:
    :return:
    """
    if os.path.isfile(EXCEL_LOC+output+'.xlsx'):
        logger.critical(f'Path {JSON_LOC}/{output}.xlsx already exists\nPlease use another -output argument')
        return False
    return True
