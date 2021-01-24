import logging
import os

import git

from scripts.utils.setting_utils import Status

logger = logging.getLogger("verifer_arg")


def verify_input_args(args):
    """
    Verify user inputs
    :param args:
    :return:
    """
    global git_path, is_ofed
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
    else:
        if from_version == '' or to_version == '':
            logger.critical('For kernel analyze script must get both -start_tag, -end_tag')
            exit(1)


class Verifier(object):
    def __init__(self, args):
        self.git_path = args.path
        self.is_ofed = args.ofed_repo
        self.start_tag = args.start_tag
        self.end_tag = args.end_tag

    def check(self):
        if getattr(self, "git_path", "").endswith('/'):
            self.git_path = self.git_path[:-1]  # remove last '/' if exist
        if not os.path.isdir(self.git_path):
            logger.critical(f'Path {self.git_path} is not a directory')
            return Status.FAIL
        if not self.is_git_repo(self.git_path):
            logger.critical(f'Path {self.git_path} is not a git repo')
            return Status.FAIL
        if self.is_ofed:
            if not self.is_ofed_dir():
                logger.critical(f'Path {self.git_path} is not an OFED repo [-ofed_repo used in command]')
                return Status.FAIL
        else:
            if getattr(self, "start_tag", "") == '' or getattr(self, "end_tag", "") == '':
                logger.critical('For kernel analyze script must get both -start_tag, -end_tag')
                return Status.FAIL
        return Status.SUCCESS

    def is_git_repo(self, path: str) -> bool:
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

    def is_ofed_dir(self):
        """
        search for metadata/ existence inside given path
        :param git_path:
        :return:
        """
        if not os.path.isdir(f"{getattr(self, 'git_path', '')}/metadata"):
            return False
        return True
