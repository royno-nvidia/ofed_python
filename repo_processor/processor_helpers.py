import json
import os

from Comperator.comperator_helpers import extract_method_from_file
from utils.setting_utils import JSON_LOC, get_logger
from datetime import datetime

logger = get_logger('Processor', 'Processor.log')


def verify_added_functions_status(all_tree_info: list, ofed_only_set: set):
    for index in range(0, len(all_tree_info)):
        # itarate all commits in tree
        for func in all_tree_info[index]['Functions']:
            if func in ofed_only_set:
                all_tree_info[index]['Functions'][func]['Status'] = 'Add'
                logger.debug(f"{func} moved status to 'Add'")
    return all_tree_info


def save_to_json(dict_for_saving, filename=None):
    """
    Output process results into timestamp json file for future analyze
    :return:
    """
    if filename is None:
        time_stamp = datetime.timestamp(datetime.now())
        filename = str(time_stamp)
    else:
        filename = f"{filename}.json"
    with open(JSON_LOC + filename, 'w') as handle:
        json.dump(dict_for_saving, handle, indent=4)
    logger.info(f"Results saved in Json - '{JSON_LOC + filename}'")


def get_actual_ofed_info(ofed_json):
    with open(JSON_LOC + ofed_json) as handle:
        ofed_modified_methods_dict = json.load(handle)
        actual_ofed_functions_modified = set()
        for commit in ofed_modified_methods_dict:
            actual_ofed_functions_modified |= set(commit['Functions'].keys())
        return actual_ofed_functions_modified


def extract_function(kernel_path, func_location, func, prefix):
    ext_func = ""
    fpath = f"{kernel_path}/{func_location}"
    if not os.path.exists(fpath):
        logger.warn(f"{prefix}: FIle not exist: {fpath}")
    else:
        ext_func = extract_method_from_file(fpath, func)
        if ext_func is None:
            logger.warn(f"{prefix}: Failed to find {func} in file {fpath}")
    return ext_func