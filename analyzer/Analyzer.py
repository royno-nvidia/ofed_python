import json
import logging
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
    def analyze_changed_method(kernel_json: str, ofed_json: str) -> dict:
        res = {}
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
            removed_list =[]
            overall_methods = len(ofed_dict[feature])
            for method in ofed_dict[feature]:
                if method in kernel_dict['deleted'].keys():
                    if method not in removed_list:
                        removed_list.append(method)
                if method in kernel_dict['modified'].keys():
                    if method not in changed_list:
                        changed_list.append(method)
            res[feature] = {"Feature name": feature,
                            "Changed/Total": f"{len(changed_list)}/{overall_methods}",
                            "Change %": int((len(changed_list)/overall_methods)*100),
                            "Deleted/Total": f"{len(removed_list)}/{overall_methods}",
                            "Delete %": int((len(removed_list) / overall_methods) * 100),
                            "Methods changed": changed_list if len(changed_list) > 0 else "",
                            "Methods deleted": removed_list if len(removed_list) > 0 else ""}

        print(json.dumps(res, indent=4))
        return res

    @staticmethod
    def create_changed_functions_excel(results: dict, filename: str, src: str, dst: str, ofed: str):
        filename += '.xlsx'
        title = f"OFED {ofed} analyze for Kernel src {src} to kernel dst {dst}"
        df = pd.DataFrame([results[feature] for feature in results.keys()])
        df.set_index('Feature name')
        writer = pd.ExcelWriter(filename, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Analyzed_result', startrow=2, header=False, index=False)
        workbook = writer.book
        worksheet = writer.sheets['Analyzed_result']

        title_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#00E4BC',
            'border': 1})
        worksheet.merge_range(f'A1:{chr(ord("A")+len(df.columns)-1)}1', title, title_format)
        # header
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(1, col_num, value, header_format)

        # formatting
        red_format = workbook.add_format({'bg_color':   '#FFC7CE',
                                          'font_color': '#9C0006'})
        yellow_format = workbook.add_format({'bg_color':   '#FFEB9C',
                                             'font_color': '#9C6500'})
        green_format = workbook.add_format({'bg_color':   '#C6EFCE',
                                            'font_color': '#006100'})
        # apply conditions for modification
        worksheet.conditional_format(f'C3:C{len(df.index)+2}',
                                     {'type':     'cell',
                                      'criteria': '>=',
                                      'value':     30,
                                      'format':    red_format})
        worksheet.conditional_format(f'C3:C{len(df.index) + 2}',
                                     {'type':     'cell',
                                      'criteria': '<=',
                                      'value':     10,
                                      'format':    green_format})
        worksheet.conditional_format(f'C3:C{len(df.index) + 2}',
                                     {'type': 'cell',
                                      'criteria': 'between',
                                      'minimum': 10,
                                      'maximum': 30,
                                      'format': yellow_format})

        # apply conditions for deletions
        worksheet.conditional_format(f'E3:E{len(df.index) + 2}',
                                     {'type': 'cell',
                                      'criteria': '>=',
                                      'value': 15,
                                      'format': red_format})
        worksheet.conditional_format(f'E3:E{len(df.index) + 2}',
                                     {'type': 'cell',
                                      'criteria': '<=',
                                      'value': 0,
                                      'format': green_format})
        worksheet.conditional_format(f'E3:E{len(df.index) + 2}',
                                     {'type': 'cell',
                                      'criteria': 'between',
                                      'minimum': 0,
                                      'maximum': 15,
                                      'format': yellow_format})
        writer.save()
        logger.info(f"Excel {filename} was created in {os.path.abspath(filename)}")
