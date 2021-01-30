import os
import logging
from colorlog import ColoredFormatter
from utils import Common
from utils.setting_utils import get_logger

logger = get_logger('Metadata', 'Metadata.log')


class Metadata(object):
    def __init__(self, path: str):
        """
        Init Metadata, get only path to root OFED repo.
        This instance hold all metadata/*.csv info from OFED path.
        :param path: str
        """
        self._path = path if not path.endswith('/') else path[:-1]
        self._info = {}
        self._features = {}
        self.build_metadata_dicts()

    @property
    def info(self):
        """
        Metadata.info getter
        :return: dict = {author name : {changeID : {['Change-Id', 'subject', 'feature', 'upstream_status', 'general'] : info}}}
        """
        return self._info

    @property
    def features(self):
        """
        Metadata.features getter
        :return: dict = {feature: {['type', 'upstream_status'] : info}}
        """
        return self._features

    def get_info_for_change_id(self, author_name: str, change_id: str) -> dict:
        if '_' in author_name:
            author_name = author_name.replace('_', ' ')
        if author_name in self._info.keys():
            if change_id in self._info[author_name].keys():
                return self._info[author_name][change_id]
            else:
                logger.error(f"{author_name} don't have commit with changeID: '{change_id}'")
        else:
            logger.error(f"Author name {author_name} not in dictionary")

    def build_metadata_dicts(self):
        """
        Iner function build both feature and info dicts when Metadata.__init__ called
        :return:
        """
        for file in os.listdir(f'{self._path}/metadata'):
            if not file.endswith('.csv'):
                logger.debug(f"skipped file '{file}'")
                continue
            if "features_metadata" in file:
                self.build_features(f'{self._path}/metadata/{file}')
                continue
            else:
                self.build_author(file)

    def build_features(self, file_path: str):
        """
         build Metadata.features dict from OFED metadata/features_metadata_db.csv
        :param file_path:
        :return:
        """
        try:
            with open(file_path) as handle:
                logger.debug(f"process file: '{file_path}'")
                line_cnt = 0
                for line in handle.readlines():
                    line_cnt += 1
                    if "name" not in line:
                        logger.debug(f"skipped line: '{line.rstrip()}' +{line_cnt} ")
                        continue
                    info = Common.parse_feature_info(line.rstrip())
                    key = info[0]
                    self._features[key] = info[1]
                logger.info(f"processed {line_cnt} lines in '{file_path}'")
        except IOError as e:
            logger.exception(f"could not open file '{file_path}' for read:\n{e}")

    def build_author(self, file: str):
        """
        build Metadata.info dict from OFED metadata/{author}.csv
        :return:
        """
        try:
            file_path = f'{self._path}/metadata/{file}'
            with open(file_path) as handle:
                logger.debug(f"process file: '{file_path}'")
                key = file.replace('.csv', '').replace('_', ' ')
                line_cnt = 0
                for line in handle.readlines():
                    line_cnt += 1
                    if "Change-Id" not in line:
                        logger.debug(f"skipped line: '{line.rstrip()}' +{line_cnt}")
                        continue
                    info = Common.parse_patch_info(line.rstrip())
                    inner_key = info[0]
                    if key in self._info.keys():
                        self._info[key][inner_key] = info[1]
                    else:
                        self._info[key] = {inner_key: info[1]}
                logger.info(f"processed {line_cnt} lines in '{file_path}'")
        except IOError as e:
            logger.exception(f"could not open file '{file}' for read:\n{e}")
