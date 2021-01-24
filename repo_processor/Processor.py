from datetime import datetime
import json
import logging
import os

from colorlog import ColoredFormatter
from pydriller import Commit

from ofed_classes.OfedRepository import OfedRepository

logger = logging.getLogger(__name__)
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


class Processor(object):
    def __init__(self, path: str):
        """
        Init Processor instance,
        processor class get path for repo to process.
        :param path: str
        """
        self._repo_for_process = path if not path.endswith('/') else path[:-1]
        self._is_ofed = self.is_ofed_repo()
        self._results = {}
        self._commits_processed = 0
        self._overall_commits = 0
        self.process()
        self.save_to_json()

    @property
    def repo(self):
        """
        Processor.repo getter
        :return: str
        """
        return self._repo_for_process

    @property
    def overall_commits(self):
        """
        Processor.overall_commits getter
        :return:
        """
        return self._overall_commits

    def set_overall_commits(self, repo):
        """
        Calculate number of commits in repo and set Processor.overall_commits accordingly
        :param repo: RepositoryMining
        :return:
        """
        cnt = 0
        for _ in repo.traverse_commits():
            cnt += 1
        self._overall_commits = cnt

    @property
    def results(self):
        """
        Processor.results getter
        :return: dict
        """
        return self._results

    @property
    def commits_precessed(self):
        """
        Processor.commits_precessed getter
        :return: int
        """
        return self._commits_processed

    def is_ofed_repo(self):
        """
        Check for metadata directory in given repo path and decide if OfedRepository accordingly
        :return: bool
        """
        if not os.path.isdir(f"{self._repo_for_process}/metadata"):
            return False
        return True

    def up(self):
        """
        Up Processor.commits_processed by one and print to logger every 100 commits
        :return:
        """
        self._commits_processed += 1
        if self._commits_processed % 100 == 0:
            if self._overall_commits > 0:
                logger.info(f"commits processed: {self._commits_processed} [{int((self._commits_processed/self._overall_commits)* 100)}%]")
            else:
                logger.info(f"commits processed: {self._commits_processed}")

    def process(self):
        """
        Process self._repo_for_process when iterate all commits in repo and create self._results
        :return:
        """
        if self._is_ofed:
            self.ofed_repo_processor()
        else:
            self.kernel_repo_processor()


    def ofed_repo_processor(self):
        """
        Process self._repo_for_process in case of OFED repo
        when iterate all commits in repo and create dict {'feature': [method changed by feature list]}
        :return:
        """
        try:
            ofed_rep = OfedRepository(self._repo_for_process)
            self.set_overall_commits(ofed_rep)
            for ofed_commit in ofed_rep.traverse_commits():
                self.up()
                for mod in ofed_commit.commit.modifications:
                    if len(mod.changed_methods) > 0:
                        feature = ofed_commit.info['feature']
                        for method in mod.changed_methods:
                            if feature in self._results.keys():
                                self._results[feature].append(method.name)
                            else:
                                self._results[feature] = []
                                self._results[feature].append(method.name)
            logger.info(f"over all commits processed: {self._commits_processed}")
        except Exception as e:
            logger.critical(f"Fail to process OfedRepository: '{self._repo_for_process}',\n{e}")

    def save_to_json(self):
        """
        Output process results into timestamp json file for future analyze
        :return:
        """
        time_stamp = datetime.timestamp(datetime.now())
        filename = f"{time_stamp}_results.txt"
        with open(filename, 'w') as handle:
            json.dump(self._results, handle, indent=4)
        logger.info(f"Results saved in '{os.path.abspath(filename)}'")

