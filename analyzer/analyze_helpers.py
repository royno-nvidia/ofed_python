from datetime import datetime
import json
from typing import Tuple
import pandas as pd
import os

from utils.setting_utils import get_logger, EXCEL_LOC, JSON_LOC

logger = get_logger('Analyzer', 'Analyzer.log')


def colored_condition_column(workbook, worksheet, col: chr, col_len: int, red_zone: int, green_zone: int):
    """
    create 3 color condition in wanted col over worksheet
    :param workbook: xlsxlwriter workbook
    :param worksheet: xlsxwriter worksheet
    :param col: Excel col char (e.g 'A','B'..)
    :param col_len: number of rows in col
    :param red_zone: number which above it row will be colored in red
    :param green_zone: number which below it row will be colored in green
    :return:
    """
    # formatting
    red_format = workbook.add_format({'bg_color': '#FFC7CE',
                                      'font_color': '#9C0006'})
    yellow_format = workbook.add_format({'bg_color': '#FFEB9C',
                                         'font_color': '#9C6500'})
    green_format = workbook.add_format({'bg_color': '#C6EFCE',
                                        'font_color': '#006100'})
    worksheet.conditional_format(f'{col}3:{col}{col_len + 2}',
                                 {'type': 'cell',
                                  'criteria': '>=',
                                  'value': red_zone,
                                  'format': red_format})
    worksheet.conditional_format(f'{col}3:{col}{col_len + 2}',
                                 {'type': 'cell',
                                  'criteria': '<=',
                                  'value': green_zone,
                                  'format': green_format})
    worksheet.conditional_format(f'{col}3:{col}{col_len + 2}',
                                 {'type': 'cell',
                                  'criteria': 'between',
                                  'minimum': green_zone,
                                  'maximum': red_zone,
                                  'format': yellow_format})


def colored_condition_row(workbook, worksheet, col: chr, col_len: int):
    red_format = workbook.add_format({'bg_color': '#FFC7CE',
                                      'font_color': '#9C0006'})
    yellow_format = workbook.add_format({'bg_color': '#FFEB9C',
                                         'font_color': '#9C6500'})
    worksheet.conditional_format(f'A3:{col}{col_len + 2}',
                                 {'type': 'formula',
                                  'criteria': '=AND($G3+H3=0,$E3+FC3>0)',
                                  'format': red_format})


def create_diff_file_and_link(method_name: str, method_diff: str, directory: str):
    filename = f'{directory}/{method_name}.diff'
    if not os.path.isfile(filename):
        with open(filename, 'w') as handle:
            for line in method_diff:
                handle.write(line+'\n')
    hyperlink = f'=HYPERLINK("{os.path.basename(directory)}\{method_name}.diff","See Diff")'
    print(hyperlink)
    return hyperlink


def get_stat_or_none(method: str, info_dict :dict, stat: str):
    if method in info_dict.keys():
        return info_dict[method]['Stats'][stat]
    else:
        return ''


def update_current_feature_methods(res_dict: dict, iter_list: list, feature: str,
                                   info_dict: dict, dir_path: str, status: str):
    print(iter_list)
    for method in iter_list:
        method_diff = info_dict[method]['Diff'] if method in info_dict.keys() else 'Missing'
        res_dict[feature].append({
            "Feature name": feature,
            "Method": method,
            "Kernel status": status,
            "Diff": 'Missing' if method_diff == 'Missing'
            else create_diff_file_and_link(method, method_diff, dir_path),
            "Prototype changed": get_stat_or_none(method, info_dict, 'Prototype changed'),
            "Content changed": get_stat_or_none(method, info_dict, 'Content changed'),
            "Old function size": get_stat_or_none(method, info_dict, 'Old function size'),
            "New function size": get_stat_or_none(method, info_dict, 'New function size'),
            "Old function unique lines": get_stat_or_none(method, info_dict, 'Old function unique lines'),
            "New function unique lines": get_stat_or_none(method, info_dict, 'New function unique lines'),
            "Lines unchanged": get_stat_or_none(method, info_dict, 'Lines unchanged'),
            "Old function scope": get_stat_or_none(method, info_dict, 'Old function scope'),
            "New function scope": get_stat_or_none(method, info_dict, 'New function scope')
        })
    return res_dict


def  get_kernel_status(method, rm_list, ch_list):
    return "removed" if method in rm_list else "modified" if method in ch_list else "unchanged"


def post_update_excel_dict(iter_list: list, res_dict: dict, feature: str, rm_list: list, ch_list: list, status: str):
    for method in iter_list:
        kernel_status = get_kernel_status(method, rm_list, ch_list)
        res_dict[feature].append({
                                    "Feature name": feature,
                                    "Method": method,
                                    "Status": status,
                                    "Kernel Status": kernel_status
                                 })
    return res_dict
