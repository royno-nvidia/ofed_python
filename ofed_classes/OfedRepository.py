import json
import logging
import re
from typing import Generator

from colorlog import ColoredFormatter
from pydriller import RepositoryMining as Repository, Commit
from ofed_classes.Metadata import Metadata
from ofed_classes.OfedCommit import OfedCommit
from utils.setting_utils import get_logger

logger = get_logger('OfedRepoisitory', 'OfedRepoisitory.log')


class OfedRepository(object):
    def __init__(self,
                 path: str,
                 from_commit: str = None,
                 to_commit: str = None,
                 from_tag: str = None,
                 to_tag: str = None):
        """
        Init OfedRepository, create instance of OfedRepository
        :param path: absolute path for rep
        """
        absolute_path = path if not path.endswith('/') else path[:-1]
        self._repository = Repository(absolute_path, from_commit=from_commit,
                                            to_commit=to_commit, from_tag=from_tag, to_tag=to_tag)
        self._metadata = Metadata(absolute_path)
        logger.debug(json.dumps(self._metadata.info, indent=4))

    def traverse_commits(self):
        """
        Create ofed commit generator, return OfedCommit in each iteration
        :return: OfedCommits generator
        """
        for commit in self._repository.traverse_commits():
            change_id = self.get_change_id(commit)
            info = self._metadata.get_info_for_change_id(commit.author.name, change_id)
            yield OfedCommit(commit, change_id, info)

    def get_change_id(self, commit: Commit):
        """
         Parse OFED commit unique change-id
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

    @property
    def metadata(self):
        """
        OfedRepository.metadata getter
        :return:
        """
        return self._metadata
