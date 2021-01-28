
import argparse
import datetime
import logging
import time
from colorlog import ColoredFormatter
from analyzer.Analyzer import Analyzer
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


def parse_args():
    parser = argparse.ArgumentParser(description="OFED pre-rebase analyzer")
    parser.add_argument("-kernel_json_path", type=str, default="", required=True,
                        help="Path for KERNEL Json with pre-rebase process results")
    parser.add_argument("-ofed_json_path", type=str, default="", required=True,
                        help="Path for OFED Json with pre-rebase process results")
    parser.add_argument("-ofed_tag", type=str, default="", required=True,
                        help="OFED version tag processed")
    parser.add_argument("-kernel_start_tag", type=str, default="", required=True,
                        help="Kernel version start tag processed")
    parser.add_argument("-kernel_end_tag", type=str, default="", required=True,
                        help="Kernel version end tag processed")
    parser.add_argument("-output_filename", type=str, default=None,
                        help="Result Excel name [default: 'Feature_methods_changed']")
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
    if not Verifier.checks_for_Analyzer(args):
        logger.critical('Argument verify failed, exiting')
        exit(1)
    main_res, modify, delete = Analyzer.analyze_changed_method(
        args.kernel_json_path, args.ofed_json_path)
    Analyzer.create_changed_functions_excel(main_res, modify, delete,
                                            'Feature_methods_changed' if
                                            args.output_file_name is None else args.output_filename,
                                            args.kernel_start_tag, args.kernel_end_tag, args.ofed_tag)
    end_time = time.time()
    show_runtime(end_time, start_time)


if __name__ == '__main__':
    main()
