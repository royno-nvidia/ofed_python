
import argparse
from datetime import datetime, timedelta
import logging
import time
from colorlog import ColoredFormatter
from analyzer.Analyzer import Analyzer
from utils.setting_utils import LOGGER_LOC, get_logger
from verifier.verifer_arg import Verifier

logger = get_logger('Analyzer', 'Analyzer.log')


def parse_args():
    parser = argparse.ArgumentParser(description="OFED pre-rebase analyzer\n"
                                                 "E.G: -kernel_json_path /swgwork/royno/Full/Python_work_place/OfedProject/jsons/kernel_v5.9-rc2_v5.11-rc5.json -ofed_json_path /swgwork/royno/Full/Python_work_place/OfedProject/jsons/ofed5_2_2_for_demo.json -ofed_tag vmlnx-ofed-5.2-2.1.8 -kernel_start_tag v5.9-rc2 -kernel_end_tag v5.11-rc5 -output_filename analyzed_for_demo")
    parser.add_argument("-kernel_json", type=str, default="", required=True,
                        help="Path for KERNEL Json with pre-rebase process results")
    parser.add_argument("-new_ofed_json", type=str, default="", required=True,
                        help="Path for OFED Json with pre-rebase process results")
    parser.add_argument("-old_ofed_json", type=str, default="", required=True,
                        help="Path for OFED Json with pre-rebase process results")
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
    if not Verifier.checks_for_Analyzer([args.kernel_json, args.new_ofed_json, args.old_ofed_json]):
        logger.critical('Argument verify failed, exiting')
        exit(1)
    main_res, function_status = Analyzer.post_analyze_changed_method(
        args.kernel_json, args.new_ofed_json, args.old_ofed_json)
    Analyzer.post_create_changed_functions_excel(main_res, function_status,
                                                 'Feature_methods_changed' if
                                                 args.output_filename is None else args.output_filename,
                                                 '', '', '')
    end_time = time.time()
    show_runtime(end_time, start_time)


if __name__ == '__main__':
    main()
