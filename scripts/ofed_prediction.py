
import argparse
import datetime
import time
from analyzer.Analyzer import Analyzer
from repo_processor.Processor import Processor
from verifier.verifer_arg import *

logger = get_logger('Analyzer', 'Analyzer.log')


def parse_args():
    parser = argparse.ArgumentParser(description="OFED pre-rebase analyzer\n"
                                                 "E.G: -kernel_json_path /swgwork/royno/Full/Python_work_place/OfedProject/jsons/kernel_v5.9-rc2_v5.11-rc5.json -ofed_json_path /swgwork/royno/Full/Python_work_place/OfedProject/jsons/ofed5_2_2_for_demo.json -ofed_tag vmlnx-ofed-5.2-2.1.8 -kernel_start_tag v5.9-rc2 -kernel_end_tag v5.11-rc5 -output_filename analyzed_for_demo")
    parser.add_argument("-kernel_json", type=str, default=None, required=True,
                        help="Path for KERNEL Json with pre-rebase process results")
    parser.add_argument("-ofed_json", type=str, default=None, required=True,
                        help="Path for OFED Json with pre-rebase process results")
    # parser.add_argument("-diff", type=str, default=None, required=True,
    #                     help="Path for kernel function diff with Comperator results")
    parser.add_argument("-osrc", type=str, default="", required=True,
                        help="Linus repository checkout at source version")
    parser.add_argument("-ksrc", type=str, default="", required=True,
                        help="Linus repository checkout at source version")
    parser.add_argument("-kdst", type=str, default=None, required=True,
                    help="Linus repository checkout at source version")
    # parser.add_argument("-ofed_extracted_functions", type=str, default=None, required=True,
    #                     help="Path for OFED extracted last version functions")
    parser.add_argument("-ofed_tag", type=str, default="", required=True,
                        help="OFED version tag processed")
    parser.add_argument("-kernel_start_tag", type=str, default="", required=True,
                        help="Kernel version start tag processed")
    parser.add_argument("-kernel_end_tag", type=str, default="", required=True,
                        help="Kernel version end tag processed")
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
    file_list_verify = []
    file_list_verify.extend(args.kernel_json)
    file_list_verify.append(args.ofed_json)
    # file_list_verify.append(args.diff)
    # file_list_verify.append(args.ofed_extracted_functions)
    if not checks_for_Analyzer(file_list_verify, args.output):
        logger.critical('Argument verify failed, exiting')
        exit(1)
    # create methods diff stats
    diff_location = Processor.get_kernels_methods_diffs(args.ksrc, args.kdst,
                                        args.kernel_json,
                                        args.output,
                                        args.ofed_json)

    # Get OFED function in version end
    ext_loc = Processor.extract_ofed_functions(args.osrc, args.ofed_json, args.output, False)
    #ofed_appliy_patches(args.src)
    # Get OFED function in version end with backports
    # Processor.extract_ofed_functions(args.src, args.ofed_methods_info, args.output, True)

    # Excel data analyze
    main_res, commit_to_function = Analyzer.build_commit_dicts(
        args.kernel_json, args.ofed_json, diff_location, ext_loc, args.output)

    # Excel workbook creation
    Analyzer.create_colored_tree_excel(main_res, commit_to_function,
                                       args.output, args.kernel_start_tag,
                                       args.kernel_end_tag, args.ofed_tag)
    end_time = time.time()
    show_runtime(end_time, start_time)


if __name__ == '__main__':
    main()
