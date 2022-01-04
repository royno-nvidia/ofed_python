
import argparse
import time
from analyzer.Analyzer import Analyzer
from repo_processor.Processor import Processor, run_ofed_scripts
from utils.setting_utils import show_runtime
from verifier.verifer_arg import *

logger = get_logger('Analyzer', 'Analyzer.log')


def parse_args():
    parser = argparse.ArgumentParser(description="OFED pre-rebase prediction scrip\n")
    parser.add_argument("-kernel_json", type=str, default=None, required=True,
                        help="Path for KERNEL Json with pre-rebase process results")
    parser.add_argument("-ofed_json", type=str, default=None, required=True,
                        help="Path for OFED Json with pre-rebase process results")
    parser.add_argument("-osrc", type=str, default="", required=True,
                        help="Linus repository checkout at source version")
    parser.add_argument("-ksrc", type=str, default="", required=True,
                        help="Linus repository checkout at source version")
    parser.add_argument("-kdst", type=str, default=None, required=True,
                        help="Linus repository checkout at destination version")
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
    loc = Processor.get_kernels_methods_diffs(args)

    # # Get OFED function in version end
    ext_loc = Processor.extract_ofed_functions(args.osrc, args.ofed_json, args.output, False)
    # run_ofed_scripts(args.osrc, 'ofed_patch.sh')
    # # Get OFED function in version end with backports
    back_loc = Processor.extract_ofed_functions(args.osrc, args.ofed_json, args.output, True)
    # run_ofed_scripts(args.osrc, 'cleanup')

    # Excel data analyze
    main_res, commit_to_function = Analyzer.build_commit_dicts(
        args.kernel_json, args.ofed_json, loc, ext_loc, back_loc, args.output)

    # Excel workbook creation
    Analyzer.create_colored_tree_excel(main_res, commit_to_function,
                                       args.output, args.kernel_start_tag,
                                       args.kernel_end_tag, args.ofed_tag)
    end_time = time.time()
    show_runtime(end_time, start_time, logger)


if __name__ == '__main__':
    main()
