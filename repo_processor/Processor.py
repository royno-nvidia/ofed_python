import subprocess
import os
from pydriller import RepositoryMining as Repository
from Comperator.Comperator import extract_method_from_file, make_readable_function, get_functions_diff_stats, \
    get_diff_stats
from ofed_classes.OfedRepository import OfedRepository
from utils.setting_utils import *

logger = get_logger('Processor', 'Processor.log')


def verify_added_functions_status(all_tree_info: list, ofed_only_set: set):
    for index in range(0, len(all_tree_info)):
        # itarate all commits in tree
        for func in all_tree_info[index]['Functions']:
            if func in ofed_only_set:
                all_tree_info[index]['Functions'][func]['Status'] = 'Add'
                logger.debug(f"{func} moved status to 'Add'")
    return all_tree_info


def get_actual_ofed_info(ofed_json):
    ofed_modified_methods_dict = open_json(ofed_json)
    actual_ofed_functions_modified = set()
    for commit in ofed_modified_methods_dict:
        actual_ofed_functions_modified |= set(
            [func for func in commit['Functions'].keys() if commit['Functions'][func]['Status'] != 'Add']
        )
    return actual_ofed_functions_modified


def get_ofed_functions_info(ofed_json):
    ofed_modified_methods_dict = open_json(ofed_json)
    ofed_funcs = {}
    for commit in ofed_modified_methods_dict:
        for func, info in commit['Functions'].items():
            ofed_funcs[func] = info
    return ofed_funcs


def extract_function(dir_path, func_location, func, prefix, with_backports):
    fpath = f"{dir_path}/{func_location}"
    if not os.path.exists(fpath):
        logger.warn(f"{prefix}: FIle not exist: {fpath} - miss info for {func}")
        return None
    else:
        ext_func = extract_method_from_file(fpath, func)
        if ext_func == '':
            logger.warn(f"{prefix}: Failed to find {func} in file {fpath}")
            return None
    return ext_func


def extract_from_sources(args, func, file):
    src_kernel_path = args.ksrc
    dst_kernel_path = args.kdst
    ofed_src_path = args.osrc

    ret = {
        'src': extract_function(src_kernel_path,
                                      file, func, "SRC", False),
        'dst': extract_function(dst_kernel_path,
                                      file, func, "DST", False),
        'ofed': extract_function(ofed_src_path,
                                       file, func, "OFED", False)
    }
    return ret


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
            self._repo = Repository(self._repo_path,
                                          from_tag=self._args.start_tag, to_tag=self._args.end_tag)
            self.set_overall_commits(self._repo)
            self._results = {}
        except Exception as e:
            logger.critical(f"Fail to process kernel: '{self._repo_path}',\n{e}")
        try:
            all_deleted_methods_set = set()
            all_added_methods_set = set()
            for commit in self._repo.traverse_commits():
                logger.debug(f'Processing commit {commit.hash}:')
                # iterate all commit in repo
                self.up()
                for mod in commit.modifications:
                    mod_file_path = mod.new_path
                    before_methods = set([meth.name for meth in mod.methods_before])
                    after_methods = set([meth.name for meth in mod.methods])
                    delete_methods_in_file = before_methods - after_methods
                    added_methods_in_file = after_methods - before_methods
                    # if method name was in file before commit and missing after means function
                    # deleted/moved/renamed any way handled as deleted
                    all_deleted_methods_set |= delete_methods_in_file
                    all_added_methods_set |= added_methods_in_file
                    for method in mod.changed_methods:
                        # iterate all changed methods in file
                        self._results[method.name] = {
                            'Location': mod_file_path,
                            'Status': 'Modify'
                        }
                        logger.debug(f"self._results[{method.name}] = {self._results[method.name]}")
                    for deleted in delete_methods_in_file:
                        self._results[deleted] = {
                            'Location': mod_file_path,
                            'Status': 'Delete'
                        }
                        logger.debug(f"self._results[{deleted}] = {self._results[deleted]}")
                    for added in added_methods_in_file:
                        self._results[added] = {
                            'Location': mod_file_path,
                            'Status': 'New'
                        }
                        logger.debug(f"self._results[{added}] = {self._results[added]}")
        #     create _results dict, make sure deleted method don't appear also in modified
            for rem in all_deleted_methods_set:
                # Verify all removed methods status is 'Delete'
                self._results[rem]['Status'] = 'Delete'
            for add in all_added_methods_set:
                # Verify all Added methods status is 'New'
                self._results[add]['Status'] = 'New'
        except Exception as e:
            logger.critical(f"Fail to process commit : '{commit.hash}',\n{e}")
        logger.info(f"over all commits processed: {self._commits_processed}")

    def ofed_repo_processor(self):
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
                chash = ofed_commit.commit.hash
                csubj = ofed_commit.info['subject']
                ccid = ofed_commit.info['Change-Id']
                cauthor = ofed_commit.commit.author.name
                cfeature = ofed_commit.info['feature']
                if cfeature == 'rebase_upstream_fixes':
                    logger.warn(f'Skip commit {ofed_commit.commit.hash[0:12]} - Feature: {cfeature} with status {cstatus}')
                    continue
                if cstatus == 'ignore' or cstatus == 'accepted':
                    logger.warn(f'Skip commit {ofed_commit.commit.hash[0:12]} - upstreamm status: {cstatus}')
                    continue

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
                # if cfeature == 'accepted':
                #     # skip accepted
                #     logger.debug(f"skipped {chash} due to accepted status")
                #     continue
                for mod in ofed_commit.commit.modifications:
                    mod_file_path = mod.new_path
                    # iterate all modifications in commit
                    if len(mod.changed_methods) > 0:
                        # if block_ofed_only:
                        #     # ofed repo commits are setting the base code so methods added
                        #     # in those commits not ofed only but kernel methods!
                        #     added_methods_in_commit = []
                        # else:
                        methods_before_commit = [meth.name for meth in mod.methods_before]
                        methods_after_commit = [meth.name for meth in mod.methods]
                        added_methods_in_commit = list(set(methods_after_commit) - set(methods_before_commit))
                        # sets algebra, methods after\methods before = method added by commit

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
                # if "Set base code to" in ofed_commit.commit.msg:
                #     block_ofed_only = False
            self._results = verify_added_functions_status(all_tree_info, ofed_only_set)
        except Exception as e:
            logger.critical(f"Fail to process commit: '{ofed_commit.commit.hash}',\n{e}")
        logger.info(f"over all commits processed: {self._commits_processed}")

    @staticmethod
    def get_kernels_methods_diffs(args):

        kernels_json_path = args.kernel_json
        output_file = args.output
        ofed_json_path = args.ofed_json
        ret_diff_stats = {}
        extracted_functions = {}
        overall = 0
        actual_process = 0

        try:
            actual_ofed_functions_modified = get_actual_ofed_info(ofed_json_path)
            kernels_modified_methods_dict = open_json(kernels_json_path)
            for func in actual_ofed_functions_modified:
                overall += 1
                if func not in kernels_modified_methods_dict.keys():
                    # handle no risk (not changed)functions
                    print(f'{func}- handle no risk')
                    ret = get_functions_diff_stats(None, None, func, False, LOW)
                    ret_diff_stats[func] = ret
                    continue
                func_status = kernels_modified_methods_dict[func]['Status']
                file = kernels_modified_methods_dict[func]['Location']
                if func_status == 'Delete':
                    # handle removed function - SEVERE risk
                    ret_diff_stats[func] = get_functions_diff_stats(None, None,
                                                                    func, True, SEVERE)

                else:
                    # handle all other risks
                    if func in extracted_functions.keys():
                        continue
                    ext = extract_from_sources(args, func, file)
                    extracted_functions[func] = ext
                    if ext['src'] is None or ext['dst'] is None:
                        continue
                    ret_diff_stats[func] = get_functions_diff_stats(ext['src'], ext['dst'],
                                                                    func, False, None)
                    actual_process += 1
            readable_extracted = {}
            for func, value in extracted_functions.items():
                readable_extracted[func] = {
                    'src': make_readable_function(value['src']),
                    'dst': make_readable_function(value['dst']),
                    'ofed': make_readable_function(value['ofed']),
                }
                diff = get_diff_stats(readable_extracted[func]['dst'],
                                      readable_extracted[func]['ofed'], func)
                readable_extracted[func]['Aligned'] = diff['Aligned'] if diff else None
            loc = {
                'ext': save_to_json(readable_extracted, f'{output_file}_ext_sources', output_file),
                'stats': save_to_json(ret_diff_stats, f'{output_file}_diff', output_file)
            }
            logger.info(f"overall functions: {overall}")
            logger.info(f"able to process functions: {actual_process}")
            if overall > 0:
                logger.info(f"success rate {actual_process/overall*100}% - [{actual_process}/{overall}]")
            return loc
        except IOError as e:
            logger.critical(f"failed to read json:\n{e}")

    @staticmethod
    def extract_ofed_functions(src_ofed_path: str, ofed_json_path: str, output: str, with_backports: bool):
        prefix = 'OFED backports' if with_backports else 'OFED'
        extracted_functions = {}
        overall = 0
        actual = 0

        ofed_modified_dict = open_json(ofed_json_path)
        for commit in ofed_modified_dict:
            for func, info in commit['Functions'].items():
                overall += 1
                if func in extracted_functions.keys():
                    overall -= 1
                    continue
                location = info['Location']
                src_func = make_readable_function(extract_function(src_ofed_path, location, func, prefix, with_backports))
                if src_func is None:
                    logger.warn(f"Unable to extract {func} from {location}")
                    continue
                actual += 1
                extracted_functions[func] = {}
                extracted_functions[func]['View'] = src_func
        try:
            postfix = '_back' if with_backports else '_ext'
            loc = save_to_json(extracted_functions, f'{output}{postfix}', output)
            logger.info(f"Process rate: {actual}/{overall} = {(actual/overall)*100}%")
            return loc
        except IOError as e:
            logger.critical(f"Unable to save results to {output}:\n{e}")


    @staticmethod
    def get_extraction_for_all_ofed_functions(args):
        ofed_functions = get_ofed_functions_info(args.ofed_json)
        error_list = []
        function_ext_dict = {}

        for func, info in ofed_functions.items():
            src_ext, dst_ext = '', ''
            last_ext = extract_function(args.ofed_repo, info['Location'], func, "Last OFED", False)
            curr_ext = extract_function(args.rebase_repo, info['Location'], func, "Rebase", False)
            if info['Status'] == 'Modify':
                src_ext = extract_function(args.kernel_src, info['Location'], func, "SRC", False)
                dst_ext = extract_function(args.kernel_dst, info['Location'], func, "DST", False)
            if not last_ext or not curr_ext or (info['Status'] == 'Modify' and (not src_ext or not dst_ext)):
                error_list.append(func)
                logger.warn(f"Function {func} - Failed to process")
                continue

            function_ext_dict[func] = {
                'Last': last_ext,
                'Rebase': curr_ext,
                'Src': src_ext,
                'Dst': dst_ext
            }

        function_ext_dict['Missing info'] = error_list
        location = save_to_json(function_ext_dict, args.output,f'{args.output}_ext_dict')
        overall = len(ofed_functions.keys())
        able = overall - len(error_list)
        logger.info(f'Success process rate: {(able/overall)*100:.2f}% [{able}/{overall}]')
        return location