from datetime import datetime
import json
import logging
import os

from colorlog import ColoredFormatter
from pydriller import Commit, RepositoryMining

from Comperator.Comperator import Comperator
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
            all_deleted_methods_set = set()
            for commit in self._repo.traverse_commits():
                logger.debug(f'Processing commit {commit.hash}:')
                # iterate all commit in repo
                self.up()
                for mod in commit.modifications:
                    mod_file_path = mod.new_path
                    before_methods = set([meth.name for meth in mod.methods_before])
                    after_methods = set([meth.name for meth in mod.methods])
                    delete_methods_in_file = before_methods - after_methods
                    # if method name was in file before commit and missing after means function
                    # deleted/moved/renamed any way handled as deleted
                    all_deleted_methods_set |= delete_methods_in_file
                    for method in mod.changed_methods:
                        # iterate all changed methods in file
                        self._results['modified'][method.name] = {'location': mod_file_path}
                        logger.debug(f"self._results['modified'][{method.name}] = 'location': {mod_file_path}")
                    for deleted in delete_methods_in_file:
                        self._results['deleted'][deleted] = {'location': mod_file_path}
                        logger.debug(f"self._results['deleted'][{deleted}] = 'location': {mod_file_path}")
        #     create _results dict, make sure deleted method don't appear also in modified
            for method in all_deleted_methods_set:
                # itarate all methods removed from kernel to avoid duplications
                ret = self._results['modified'].pop(method, None)  # throw ofed only duplicates in 'kernel'
                if ret is None:
                    logger.debug(f"could not find {method} in result['modified']")
                else:
                    logger.debug(f"{method} abandoned from kernel, removed from result['modified']")
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
            # cnt = 0
            ofed_only_set = set()
            for ofed_commit in self._repo.traverse_commits():
                if ofed_commit.info is None:
                    logger.warn(f"Could not get metadata info - hash: {ofed_commit.commit.hash[:12]}")
                    continue
                # if cnt > 10:
                #     break
                # cnt += 1
                feature = ofed_commit.info['feature']
                # iterate all repo commit
                logger.debug(f"process hash: {ofed_commit.commit.hash[:12]}, feature: {feature}")
                self.up()
                if ofed_commit.info['upstream_status'] == 'accepted':
                    # skip accepted
                    logger.debug(f"skipped due to accepted status")
                    continue
                for mod in ofed_commit.commit.modifications:
                    mod_file_path = mod.new_path
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
                            # add all changed methods to dict
                            if feature in self._results.keys():
                                # if feature exist add relevant method
                                self._results[feature]['kernel'][method.name] = {'location': mod_file_path}
                                logger.debug(f'feature {feature} exist, adding: {method.name} in file {method.filename}')
                            else:
                                # first feature appearance, create key in dict and append
                                self._results[feature] = {'kernel': {},
                                                          'ofed_only': {}}
                                self._results[feature]['kernel'][method.name] = {'location': mod_file_path}
                                logger.debug(
                                    f'feature {feature} first appearence, adding: {method.name} in file {method.filename}')
                        for ofed_method in added_methods:
                            # add all added methods to dict
                            self._results[feature]['ofed_only'][ofed_method] = {'location': mod_file_path}
                            ofed_only_set.add(ofed_method)
                            # iterate new methods added by ofed
                            logger.debug(f'{ofed_method} added by ofed in commit {ofed_commit.commit.hash}')
                            # self._results[feature]['ofed_only'].append(ofed_method)
                    else:
                        logger.debug(f'nothing to do in {ofed_commit.commit.hash}, file {mod.filename}')
                if "Set base code to" in ofed_commit.commit.msg:
                    block_ofed_only = False

            # create ofed_only
            for feature in self._results.keys():
                # itarate all featurs in dict
                for ofed_func in ofed_only_set:
                    ret = self._results[feature]['kernel'].pop(ofed_func, None) # throw ofed only duplicates in 'kernel'
                    if ret is None:
                        logger.debug(f"could not find {ofed_func} in result[{feature}]['kernel']")
                    else:
                        logger.debug(f"{ofed_func} is ofed only, removed from result[{feature}]['kernel']")
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

    @staticmethod
    def get_kernels_methods_diffs(src_kernel_path: str, dst_kernel_path: str,
                                  kernels_modified_methods_json_path, output_file: str):
        ret_diff_stats = {}
        overall = 0
        able_to_process = 0
        try:
            with open(JSON_LOC+kernels_modified_methods_json_path) as handle:
                kernels_modified_methods_dict = json.load(handle)
                for key, value in kernels_modified_methods_dict['modified'].items():
                    # print(f"key: {key}, value: {value}")
                    src_path = f"{src_kernel_path}/{value['location']}"
                    if not os.path.exists(src_path):
                        logger.warn(f"SRC: FIle not exist: {src_path}")
                    else:
                        src_func = Comperator.extract_method_from_file(src_path, key)
                    # print(src_func)
                        if src_func is None:
                            logger.warn(f"SRC: Failed to find {key} in file {src_kernel_path}/{value['location']}")
                    dst_path = f"{dst_kernel_path}/{value['location']}"
                    if not os.path.exists(dst_path):
                        logger.warn(f"DST: FIle not exist: {dst_path}")
                    else:
                        dest_func = Comperator.extract_method_from_file(f"{dst_kernel_path}/{value['location']}", key)
                    # print(dest_func)
                        if dest_func is None:
                            logger.warn(f"DST: Failed to find {key} in file {dst_kernel_path}/{value['location']}")
                    if dest_func is None or src_func is None:
                        continue
                    ret_diff_stats[key] = Comperator.get_functions_diff_stats(src_func, dest_func, key)
                    able_to_process += 1
                overall= len(kernels_modified_methods_dict['modified'].keys())
                # able_to_process = len(ret_diff_stats.keys())
                with open(JSON_LOC + output_file, 'w') as handle:
                    json.dump(ret_diff_stats, handle, indent=4)
                logger.debug(f"create json: {output_file}")
                print(f"overall functions: {overall}")
                print(f"able to process functions: {able_to_process}")
                print(f"success rate {able_to_process/overall*100}%")
        except IOError as e:
            logger.critical(f"failed to read json:\n{e}")
