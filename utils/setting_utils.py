import logging
from colorlog import ColoredFormatter


class Status(object):
    SUCCESS = 0
    FAIL = 1


# DEFINES
LOGGER_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/loggers/"
JSON_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/jsons/"
EXCEL_LOC = "/swgwork/royno/Full/Python_work_place/OfedProject/Excels/"


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
