from datetime import datetime
import json
import logging
import os

from colorlog import ColoredFormatter
from pydriller import Commit, RepositoryMining

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
    def __init__(self, args = None, repo = None):
        """
        Init Processor instance,
        processor class get path for repo to process.
        :param args: argparse.parse_args()
        :param repo: RepositoryMining/OfedRepository
        """
        self._args = args
        self._repo_path = args.path if not args.path.endswith('/') else args.path[:-1]
        self._repo = repo
        self._is_ofed = self.is_ofed_repo()
        self._results = {}
        self._commits_processed = 0
        self._overall_commits = 0
        self._last_result_path = ""

    @property
    def last_result_path(self):
        """
        Processor.last_result_path getter
        :return: str
        """
        return self._last_result_path

    @property
    def repo_path(self):
        """
        Processor.repo_path getter
        :return: str
        """
        return self._repo_path

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
        logger.info(f'Repository contains {self._overall_commits}..')

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
        if not os.path.isdir(f"{self._repo_path}/metadata"):
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
                logger.info(f"commits processed: {self._commits_processed} "
                            f"[{int((self._commits_processed/self._overall_commits)* 100)}%]")
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

    def kernel_repo_processor(self):
        """
        Process self._repo_for_process in case of Kernel repo
        when iterate all commits in repo and create dict {'method changed name': 0}
        :return:
        """
        try:
            self._repo = RepositoryMining(self._repo_path,
                                        from_tag=self._args.start_tag, to_tag=self._args.end_tag)
            self.set_overall_commits(self._repo)
            self._results['modified'] = {}
            self._results['deleted'] = {}
            for commit in self._repo.traverse_commits():
                self.up()
                for mod in commit.modifications:
                    before_methods = set(mod.methods_before)
                    after_methods = set(mod.methods)
                    delete_methods = list(before_methods - after_methods)
                    for delete in delete_methods:
                        del_func = delete.name
                        if del_func not in self._results['deleted'].keys():
                            self._results['deleted'][del_func] = 0  # for now 0 maybe will be changed
                    if len(mod.changed_methods) > 0:
                        for method in mod.changed_methods:
                            key = method.name
                            if key not in self._results['modified'].keys():
                                self._results['modified'][key] = 0  # for now 0 maybe will be changed
            logger.info(f"over all commits processed: {self._commits_processed}")
        except Exception as e:
            logger.critical(f"Fail to process kernel: '{self._repo_path}',\n{e}")

    def ofed_repo_processor(self):
        """
        Process self._repo_for_process in case of OFED repo
        when iterate all commits in repo and create dict {'feature': [method changed by feature list]}
        :return:
        """
        try:
            self._repo = OfedRepository(self._repo_path)
            self.set_overall_commits(self._repo)
            for ofed_commit in self._repo.traverse_commits():
                self.up()
                if ofed_commit.info['upstream_status'] == 'accepted':
                    continue
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
            logger.critical(f"Fail to process OfedRepository: '{self._repo_path}',\n{e}")

    def save_to_json(self, name=None):
        """
        Output process results into timestamp json file for future analyze
        :return:
        """
        if name is None:
            time_stamp = datetime.timestamp(datetime.now())
            if self._is_ofed:
                filename = f"ofed_{time_stamp}.json"
            else:
                filename = f"kernel_{self._args.start_tag}_{self._args.end_tag}.json"
        else:
            filename = name
        with open(filename, 'w') as handle:
            json.dump(self._results, handle, indent=4)
        self._last_result_path = os.path.abspath(filename)
        logger.info(f"Results saved in '{os.path.abspath(filename)}'")


