
import argparse
import datetime
import logging
import time
from pprint import pprint

from colorlog import ColoredFormatter

from Comperator.Comperator import Comperator
from analyzer.Analyzer import Analyzer
from utils.setting_utils import LOGGER_LOC, get_logger
from verifier.verifer_arg import Verifier

logger = get_logger('Analyzer', 'Analyzer.log')


def parse_args():
    parser = argparse.ArgumentParser(description="OFED pre-rebase analyzer\n"
                                                 "E.G: -kernel_json_path /swgwork/royno/Full/Python_work_place/OfedProject/jsons/kernel_v5.9-rc2_v5.11-rc5.json -ofed_json_path /swgwork/royno/Full/Python_work_place/OfedProject/jsons/ofed5_2_2_for_demo.json -ofed_tag vmlnx-ofed-5.2-2.1.8 -kernel_start_tag v5.9-rc2 -kernel_end_tag v5.11-rc5 -output_filename analyzed_for_demo")
    parser.add_argument("-kernel", nargs='+', type=str, default="", required=True,
                        help="Path for KERNEL Json with pre-rebase process results")
    parser.add_argument("-ofed", type=str, default=None, required=True,
                        help="Path for OFED Json with pre-rebase process results")
    parser.add_argument("-diff", type=str, default=None, required=True,
                        help="Path for kernel function diff with Comperator results")
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
    file_list_verify = []
    file_list_verify.extend(args.kernel)
    file_list_verify.append(args.ofed)
    file_list_verify.append(args.diff)
    if not Verifier.checks_for_Analyzer(file_list_verify):
        logger.critical('Argument verify failed, exiting')
        exit(1)
    main_res, feature_to_function = Analyzer.pre_analyze_changed_method(
        args.kernel, args.ofed, args.diff)
    # pprint(feature_to_function)
    Analyzer.pre_create_changed_functions_excel(main_res, feature_to_function,
                                                'Feature_methods_changed' if
                                                args.output_filename is None else args.output_filename,
                                                args.kernel_start_tag, args.kernel_end_tag, args.ofed_tag)
    # Analyzer.function_modified_by_feature(args.ofed_json_path)
    # output1 = Comperator.extract_method_from_file('/tmp/en_main.c', 'mlx5e_alloc_rq')
    # output2 = Comperator.extract_method_from_file('/tmp/en_main2.c', 'mlx5e_alloc_rq')
    # with open('/tmp/o1.txt', 'w') as handle:
    #     handle.write(output1)
    # with open('/tmp/o2.txt', 'w') as handle:
    #     handle.write(output2)
    # Comperator.get_functions_diff_stats(output1, output2)
    # print(output1)
    # print('-----------')
    # print(output2)
    end_time = time.time()
    show_runtime(end_time, start_time)


if __name__ == '__main__':
    main()
