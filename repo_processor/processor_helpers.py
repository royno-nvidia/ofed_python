import json
import os
from utils.setting_utils import JSON_LOC, get_logger
from datetime import datetime

logger = get_logger('Processor', 'Processor.log')


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