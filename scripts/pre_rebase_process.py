
import argparse
import datetime
import logging
import time
from colorlog import ColoredFormatter
from repo_processor.Processor import Processor
from verifier.verifer_arg import Verifier

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
s_formatter = ColoredFormatter('%(log_color)s%(asctime)s[%(filename)s +%(lineno)s] - %(levelname)s - %(message)s%(reset)s')
f_formatter = logging.Formatter('%(asctime)s[%(filename)s +%(lineno)s] - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('processor.log')
file_handler.setFormatter(f_formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(s_formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def parse_args():
    parser = argparse.ArgumentParser(description="OFED pre-rebase process")
    parser.add_argument("-path", type=str, default="", required=True, help="Git path")
    parser.add_argument("-start_tag", type=str, default="",
                        help="Script will process only commits from tag and above [must be valid tag in -path repo]")
    parser.add_argument("-end_tag", type=str, default="",
                        help="Script will process only commits up to tag [must be valid tag in -path repo]")
    parser.add_argument("-output_filename", type=str, default=None,
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
    if not Verifier.checks_for_processor(args):
        logger.critical('Argument verify failed, exiting')
        exit(1)
    pr = Processor(args)
    pr.process()
    pr.save_to_json(args.output_filename)
    end_time = time.time()
    show_runtime(end_time, start_time)


if __name__ == '__main__':
    main()
