import logging
from colorlog import ColoredFormatter
from pydriller import Commit
from utils.setting_utils import get_logger

logger = get_logger('OfedCommit', 'OfedCommit.log')


class OfedCommit(object):
    def __init__(self, commit: Commit, change_id: str, info: dict):
        """
        Init OfedCommit, create extension for RepositoryMining.Commit and add OFED commit info for commit
        :param commit: Commit
        :param change_id: str
        :param info: dict
        """
        self._commit = commit
        self._change_id = change_id
        self._metadata_info = info

    @property
    def commit(self):
        """
        OfedCommit.commit getter
        :return: Commit
        """
        return self._commit
    # @commit.setter
    # def repository(self, commit):
    #     self._commit = commit

    @property
    def change_id(self):
        """
        OfedCommit.change_id getter
        :return: str
        """
        return self._change_id

    @property
    def info(self):
        """
        OfedCommit.info getter
        :return:
        """
        return self._metadata_info
