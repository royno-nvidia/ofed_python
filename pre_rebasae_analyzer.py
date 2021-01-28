
import argparse
import datetime
import logging
import time
from colorlog import ColoredFormatter
from analyzer.Analyzer import Analyzer
from repo_processor.Processor import Processor
from verifier.verifer_arg import Verifier

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
s_formatter = ColoredFormatter('%(log_color)s%(asctime)s[%(filename)s +%(lineno)s] - %(levelname)s - %(message)s%(reset)s')
f_formatter = logging.Formatter('%(asctime)s[%(filename)s +%(lineno)s] - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('analyzer.log')
file_handler.setFormatter(f_formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(s_formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def logger_legend():
    logger.debug("A quirky message only developers care about")
    logger.info("Curious users might want to know this")
    logger.warn("Something is wrong and any user should be informed")
    logger.error("Serious stuff, this is red for a reason")
    logger.critical("OH NO everything is on fire")


def parse_args():
    parser = argparse.ArgumentParser(description="OFED pre-rebase")
    parser.add_argument("-path", type=str, default="", required=True, help="Git path")
    parser.add_argument("-start_tag", type=str, default="",
                        help="Script will process only commits from tag and above [must be valid tag in -path repo]")
    parser.add_argument("-end_tag", type=str, default="",
                        help="Script will process only commits up to tag [must be valid tag in -path repo]")
    parser.add_argument("-ofed_repo", action='store_true',
                        help="Script will analyze git repo as OFED repo")
    options = parser.parse_args()
    return options
    # More parser examples:
    # parser.add_argument("-hosts", nargs='+', type=str, required=True, help="the host to map GPU/HCA")
    # parser.add_argument("-hca", nargs='+', type=int, required=True,
    #                     help="Hca numbers example \"-hca 0 1 2 3 4 5 6 7\" ")
    # parser.add_argument("-server_hca", default=1, type=int,
    #                     help="choosing the server hca ")
    # parser.add_argument("-json", action='store_true', help="create a json file")
    # parser.add_argument("-xml", action='store_true', help="create a xml file (must be 8 gpu and 8 hca)")


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
    # logger_legend()
    start_time = time.time()
    args = parse_args()
    Verifier(args)
    # pr = Processor(args)
    # pr.process()
    # pr.save_to_json()

    main_res, modify, delete = Analyzer.analyze_changed_method(
        '/swgwork/royno/Full/Python_work_place/OfedProject/kernel_v5.9-rc2_v5.11-rc5.json',
        '/swgwork/royno/Full/Python_work_place/OfedProject/ofed_1611837094.671246.json')
    Analyzer.create_changed_functions_excel(main_res, modify, delete, 'Feature_methods_changed', 'v5.9-rc2', 'v5.11-rc4', '5.2')

    end_time = time.time()
    show_runtime(end_time, start_time)


if __name__ == '__main__':
    main()
