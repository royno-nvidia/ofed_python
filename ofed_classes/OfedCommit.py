import logging
from colorlog import ColoredFormatter
from pydriller import Commit

logger = logging.getLogger('OfedCommit')
logger.setLevel(logging.DEBUG)
s_formatter = ColoredFormatter(
    '%(log_color)s%(asctime)s[%(filename)s +%(lineno)s] - %(levelname)s - %(message)s%(reset)s')
f_formatter = logging.Formatter('%(asctime)s[%(filename)s +%(lineno)s] - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('analyzer.log')
file_handler.setFormatter(f_formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(s_formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


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
