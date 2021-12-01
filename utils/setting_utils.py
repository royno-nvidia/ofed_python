import logging
import datetime
import json
from colorlog import ColoredFormatter

# DEFINES
WORK_DAYS = 12
WIDTH = 0.5
TWO = 2
LOGGER_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/loggers/"
JSON_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/jsons/"
EXCEL_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/Excels/"
EXCEL_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/Excels/"

# RISK LEVELS
NA = 5
REDESIGN = 4
SEVERE = 3
HIGH = 2
MEDIUM = 1
LOW = 0

class Status(object):
    SUCCESS = 0
    FAIL = 1


def string_to_enum(risk: str):
    if risk == 'Low':
        return LOW
    if risk == 'Medium':
        return MEDIUM
    if risk == 'High':
        return HIGH
    if risk == 'Severe':
        return SEVERE
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
    if risk == NA:
        return 'NA'




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


def save_to_json(dict_for_saving, filename=None):
    """
    Output process results into timestamp json file for future analyze
    :return:
    """
    if filename is None:
        time_stamp = datetime.timestamp(datetime.now())
        filename = f'{str(time_stamp)}.json'
    else:
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
    with open(JSON_LOC + filename, 'w') as handle:
        json.dump(dict_for_saving, handle, indent=4)
    print(f"Results saved in Json - '{JSON_LOC + filename}'")
    return filename


def open_json(json_name: str):
    try:
        path = JSON_LOC + json_name
        with open(JSON_LOC + json_name) as j_file:
            data = json.load(j_file)
            return data
    except IOError as e:
        print(f"failed to read json - {path}:\n{e}")


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