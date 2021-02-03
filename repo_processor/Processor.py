from datetime import datetime
import json
import logging
import os

from colorlog import ColoredFormatter
from pydriller import Commit, RepositoryMining

from ofed_classes.OfedRepository import OfedRepository
from utils.setting_utils import get_logger, JSON_LOC

logger = get_logger('Processor', 'Processor.log')


class Processor(object):
    def __init__(self, args=None, repo=None):
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
                # show progress to user
                logger.info(f"commits processed: {self._commits_processed} "
                            f"[{int((self._commits_processed / self._overall_commits) * 100)}%]")
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
            self._results = {'modified': {},
                             'deleted': {}}
        except Exception as e:
            logger.critical(f"Fail to process kernel: '{self._repo_path}',\n{e}")
        try:
            for commit in self._repo.traverse_commits():
                logger.debug(f'Processing commit {commit.hash}:')
                # iterate all commit in repo
                self.up()
                for mod in commit.modifications:
                    before_methods = set([meth.name for meth in mod.methods_before])
                    after_methods = set([meth.name for meth in mod.methods])
                    delete_methods = list(before_methods - after_methods)
                    # if method name was in file before commit and missing after means function
                    # deleted/moved/renamed any way handled as deleted
                    logger.debug('removed methods in commit:')
                    for delete in delete_methods:
                        logger.debug(f'{delete}')
                        if delete not in self._results['deleted'].keys():
                            self._results['deleted'][delete] = 0  # for now 0 maybe will be changed
                    if len(mod.changed_methods) > 0:
                        logger.debug('changed methods in commit:')
                        for method in mod.changed_methods:
                            # iterate all changed methods
                            logger.debug(f'{method.name}')
                            key = method.name
                            if key not in self._results['modified'].keys():
                                self._results['modified'][key] = 0  # for now 0 maybe will be changed
        except Exception as e:
            logger.critical(f"Fail to process commit : '{commit.hash}',\n{e}")
        logger.info(f"over all commits processed: {self._commits_processed}")

    def ofed_repo_processor(self):
        """
        Process self._repo_for_process in case of OFED repo
        when iterate all commits in repo and create dict {'feature': [method changed by feature list]}
        :return:
        """
        try:
            self._repo = OfedRepository(self._repo_path,
                                        None if not self._args.start_tag else self._args.start_tag,
                                        None if not self._args.start_tag else self._args.end_tag)
            self.set_overall_commits(self._repo)
        except Exception as e:
            logger.critical(f"Fail to process OfedRepository: '{self._repo_path}',\n{e}")
        block_ofed_only = True
        try:
            for ofed_commit in self._repo.traverse_commits():
                if ofed_commit.info is None:
                    logger.warn(f"Could not get metadata info - hash: {ofed_commit.commit.hash[:12]}")
                    continue
                feature = ofed_commit.info['feature']
                # iterate all repo commit
                logger.debug(f"process hash: {ofed_commit.commit.hash[:12]}, feature: {feature}")
                self.up()
                if ofed_commit.info['upstream_status'] == 'accepted':
                    # skip accepted
                    logger.debug(f"skipped due to accepted status")
                    continue
                for mod in ofed_commit.commit.modifications:
                    # iterate all modifications in commit
                    if len(mod.changed_methods) > 0:
                        if block_ofed_only:
                            # ofed repo commits are setting the base code so methods added
                            # in those commits not ofed only but kernel methods!
                            added_methods = []
                        else:
                            methods_before = [meth.name for meth in mod.methods_before]
                            methods_after = [meth.name for meth in mod.methods]
                            added_methods = list(set(methods_after) - set(methods_before))
                            # sets algebra, methods after\methods before = method added by commit
                        logger.debug('methods changed:')
                        for method in mod.changed_methods:
                            logger.debug(f'{method.name} in file {method.filename}')
                            if feature in self._results.keys():
                                # if feature exist append method name (don't care about name duplications
                                # removed latter)
                                self._results[feature]['kernel'].append(method.name)
                            else:
                                # first feature appearance, create key in dict and append
                                self._results[feature] = {'kernel': [],
                                                          'ofed_only': []}
                                self._results[feature]['kernel'].append(method.name)
                            logger.debug('Methods added by OFED:')
                            for ofed_method in added_methods:
                                # iterate new methods added by ofed
                                    logger.debug(f'{ofed_method}')
                                    self._results[feature]['ofed_only'].append(ofed_method)
                    else:
                        logger.debug(f'No method changed in file {mod.filename}')
                if "Set base code to" in ofed_commit.commit.msg:
                    block_ofed_only = False

            # remove duplications
            for feature in self._results.keys():
                # itarate all featurs in dict
                # do it only if feature added only_ofed methods
                ofed_set = set(self._results[feature]['ofed_only'])
                kernel_set = set(self._results[feature]['kernel'])
                self._results[feature]['kernel'] = list(kernel_set - ofed_set)
                # kernel methods contain all methods, removing ofed_only methods from it
                self._results[feature]['ofed_only'] = list(ofed_set)
                # remove duplicates also from ofed_only methods [shouldn't be but just in case]

        except Exception as e:
            logger.critical(f"Fail to process commit: '{ofed_commit.commit.hash}',\n{e}")
        logger.info(f"over all commits processed: {self._commits_processed}")

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
            filename = f"{name}.json"
        with open(JSON_LOC+filename, 'w') as handle:
            json.dump(self._results, handle, indent=4)
        self._last_result_path = os.path.abspath(filename)
        logger.info(f"Results saved in '{JSON_LOC + filename}'")
