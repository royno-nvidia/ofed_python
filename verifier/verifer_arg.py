import logging
import os
from os.path import dirname

import git

from utils.setting_utils import get_logger, JSON_LOC

logger = get_logger('Verifier', 'Verifier.log')


def checks_for_processor(args) -> bool:
    """
    Verify user arguments for 'pre_rebase_process.py' script
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


def checks_for_Analyzer(loc_list: list):
    """
    Verify user arguments for 'pre_rebase_analyzer.py' script
    :param args:
    :return:
    """

    for path in loc_list:
        if not os.path.isfile(f'{JSON_LOC}/{path}'):
            logger.critical(f'Path {JSON_LOC}/{path} is not a File')
            return False
    return True
