import json
import logging
from typing import Tuple

from colorlog import ColoredFormatter
import pandas as pd
import xlsxwriter
import os

logger = logging.getLogger('Analyzer')
logger.setLevel(logging.DEBUG)
s_formatter = ColoredFormatter(
    '%(log_color)s%(asctime)s[%(filename)s +%(lineno)s] - %(levelname)s - %(message)s%(reset)s')
f_formatter = logging.Formatter('%(asctime)s[%(filename)s +%(lineno)s] - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('analyzer.log')
file_handler.setFormatter(f_formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(s_formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


class Analyzer(object):
    def __init__(self):
        """
        Init Analyzer, create instance of Analyzer can be used for static method calls
        """

    @staticmethod
    def analyze_changed_method(kernel_json: str, ofed_json: str) -> Tuple[dict, dict, dict]:
        main_res = {}
        feature_to_modified = {}
        feature_to_deleted = {}
        kernel_dict = {}
        ofed_dict = {}
        try:
            with open(kernel_json) as k_file:
                kernel_dict = json.load(k_file)
            with open(ofed_json) as o_file:
                ofed_dict = json.load(o_file)
        except IOError as e:
            logger.critical(f"failed to read json:\n{e}")
        for feature in ofed_dict.keys():
            changed_list = []
            removed_list = []
            # overall_methods = len(ofed_dict[feature][''])
            for method in ofed_dict[feature]['kernel']:
                if method in kernel_dict['deleted'].keys():
                    if method not in removed_list:
                        removed_list.append(method)
                if method in kernel_dict['modified'].keys():
                    if method not in changed_list:
                        changed_list.append(method)
            ofed_only_methods_num = len(ofed_dict[feature]['ofed_only'])
            kernel_methods_num = len(ofed_dict[feature]['kernel'])
            main_res[feature] = {"Feature name": feature,
                                 "Only OFED methods": ofed_only_methods_num,
                                 "Kernel methods": kernel_methods_num,
                                 # "Overall methods feature depend":
                                 #     ofed_only_methods_num + kernel_methods_num,
                                 "Changed in kernel": len(changed_list),
                                 "Changed % [comparison to kernel methods]":
                                     int((len(changed_list) / kernel_methods_num) * 100)
                                     if kernel_methods_num != 0 else 0,
                                 "Deleted from kernel": len(removed_list),
                                 "Deleted % [comparison to kernel methods]":
                                     int((len(removed_list) / kernel_methods_num) * 100)
                                     if kernel_methods_num != 0 else 0}
            feature_to_modified[feature] = [{"Feature name": feature,
                                            "Methods changed": method} for method in changed_list]
            feature_to_deleted[feature] = [{"Feature name": feature,
                                           "Methods deleted": method} for method in removed_list]

        return main_res, feature_to_modified, feature_to_deleted

    @staticmethod
    def create_changed_functions_excel(results: dict, modify: dict, delete: dict, filename: str, src: str, dst: str,
                                       ofed: str):
        filename += '.xlsx'
        title = f"OFED {ofed} analyze for Kernel src {src} to kernel dst {dst}"
        df_main = pd.DataFrame([results[feature] for feature in results.keys()])
        df_main.set_index('Feature name')
        writer = pd.ExcelWriter(filename, engine='xlsxwriter')
        df_main.to_excel(writer, sheet_name='Analyzed_result', startrow=2, header=False, index=False)

        workbook = writer.book
        worksheet = writer.sheets['Analyzed_result']

        title_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#00E4BC',
            'border': 1})
        worksheet.merge_range(f'A1:{chr(ord("A") + len(df_main.columns) - 1)}1', title, title_format)
        # header
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})
        for col_num, value in enumerate(df_main.columns.values):
            worksheet.write(1, col_num, value, header_format)

        # formatting
        red_format = workbook.add_format({'bg_color': '#FFC7CE',
                                          'font_color': '#9C0006'})
        yellow_format = workbook.add_format({'bg_color': '#FFEB9C',
                                             'font_color': '#9C6500'})
        green_format = workbook.add_format({'bg_color': '#C6EFCE',
                                            'font_color': '#006100'})
        # apply conditions for modification
        worksheet.conditional_format(f'E3:E{len(df_main.index) + 2}',
                                     {'type': 'cell',
                                      'criteria': '>=',
                                      'value': 30,
                                      'format': red_format})
        worksheet.conditional_format(f'E3:E{len(df_main.index) + 2}',
                                     {'type': 'cell',
                                      'criteria': '<=',
                                      'value': 10,
                                      'format': green_format})
        worksheet.conditional_format(f'E3:E{len(df_main.index) + 2}',
                                     {'type': 'cell',
                                      'criteria': 'between',
                                      'minimum': 10,
                                      'maximum': 30,
                                      'format': yellow_format})

        # apply conditions for deletions
        worksheet.conditional_format(f'G3:G{len(df_main.index) + 2}',
                                     {'type': 'cell',
                                      'criteria': '>=',
                                      'value': 15,
                                      'format': red_format})
        worksheet.conditional_format(f'G3:G{len(df_main.index) + 2}',
                                     {'type': 'cell',
                                      'criteria': '<=',
                                      'value': 0,
                                      'format': green_format})
        worksheet.conditional_format(f'G3:G{len(df_main.index) + 2}',
                                     {'type': 'cell',
                                      'criteria': 'between',
                                      'minimum': 0,
                                      'maximum': 15,
                                      'format': yellow_format})

        # Modified work sheet
        dicts_list_from_modify = [modify[feature][index] for
                                  feature in modify.keys() for index in range(len(modify[feature]))]
        df_mod = pd.DataFrame(dicts_list_from_modify)
        df_mod.set_index('Feature name')
        df_mod.to_excel(writer, sheet_name='Modified', startrow=1, header=False, index=False)
        worksheet_mod = writer.sheets['Modified']
        for col_num, value in enumerate(df_mod.columns.values):
            worksheet_mod.write(0, col_num, value, header_format)


        # Modified work sheet
        dicts_list_from_deleted = [delete[feature][index] for
                                  feature in delete.keys() for index in range(len(delete[feature]))]
        df_del = pd.DataFrame(dicts_list_from_deleted)
        df_del.set_index('Feature name')
        df_del.to_excel(writer, sheet_name='Deleted', startrow=1, header=False, index=False)
        worksheet_del = writer.sheets['Deleted']
        for col_num, value in enumerate(df_del.columns.values):
            worksheet_del.write(0, col_num, value, header_format)

        writer.save()
        logger.info(f"Excel {filename} was created in {os.path.abspath(filename)}")
