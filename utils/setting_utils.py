import logging
import datetime
import json
import os
import shutil
import subprocess
from colorlog import ColoredFormatter

# DEFINES
WORK_DAYS = 12
WIDTH = 0.5
TWO = 2
LOGGER_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/loggers/"
JSON_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/jsons"
EXCEL_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/Excels/"
EXCEL_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/Excels/"
TAB_SIZE = 4

# RISK LEVELS
NA = 5
REDESIGN = 4
SEVERE = 3
HIGH = 2
MEDIUM = 1
LOW = 0


def string_to_enum(risk: str):
    if risk == 'Low':
        return LOW
    if risk == 'Medium':
        return MEDIUM
    if risk == 'High':
        return HIGH
    if risk == 'Severe':
        return SEVERE
    if risk == 'Redesign':
        return REDESIGN
    if risk == 'NA':
        return NA


def risk_to_string(risk: int):
    if risk == LOW:
        return 'Low'
    if risk == MEDIUM:
        return 'Medium'
    if risk == HIGH:
        return 'High'
    if risk == SEVERE:
        return 'Severe'
    if risk == REDESIGN:
        return 'Redesign'
    if risk == NA:
        return 'NA'


def get_risk_mining(risk: int):
    if risk == LOW:
        return 'Low - Nothing changed in upstream functions (Patch should apply smoothly but ' \
               'compilation not guarantied)'
    if risk == MEDIUM:
        return 'Medium - Function\'s Body has new changes over upstream'
    if risk == HIGH:
        return 'High - Function\'s API changed (Only in case of Argument removal) in upstream'
    if risk == SEVERE:
        return 'Severe - Function REMOVED/MOVED/FILE RENAMED in upstream'
    if risk == REDESIGN:
        return 'Redesign - Feature need developer redesign'


def get_logger(module_name, file_name):
    """
    retuen logger instance for module
    :param module_name:
    :param file_name:
    :return:
    """
    logger = logging.getLogger(module_name)
    logger.setLevel(logging.DEBUG)
    s_formatter = ColoredFormatter(
        '%(log_color)s%(asctime)s[%(filename)s +%(lineno)s] - %(levelname)s - %(message)s%(reset)s')
    f_formatter = logging.Formatter('%(asctime)s[%(filename)s +%(lineno)s] - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler(LOGGER_LOC + file_name)
    file_handler.setFormatter(f_formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(s_formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def save_to_json(dict_for_saving, filename, directory=""):
    """
    Output process results into timestamp json file for future analyze
    :return:
    """
    if not filename.endswith('.json'):
        filename = f"{filename}.json"
    save_path = f'{directory}/{filename}'
    with open(f'{JSON_LOC}/{save_path}', 'w') as handle:
        json.dump(dict_for_saving, handle, indent=4)
    print(f"Results saved in Json - f'{JSON_LOC}/{save_path}'")
    return save_path


def combine_dicts(dict_list, filename):
    results = {}
    uniqe_keys = set()
    for js in dict_list:
        temp = open_json(js)
        uniqe_keys |= set(temp.keys())
        for key, value in temp.items():
            if key in results.keys() and value['Status'] == 'Modify':
                continue
            if key in results.keys() and results[key]['Status'] == 'Delete':
                continue
            results[key] = value
    print(f'Uniq keys = {len(uniqe_keys)}')
    return save_to_json(results, filename)


def open_json(json_name: str, directory=""):
    try:
        open_path = f"{JSON_LOC}/{directory}/{json_name}"
        if not os.path.isfile(open_path):
            print(f"File {open_path} - Not exists!")
            exit(1)
        with open(open_path) as j_file:
            data = json.load(j_file)
            return data
    except IOError as e:
        print(f"failed to read json - {open_path}:\n{e}")


def run_ofed_scripts(src_path: str, script: str, logger):
    cwd = os.getcwd()
    os.chdir(src_path)
    logger.debug(f'inside {os.getcwd()}')
    ret = subprocess.check_output(f'./ofed_scripts/{script}', shell=True)
    os.chdir(cwd)
    logger.debug(f'returned {os.getcwd()}')
    return ret


def show_runtime(end_time, start_time, logger):
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


def check_and_create_dir(loc, logger, remove=True):
    if os.path.exists(loc) and remove:
        shutil.rmtree(loc)
        logger.critical(f'Directory {loc} exists, remove automatically')
    os.mkdir(loc, 0o0755)
    logger.info(f'Directory {loc} created')