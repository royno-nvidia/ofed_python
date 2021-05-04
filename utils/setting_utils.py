import logging
from colorlog import ColoredFormatter

# DEFINES
WORK_DAYS = 14
WIDTH = 0.5
TWO = 2
LOGGER_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/loggers/"
JSON_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/jsons/"
EXCEL_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/Excels/"
EXCEL_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/Excels/"

# RISK LEVELS
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


def risk_to_string(risk: int):
    if risk == LOW:
        return 'Low'
    if risk == MEDIUM:
        return 'Medium'
    if risk == HIGH:
        return 'High'
    if risk == SEVERE:
        return 'Severe'



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


