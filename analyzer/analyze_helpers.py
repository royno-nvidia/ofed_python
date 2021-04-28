from datetime import datetime
import json
from typing import Tuple
import pandas as pd
import os

from utils.setting_utils import get_logger, EXCEL_LOC, JSON_LOC

logger = get_logger('Analyzer', 'Analyzer.log')


def colored_condition_column(workbook, worksheet, col: chr, col_len: int):
                             #red_zone: int, green_zone: int):
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
                                      'font_color': '#FFC7CE'})
    yellow_format = workbook.add_format({'bg_color': '#FFEB9C',
                                         'font_color': '#FFEB9C'})
    green_format = workbook.add_format({'bg_color': '#C6EFCE',
                                        'font_color': '#C6EFCE'})
    orange_format = workbook.add_format({'bg_color': '#FFA500',
                                        'font_color': '#FFA500'})
    worksheet.conditional_format(f'{col}3:{col}{col_len + 2}',
                                 {'type': 'cell',
                                  'criteria': '==',
                                  'value': 0,
                                  'format': green_format})
    worksheet.conditional_format(f'{col}3:{col}{col_len + 2}',
                                 {'type': 'cell',
                                  'criteria': '==',
                                  'value': 1,
                                  'format': yellow_format})
    worksheet.conditional_format(f'{col}3:{col}{col_len + 2}',
                                 {'type': 'cell',
                                  'criteria': '==',
                                  'value': 2,
                                  'format': orange_format})
    worksheet.conditional_format(f'{col}3:{col}{col_len + 2}',
                                 {'type': 'cell',
                                  'criteria': '==',
                                  'value': 3,
                                  'format': red_format})

    # worksheet.conditional_format(f'{col}3:{col}{col_len + 2}',
    #                              {'type': 'cell',
    #                               'criteria': '>=',
    #                               'value': red_zone,
    #                               'format': red_format})
    # worksheet.conditional_format(f'{col}3:{col}{col_len + 2}',
    #                              {'type': 'cell',
    #                               'criteria': '<=',
    #                               'value': green_zone,
    #                               'format': green_format})
    # worksheet.conditional_format(f'{col}3:{col}{col_len + 2}',
    #                              {'type': 'cell',
    #                               'criteria': 'between',
    #                               'minimum': green_zone,
    #                               'maximum': red_zone,
    #                               'format': yellow_format})


def colored_condition_row(workbook, worksheet, col: chr, col_len: int):
    red_format = workbook.add_format({'bg_color': '#FFC7CE',
                                      'font_color': '#9C0006'})
    yellow_format = workbook.add_format({'bg_color': '#FFEB9C',
                                         'font_color': '#9C6500'})
    worksheet.conditional_format(f'A3:{col}{col_len + 2}',
                                 {'type': 'formula',
                                  'criteria': '=AND($G3+H3=0,$E3+FC3>0)',
                                  'format': red_format})


def create_diff_file_and_link(method_name: str, info_dict: str, directory: str):
    if method_name not in info_dict.keys():
        return 'NA'
    if info_dict[method_name]['Diff'] == 'NA':
        return 'NA'
    method_diff = info_dict[method_name]['Diff']
    filename = f'{directory}/{method_name}.diff'
    if not os.path.isfile(filename):
        with open(filename, 'w') as handle:
            for line in method_diff:
                handle.write(line+'\n')
    hyperlink = f'=HYPERLINK("{os.path.basename(directory)}\{method_name}.diff","See Diff")'
    print(hyperlink)
    return hyperlink


def get_stat_or_none(method: str, info_dict :dict, stat: str):
    if method in info_dict.keys() and info_dict[method]['Stats'][stat] != 'NA':
        return info_dict[method]['Stats'][stat]
    else:
        return ''


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
