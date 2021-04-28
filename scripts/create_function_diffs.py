import argparse
import datetime
import logging
import time
from pprint import pprint

from colorlog import ColoredFormatter

from Comperator.Comperator import Comperator
from repo_processor.Processor import Processor
from utils.setting_utils import get_logger
from verifier.verifer_arg import *

logger = get_logger('Processor', 'Processor.log')


def parse_args():
    parser = argparse.ArgumentParser(description="Create dictionary for kernel methods changes between versions")
    parser.add_argument("-src", type=str, default="", required=True,
                        help="Linus repository checkout at source version")
    parser.add_argument("-dst", type=str, default=None, required=True,
                        help="Linus repository checkout at source version")
    parser.add_argument("-kernel_methods_info", type=str, default=None, required=True,
                        help="Name of Json under Jsons/ directory")
    parser.add_argument("-output", type=str, default=None, required=True,
                        help="Name for Json result file")
    parser.add_argument("-ofed_methods_info", type=str, default=None, required=True,
                        help="Name of Json under Jsons/ directory")
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
    if not functions_diff_checks(args):
        logger.critical('Argument verify failed, exiting')
        exit(1)

    Processor.get_kernels_methods_diffs(args.src, args.dst,
                                        args.kernel_methods_info,
                                        args.output,
                                        args.ofed_methods_info)
    end_time = time.time()
    show_runtime(end_time, start_time)


if __name__ == '__main__':
    main()
