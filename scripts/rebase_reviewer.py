import argparse
import datetime
import time

from analyzer.Analyzer import Analyzer
from repo_processor.Processor import Processor
from verifier.verifer_arg import *

logger = get_logger('Analyzer', 'Analyzer.log')


def parse_args():
    parser = argparse.ArgumentParser(description="OFED post-rebase script\n"
                                                 "Compare and alert functions")
    parser.add_argument("-ofed_repo", type=str, default=None, required=True,
                        help="Path for last OFED repo")
    parser.add_argument("-ofed_json", type=str, default=None, required=True,
                        help="Path for OFED Json with pre-rebase process results")
    parser.add_argument("-rebase_repo", type=str, default=None, required=True,
                        help="Path for current rebase repo")
    parser.add_argument("-kernel_src", type=str, default=None, required=True,
                        help="Path for upstream repo checkout on base tag of lase ofed")
    parser.add_argument("-kernel_dst", type=str, default=None, required=True,
                        help="Path for upstream repo checkout on current rebase base")
    # parser.add_argument("-diff", type=str, default=None, required=True,
    #                     help="Path for kernel function diff with Comperator results")
    # parser.add_argument("-ofed_extracted_functions", type=str, default=None, required=True,
    #                     help="Path for OFED extracted last version functions")
    # parser.add_argument("-ofed_tag", type=str, default="", required=True,
    #                     help="OFED version tag processed")
    # parser.add_argument("-kernel_start_tag", type=str, default="", required=True,
    #                     help="Kernel version start tag processed")
    # parser.add_argument("-kernel_end_tag", type=str, default="", required=True,
    #                     help="Kernel version end tag processed")
    parser.add_argument("-output", type=str, default=None, required=True,
                        help="Result Excel name")
    options = parser.parse_args()
    return options


def show_runtime(end_time, start_time):
    """
    display script runtime in logger
    :param end_time:
    :param start_time:
    :return:
    """
    runtime = end_time - start_time
    msg = f"Script run time:  {str(datetime.timedelta(seconds=runtime//1))}"
    logger.info('-' * len(msg))
    logger.info(msg)
    logger.info('-' * len(msg))


def main():
    start_time = time.time()
    args = parse_args()
    # file_list_verify = []
    # file_list_verify.extend(args.kernel)
    # file_list_verify.append(args.ofed)
    # file_list_verify.append(args.diff)
    # file_list_verify.append(args.ofed_extracted_functions)
    # if not checks_for_Analyzer(file_list_verify, args.output):
    #     logger.critical('Argument verify failed, exiting')
    #     exit(1)
    ext_loc = Processor.get_extraction_for_all_ofed_functions(args)
    location = Analyzer.create_diffs_from_extracted(ext_loc)
    Analyzer.create_rebase_reviews_excel(location, args.output)
    end_time = time.time()
    show_runtime(end_time, start_time)


if __name__ == '__main__':
    main()
