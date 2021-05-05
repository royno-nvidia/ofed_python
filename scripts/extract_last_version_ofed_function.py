import argparse
import datetime
import subprocess
import time
from repo_processor.Processor import Processor
from verifier.verifer_arg import *

logger = get_logger('Processor', 'Processor.log')


def parse_args():
    parser = argparse.ArgumentParser(description="Create dictionary for extracted function as in seen in OFED")
    parser.add_argument("-src", type=str, default="", required=True,
                        help="OFED repository")
    parser.add_argument("-ofed_methods_info", type=str, default=None, required=True,
                        help="Name of Json under Jsons/ directory")
    parser.add_argument("-output", type=str, default=None, required=True,
                        help="Json output name")
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
    if not extract_ofed_checks(args):
        logger.critical('Argument verify failed, exiting')
        exit(1)

    Processor.extract_ofed_functions(args.src, args.ofed_methods_info, args.output, False)
    # ofed_appliy_patches(args.src)
    # Processor.extract_ofed_functions(args.src, args.ofed_methods_info, args.output, True)

    end_time = time.time()
    show_runtime(end_time, start_time)


if __name__ == '__main__':
    main()
