import logging
from colorlog import ColoredFormatter

# DEFINES
LOGGER_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/loggers/"
JSON_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/jsons/"
EXCEL_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/Excels/"
EXCEL_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/Excels/"

# RISK LEVELS
HIGH = 3
MEDIUM = 2
LOW = 1
NO = 0


class Status(object):
    SUCCESS = 0
    FAIL = 1


def string_to_enum(risk: str):
    if risk == 'No Risk':
        return NO
    if risk == 'Low':
        return LOW
    if risk == 'Medium':
        return MEDIUM
    if risk == 'High':
        return HIGH


def risk_to_string(risk: int):
    if risk == NO:
        return 'No Risk'
    if risk == LOW:
        return 'Low'
    if risk == MEDIUM:
        return 'Medium'
    if risk == HIGH:
        return 'High'


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


