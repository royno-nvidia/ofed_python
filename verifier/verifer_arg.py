import logging
import os
import git
from colorlog import ColoredFormatter

from utils.setting_utils import LOGGER_LOC, get_logger

logger = get_logger('Verifier', 'Verifier.log')


class Verifier(object):

    @staticmethod
    def checks_for_processor(args) -> bool:
        """
        Verify user arguments for 'pre_rebase_process.py' script
        :param args: user input
        :return:
        """
        if not os.path.isdir(args.path):
            logger.critical(f'Path {args.path} is not a directory')
            return False
        if not Verifier.is_git_repo(args.path):
            logger.critical(f'Path {args.path} is not a git repo')
            return False
        return True

    @staticmethod
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

    @staticmethod
    def checks_for_Analyzer(loc_list: list):
        """
        Verify user arguments for 'pre_rebase_analyzer.py' script
        :param args:
        :return:
        """
        for path in loc_list:
            if not os.path.isfile(path):
                logger.critical(f'Path {path} is not a File')
                return False
        return True
