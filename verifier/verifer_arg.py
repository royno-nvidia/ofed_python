import logging
import os
import git
from scripts.utils.setting_utils import Status

logger = logging.getLogger("Verifier")


class Verifier(object):
    def __init__(self, args):
        self.git_path = args.path
        self.is_ofed = args.ofed_repo
        self.start_tag = args.start_tag
        self.end_tag = args.end_tag
        self.check()

    def check(self):
        if getattr(self, "git_path", "").endswith('/'):
            self.git_path = self.git_path[:-1]  # remove last '/' if exist
        if not os.path.isdir(self.git_path):
            logger.critical(f'Path {self.git_path} is not a directory')
            return Status.FAIL
        if not self.is_git_repo(self.git_path):
            logger.critical(f'Path {self.git_path} is not a git repo')
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
