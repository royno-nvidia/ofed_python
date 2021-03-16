import json
import logging
import pprint
from typing import Tuple
from colorlog import ColoredFormatter
import pandas as pd
import xlsxwriter
import os
from utils.setting_utils import get_logger, EXCEL_LOC, JSON_LOC

logger = get_logger('Analyzer', 'Analyzer.log')


class Analyzer(object):
    def __init__(self):
        """
        Init Analyzer, create instance of Analyzer can be used for static method calls
        """

    @staticmethod
    def combine_kernel_dicts(kernel_jsons) -> dict:
        """
        Create one combined dictionary for all kernels json list files
        :param kernel_jsons: list of kernel jsons
        :return: combined dictionary
        """
        res_dict = {"modified": {}, "deleted": {}}
        modified_set = set()
        deleted_set = set()

        try:
            for j_file in kernel_jsons:
                with open(JSON_LOC+j_file) as k_file:
                    kernel_dict = json.load(k_file)
                    modified_set |= set(kernel_dict['modified'].keys())
                    deleted_set |= set(kernel_dict['deleted'].keys())
                    modified_set -= deleted_set # remove duplications
        except IOError as e:
            logger.critical(f"failed to read json:\n{e}")
        res_dict['modified'] = dict.fromkeys(modified_set, 0)
        res_dict['deleted'] = dict.fromkeys(deleted_set, 0)
        # with open(JSON_LOC+'check_combiner2.json', 'w') as handle:
        #     json.dump(res_dict, handle, indent=4)
        return res_dict


    @staticmethod
    def pre_analyze_changed_method(kernel_json, ofed_json: str) -> Tuple[dict, dict, dict]:
        """
        Take processor Json's output and analyze result, build data for Excel display
        :param kernel_json:
        :param ofed_json:
        :return:
        """
        main_res = {}
        feature_to_modified = {}
        feature_to_deleted = {}
        feature_to_function = {}
        kernel_dict = Analyzer.combine_kernel_dicts(kernel_json)
        ofed_dict = {}
        try:
            with open(JSON_LOC+ofed_json) as o_file:
                ofed_dict = json.load(o_file)
        except IOError as e:
            logger.critical(f"failed to read json:\n{e}")
        for feature in ofed_dict.keys():
            changed_set = set()
            removed_set = set()
            # overall_methods = len(ofed_dict[feature][''])
            for method in ofed_dict[feature]['kernel']:
                if method in kernel_dict['deleted'].keys():
                    removed_set.add(method)
                if method in kernel_dict['modified'].keys():
                    changed_set.add(method)
            changed_set -= removed_set
            ofed_only_methods_num = len(ofed_dict[feature]['ofed_only'])
            kernel_methods_num = len(ofed_dict[feature]['kernel'])
            main_res[feature] = {"Feature name": feature,
                                 "OFED only methods": ofed_only_methods_num,
                                 "Kernel methods": kernel_methods_num,
                                 # "Overall methods feature depend":
                                 #     ofed_only_methods_num + kernel_methods_num,
                                 "Changed in kernel": len(changed_set),
                                 "Changed % [comparison to kernel methods]":
                                     int((len(changed_set) / kernel_methods_num) * 100)
                                     if kernel_methods_num != 0 else 0,
                                 "Deleted from kernel": len(removed_set),
                                 "Deleted % [comparison to kernel methods]":
                                     int((len(removed_set) / kernel_methods_num) * 100)
                                     if kernel_methods_num != 0 else 0}
            if len(removed_set) or len(changed_set):
                feature_to_function[feature] = []
                for rem in list(removed_set):
                    feature_to_function[feature].append({
                                                "Feature name": feature,
                                                "Method": rem,
                                                "Status": "removed"})
                for mod in list(changed_set):
                    feature_to_function[feature].append({
                                                "Feature name": feature,
                                                "Method": mod,
                                                "Status": "modified"})
                for oo in ofed_dict[feature]['ofed_only']:
                    feature_to_function[feature].append({
                        "Feature name": feature,
                        "Method": oo,
                        "Status": "ofed only"})
                unchhanged_set = set(ofed_dict[feature]['kernel'])
                unchhanged_set = unchhanged_set.difference(changed_set, removed_set)
                for unchanged in list(unchhanged_set):
                    feature_to_function[feature].append({
                        "Feature name": feature,
                        "Method": unchanged,
                        "Status": "unchanged"})
                print(feature_to_function[feature])
            # modified_list = [{"Feature name": feature,
            #                                  "Method": method, "Status": "modified"} for method in list(changed_set)]
            # removed_list = [{"Feature name": feature,
            #                                  "Method": method, "Status": "removed"} for method in list(removed_set)]

            # feature_to_function[feature] = modified_list.extend(removed_list)
            # print(feature_to_function[feature])
            # feature_to_function[feature] = [{"Feature name": feature,
            #                                  "Method": method, "Status": "modified"} for method in changed_set]
            # feature_to_function[feature].append([{"Feature name": feature,
            #                                  "Methods": method, "Status": "modified"} for method in changed_set])
            # feature_to_modified[feature] = [{"Feature name": feature,
            #                                  "Methods changed": method, "Status": "modified"} for method in changed_set]
            # feature_to_deleted[feature] = [{"Feature name": feature,
            #                                 "Methods deleted": method} for method in removed_set]

        # return main_res, feature_to_modified, feature_to_deleted
        return main_res, feature_to_function

    @staticmethod
    def post_analyze_changed_method(kernel_json: str, new_ofed_json: str, old_ofed_json: str):

        main_res = {}
        kernel_modified = {}
        only_new_methods = {}
        only_old_methods = {}
        modified_in_kernel = {}
        kernel_dict = {}
        new_ofed_dict = {}
        old_ofed_dict = {}
        try:
            with open(kernel_json) as k_file:
                kernel_dict = json.load(k_file)
            with open(old_ofed_json) as o_file:
                old_ofed_dict = json.load(o_file)
            with open(new_ofed_json) as n_file:
                new_ofed_dict = json.load(n_file)
        except IOError as e:
            logger.critical(f"failed to read json:\n{e}")
        # newly added features
        new_features = list(set(new_ofed_dict.keys()) - set(old_ofed_dict.keys()))
        # accepted/abandon features
        old_features = list(set(old_ofed_dict.keys()) - set(new_ofed_dict.keys()))
        combine_features = list(set(old_ofed_dict.keys()).intersection(set(new_ofed_dict.keys())))
        for feature in combine_features:
            changed_list = []
            removed_list = []
            function_modified_in_new = [method for method in new_ofed_dict[feature]['kernel']]
            function_modified_in_old = [method for method in old_ofed_dict[feature]['kernel']]
            has_changes = False
            for method in function_modified_in_old:
                if method in kernel_dict['deleted'].keys():
                    if method not in removed_list:
                        removed_list.append(method)
                        has_changes = True
                if method in kernel_dict['modified'].keys():
                    if method not in changed_list:
                        changed_list.append(method)
                        has_changes = True
            only_new_methods = list(set(function_modified_in_new) - set(function_modified_in_old))
            only_old_methods = list(set(function_modified_in_old) - set(function_modified_in_new))
            overlapping_methods = list(set(function_modified_in_new).intersection(set(function_modified_in_old)))
            main_res[feature] = {"Feature name": feature,
                                 "Old OFED version methods dependencies": len(only_old_methods) + len(overlapping_methods),
                                 "New OFED version methods dependencies": len(only_new_methods) + len(overlapping_methods),
                                 "Overlapping methods dependencies": len(overlapping_methods),
                                 "Added methods dependencies": len(only_new_methods),
                                 "Missing methods dependencies": len(only_old_methods),
                                 "Modified methods in kernel": len(changed_list),
                                 "Removed methods from kernel": len(removed_list)}

            # kernel_modified[feature] = [{"Feature name": feature,
            #                                  "Methods changed": method} for method in changed_list]
            # feature_to_deleted[feature] = [{"Feature name": feature,
            #                                 "Methods deleted": method} for method in removed_list]
            has_changes = False
        return main_res

    @staticmethod
    def __colored_condition_row(workbook, worksheet, col: chr, col_len: int):
        red_format = workbook.add_format({'bg_color': '#FFC7CE',
                                          'font_color': '#9C0006'})
        yellow_format = workbook.add_format({'bg_color': '#FFEB9C',
                                             'font_color': '#9C6500'})
        worksheet.conditional_format(f'A3:{col}{col_len+2}',
                                     {'type':     'formula',
                                      'criteria': '=AND($G3+H3=0,$E3+FC3>0)',
                                      'format':   red_format})


    @staticmethod
    def __colored_condition_column(workbook, worksheet, col: chr, col_len: int, red_zone: int, green_zone: int):
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


    @staticmethod
    def pre_create_changed_functions_excel(results: dict, feature_to_functiom: dict, filename: str, src: str, dst: str,
                                           ofed: str):
        """
        Build excel file from analyzed results
        :param results: dict contain result for main page
        :param modify:  dict contain which features methods was modified in kernel
        :param delete: dict contain which features methods was deleted in kernel
        :param filename: name for output excel file
        :param src: kernel source version tag
        :param dst: kernel destination version tag
        :param ofed: Ofed specific tag
        :return:
        """
        title = f"MSR Analyze [OFED: {ofed} | Kernel src: {src} | kernel dst: {dst}]"
        df_main = pd.DataFrame([results[feature] for feature in results.keys()])
        df_main.set_index('Feature name')
        writer = pd.ExcelWriter(EXCEL_LOC + filename + '.xlsx', engine='xlsxwriter')
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

        # apply conditions for modification
        Analyzer.__colored_condition_column(workbook, worksheet, 'E', len(df_main.index), 30, 10)
        # apply conditions for deletions
        Analyzer.__colored_condition_column(workbook, worksheet, 'G', len(df_main.index), 15, 0)
        print("check")
        print(feature_to_functiom)
        # Modified worksheet
        dicts_list_from_modify = [feature_to_functiom[feature][index] for
                                  feature in feature_to_functiom.keys() for
                                  index in range(len(feature_to_functiom[feature]))]

        df_mod = pd.DataFrame(dicts_list_from_modify)
        df_mod.set_index('Feature name')
        df_mod.to_excel(writer, sheet_name='Feature function status', startrow=1, header=False, index=False)
        worksheet_mod = writer.sheets['Feature function status']
        for col_num, value in enumerate(df_mod.columns.values):
            worksheet_mod.write(0, col_num, value, header_format)

        # # deleted worksheet
        # dicts_list_from_deleted = [delete[feature][index] for
        #                            feature in delete.keys() for index in range(len(delete[feature]))]
        # df_del = pd.DataFrame(dicts_list_from_deleted)
        # df_del.set_index('Feature name')
        # df_del.to_excel(writer, sheet_name='Deleted', startrow=1, header=False, index=False)
        # worksheet_del = writer.sheets['Deleted']
        # for col_num, value in enumerate(df_del.columns.values):
        #     worksheet_del.write(0, col_num, value, header_format)

        writer.save()
        logger.info(f"Excel {filename} was created in {os.path.abspath(filename)}")

    @staticmethod
    def post_create_changed_functions_excel(results: dict, modify: dict, delete: dict,
                                            filename: str, src: str, dst: str, ofed: str):
        """
        Build excel file from analyzed results
        :param results: dict contain result for main page
        :param modify:  dict contain which features methods was modified in kernel
        :param delete: dict contain which features methods was deleted in kernel
        :param filename: name for output excel file
        :param src: kernel source version tag
        :param dst: kernel destination version tag
        :param ofed: Ofed specific tag
        :return:
        """

        title = f"MSR Analyze [OFED: {ofed} | Kernel src: {src} | kernel dst: {dst}]"

        df_main = pd.DataFrame([results[feature] for feature in results.keys()])
        df_main.set_index('Feature name')
        writer = pd.ExcelWriter(EXCEL_LOC + filename + '.xlsx', engine='xlsxwriter')
        df_main.to_excel(writer, sheet_name='Analyzed_result', startrow=2, header=False, index=False)

        workbook = writer.book
        worksheet = writer.sheets['Analyzed_result']

        title_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#00E4BC',
            'border': 1})
        red_format = workbook.add_format({'bg_color': '#FFC7CE',
                                          'font_color': '#9C0006'})
        worksheet.merge_range(f'A1:{chr(ord("A") + len(df_main.columns) - 1)}1', title, title_format)
        Analyzer.__colored_condition_row(workbook, worksheet, 'H', len(df_main.index))
        # header
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})
        for col_num, value in enumerate(df_main.columns.values):
            worksheet.write(1, col_num, value, header_format)

        # apply conditions for modification
        # Analyzer.__colored_condition_column(workbook, worksheet, 'E', len(df_main.index), 30, 10)
        # apply conditions for deletions
        # Analyzer.__colored_condition_column(workbook, worksheet, 'G', len(df_main.index), 15, 0)

        # Modified worksheet
        # dicts_list_from_modify = [modify[feature][index] for
        #                           feature in modify.keys() for
        #                           index in range(len(modify[feature]))]
        # df_mod = pd.DataFrame(dicts_list_from_modify)
        # df_mod.set_index('Feature name')
        # df_mod.to_excel(writer, sheet_name='Modified', startrow=1, header=False, index=False)
        # worksheet_mod = writer.sheets['Modified']
        # for col_num, value in enumerate(df_mod.columns.values):
        #     worksheet_mod.write(0, col_num, value, header_format)
        #
        # # deleted worksheet
        # dicts_list_from_deleted = [delete[feature][index] for
        #                            feature in delete.keys() for index in range(len(delete[feature]))]
        # df_del = pd.DataFrame(dicts_list_from_deleted)
        # df_del.set_index('Feature name')
        # df_del.to_excel(writer, sheet_name='Deleted', startrow=1, header=False, index=False)
        # worksheet_del = writer.sheets['Deleted']
        # for col_num, value in enumerate(df_del.columns.values):
        #     worksheet_del.write(0, col_num, value, header_format)

        writer.save()
        logger.info(f"Excel {filename} was created in {os.path.abspath(filename)}")
