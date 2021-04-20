import argparse
import datetime
import logging
import time
from pprint import pprint

from colorlog import ColoredFormatter

from Comperator.Comperator import Comperator
from repo_processor.Processor import Processor
from repo_processor.processor_helpers import save_to_json
from utils.setting_utils import get_logger
from verifier.verifer_arg import *

logger = get_logger('Processor', 'Processor.log')


def parse_args():
    parser = argparse.ArgumentParser(description="Processing OFED repository and make json shows which functions each OFED feature relies on")
    parser.add_argument("-path", type=str, default="", required=True, help="OFED git path")
    parser.add_argument("-start_tag", type=str, default=None,
                        help="Script will process only commits from tag and above [must be valid tag in -path repo]")
    parser.add_argument("-end_tag", type=str, default=None,
                        help="Script will process only commits up to tag [must be valid tag in -path repo]")
    parser.add_argument("-output", type=str, default=None,
                        help="Name for Json result file")
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
    if not checks_for_processor(args):
        logger.critical('Argument verify failed, exiting')
        exit(1)
    pr = Processor(args,args.path)
    pr.process()
    res = pr.results
    save_to_json(res, args.output)
    end_time = time.time()
    show_runtime(end_time, start_time)


if __name__ == '__main__':
    main()
