import json
import os
from pprint import pprint

from pydriller import Commit, RepositoryMining
from Comperator.Comperator import Comperator
from Comperator.comperator_helpers import extract_method_from_file
from ofed_classes.OfedRepository import OfedRepository
from repo_processor.processor_helpers import *
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
        self._results = None
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
        logger.info(f'Repository contains {self._overall_commits} commits')

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
            if self._args.by_commit:
                self.ofed_process_by_commit()
            else:
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
            self._results = {}
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
                        self._results[method.name] = {
                            'Location': mod_file_path,
                            'Status': 'Modify'
                        }
                        logger.debug(f"self._results[{method.name}] = {self._results[method.name]}")
                    for deleted in delete_methods_in_file:
                        self._results[deleted] = {
                            'location': mod_file_path,
                            'Status': 'Delete'
                        }
                        logger.debug(f"self._results[{deleted}] = {self._results[deleted]}")
        #     create _results dict, make sure deleted method don't appear also in modified
            for method in all_deleted_methods_set:
                # itarate all methods removed from kernel to avoid duplications
                ret = self._results.pop(method, None)  # throw ofed only duplicates in 'kernel'
                if ret is None:
                    logger.debug(f"could not find {method} in result['modified']")
                else:
                    logger.debug(f"{method} abandoned from kernel, removed from result['modified']")
        except Exception as e:
            logger.critical(f"Fail to process commit : '{commit.hash}',\n{e}")
        logger.info(f"over all commits processed: {self._commits_processed}")

    def ofed_process_by_commit(self):
        """
        Process self._repo_for_process in case of OFED repo
        when iterate all commits in repo and create dict {'commit': [method changed by feature list]}
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
        all_tree_info = []
        added_methods_in_commit = []
        try:
            # cnt = 0
            ofed_only_set = set()
            for ofed_commit in self._repo.traverse_commits():
                if ofed_commit.info is None:
                    logger.warn(f"Could not get metadata info - hash: {ofed_commit.commit.hash[:12]}")
                    continue
                cstatus = ofed_commit.info['upstream_status']
                if cstatus == 'accepted' or cstatus == 'ignore':
                    continue
                chash = ofed_commit.commit.hash
                csubj = ofed_commit.info['subject']
                ccid = ofed_commit.info['Change-Id']
                cauthor = ofed_commit.commit.author.name

                cfeature = ofed_commit.info['feature']

                commit_info_dict = {
                    'Hash': chash,
                    'Subject': csubj,
                    'Change-Id': ccid,
                    'Author': cauthor,
                    'Status': cstatus,
                    'Feature': cfeature
                }
                commit_methods_info = {}
                # iterate all repo commit
                logger.debug(f"process hash: {ofed_commit.commit.hash[:12]}, feature: {cfeature}")
                self.up()
                if cfeature == 'accepted':
                    # skip accepted
                    logger.debug(f"skipped {chash} due to accepted status")
                    continue
                for mod in ofed_commit.commit.modifications:
                    mod_file_path = mod.new_path
                    # iterate all modifications in commit
                    if len(mod.changed_methods) > 0:
                        if block_ofed_only:
                            # ofed repo commits are setting the base code so methods added
                            # in those commits not ofed only but kernel methods!
                            added_methods_in_commit = []
                        else:
                            methods_before_commit = [meth.name for meth in mod.methods_before]
                            methods_after_commit = [meth.name for meth in mod.methods]
                            added_methods_in_commit = list(set(methods_after_commit) - set(methods_before_commit))
                            # sets algebra, methods after\methods before = method added by commit

                        logger.debug('methods changed:')
                        for method in mod.changed_methods:
                            # add all changed methods to dict
                            commit_methods_info[method.name] = {
                                'Location': mod_file_path,
                                'Status': 'Modify'
                            }
                        for ofed_method in added_methods_in_commit:
                            # add all added methods to dict
                            commit_methods_info[ofed_method] = {
                                'Location': mod_file_path,
                                'Status': 'Add'
                            }
                            ofed_only_set.add(ofed_method)
                    else:
                        logger.debug(f'nothing to do in {ofed_commit.commit.hash}, file {mod.filename}')
                commit_info_dict['Functions'] = commit_methods_info
                all_tree_info.append(commit_info_dict)
                if "Set base code to" in ofed_commit.commit.msg:
                    block_ofed_only = False
            self._results = verify_added_funtions_status(all_tree_info, ofed_only_set)
            save_to_json(self._results)
        except Exception as e:
            logger.critical(f"Fail to process commit: '{ofed_commit.commit.hash}',\n{e}")
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
            save_to_json(self._results)
        except Exception as e:
            logger.critical(f"Fail to process commit: '{ofed_commit.commit.hash}',\n{e}")
        logger.info(f"over all commits processed: {self._commits_processed}")



    @staticmethod
    def get_kernels_methods_diffs(src_kernel_path: str, dst_kernel_path: str,
                                  kernels_modified_methods_json_path, output_file: str,
                                  minimize, minimized_ofed_json):
        ret_diff_stats = {}
        overall = 0
        able_to_process = 0
        try:
            if minimize:
                with open(JSON_LOC + minimized_ofed_json) as handle:
                    ofed_modified_methods_dict = json.load(handle)
                    actual_ofed_mothods_modified = set()
                    for feature in ofed_modified_methods_dict.keys():
                        pprint(ofed_modified_methods_dict[feature])
                        actual_ofed_mothods_modified |= set(ofed_modified_methods_dict[feature]['kernel'])
                        actual_ofed_mothods_modified |= set(ofed_modified_methods_dict[feature]['ofed_only'])
            with open(JSON_LOC+kernels_modified_methods_json_path) as handle:
                kernels_modified_methods_dict = json.load(handle)
                for key, value in kernels_modified_methods_dict['modified'].items():
                    if minimize and key not in actual_ofed_mothods_modified:
                        continue
                    overall += 1
                    # print(f"key: {key}, value: {value}")
                    src_path = f"{src_kernel_path}/{value['location']}"
                    if not os.path.exists(src_path):
                        logger.warn(f"SRC: FIle not exist: {src_path}")
                    else:
                        src_func = extract_method_from_file(src_path, key)
                    # print(src_func)
                        if src_func is None:
                            logger.warn(f"SRC: Failed to find {key} in file {src_kernel_path}/{value['location']}")
                    dst_path = f"{dst_kernel_path}/{value['location']}"
                    if not os.path.exists(dst_path):
                        logger.warn(f"DST: FIle not exist: {dst_path}")
                    else:
                        dest_func = extract_method_from_file(f"{dst_kernel_path}/{value['location']}", key)
                    # print(dest_func)
                        if dest_func is None:
                            logger.warn(f"DST: Failed to find {key} in file {dst_kernel_path}/{value['location']}")
                    if dest_func is None or src_func is None:
                        continue
                    ret_diff_stats[key] = Comperator.get_functions_diff_stats(src_func, dest_func, key, False)
                    able_to_process += 1
                for key in kernels_modified_methods_dict['deleted'].keys():
                    if minimize and key not in actual_ofed_mothods_modified:
                        continue
                    if 'High risk' not in ret_diff_stats.keys():
                        ret_diff_stats['High risk'] = []
                    ret_diff_stats['High risk'].append(key)

                # if minimize:
                #     overall = len(actual_ofed_mothods_modified)
                # else:
                #     overall = len(kernels_modified_methods_dict['modified'].keys())
                # able_to_process = len(ret_diff_stats.keys())
                save_to_json(ret_diff_stats, output_file)
                logger.info(f"overall functions: {overall}")
                logger.info(f"able to process functions: {able_to_process}")
                logger.info(f"success rate {able_to_process/overall*100}%")
        except IOError as e:
            logger.critical(f"failed to read json:\n{e}")
