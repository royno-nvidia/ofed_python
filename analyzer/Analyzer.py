from datetime import datetime
import json
from pprint import pprint

import pandas as pd
import os


from analyzer.analyze_helpers import colored_condition_column, colored_condition_row, \
    post_update_excel_dict, get_stat_or_none, create_diff_file_and_link
from utils.setting_utils import get_logger, EXCEL_LOC, JSON_LOC, RiskLevel, string_to_enum

logger = get_logger('Analyzer', 'Analyzer.log')


def create_main_dict(kernel_dict, ofed_list, diff_dict):
    main_res = []

    for commit in ofed_list:
        commit_risk = 0
        for func in commit['Functions']:
            if func in diff_dict.keys():
                commit_risk = max(commit_risk, string_to_enum(diff_dict[func]['Stats']['Risk']))
            else:
                logger.warn(f'{func} - not in dict, missing info')
        main_res.append({
            "Hash": commit['Hash'],
            "Subject": commit['Subject'],
            "Risk Level": commit_risk,
            "Feature": commit['Feature'],
            "Status": commit['Status'],
            "Change-Id": commit['Change-Id'],
            "Author": commit['Author']
        })
    return main_res

def create_func_stats_line(func_name, chash, diff_dict, dir_path):
    ret_stats = {
        "Hash": chash,
        "Function": func_name,
        "Diff": create_diff_file_and_link(func_name, diff_dict, dir_path),
        "Removed": get_stat_or_none(func_name, diff_dict,'Removed'),
        "Prototype changed": get_stat_or_none(func_name, diff_dict, 'Prototype changed'),
        "Content changed": get_stat_or_none(func_name, diff_dict, 'Content changed'),
        "Old function size": get_stat_or_none(func_name, diff_dict, 'Old function size'),
        "New function size": get_stat_or_none(func_name, diff_dict, 'New function size'),
        "Old function unique lines": get_stat_or_none(func_name, diff_dict, 'Old function unique lines'),
        "New function unique lines": get_stat_or_none(func_name, diff_dict, 'New function unique lines'),
        "Lines unchanged": get_stat_or_none(func_name, diff_dict, 'Lines unchanged'),
        "Old function scope": get_stat_or_none(func_name, diff_dict, 'Old function scope'),
        "New function scope": get_stat_or_none(func_name, diff_dict, 'New function scope')
    }
    return ret_stats


def create_commit_to_function_dict(ofed_list, diff_dict, dir_path):
    feature_to_function = []
    for commit in ofed_list:
        for func in commit['Functions'].keys():
            feature_to_function.append(create_func_stats_line(func, commit['Hash'], diff_dict, dir_path))
    return feature_to_function



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
        res_dict = {}
        try:
            for j_file in kernel_jsons:
                with open(JSON_LOC+j_file) as k_file:
                    kernel_dict = json.load(k_file)
                    for func, info in kernel_dict.items():
                        if func not in res_dict.keys():
                            res_dict[func] = info
        except IOError as e:
            logger.critical(f"failed to read json:\n{e}")
        return res_dict

    @staticmethod
    def function_modified_by_feature(ofed_json: str) -> dict:
        res_dict = {}
        ofed_dict = {}
        try:
            with open(JSON_LOC+ofed_json) as o_file:
                ofed_dict = json.load(o_file)
        except IOError as e:
            logger.critical(f"failed to read json:\n{e}")
        for feature in ofed_dict.keys():
            logger.debug(f'feature: {feature}')
            if feature == 'rebase':
                continue
            for method in ofed_dict[feature]['kernel']:
                if method not in res_dict.keys():
                    res_dict[method] = {'feature_list': [], 'counter': 1}
                    res_dict[method]['feature_list'].append(feature)
                    # res_dict[method]['count'] = 1
                else:
                    res_dict[method]['feature_list'].append(feature)
                    res_dict[method]['counter'] = res_dict[method]['counter'] + 1
        filename = 'function_to_feature'
        with open(JSON_LOC + filename, 'w') as handle:
            json.dump(res_dict, handle, indent=4)




    @staticmethod
    def pre_analyze_changed_method(kernel_json: str, ofed_json: str, diff_json: str, output: str):
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
            with open(JSON_LOC + diff_json) as d_file:
                diff_dict = json.load(d_file)
        except IOError as e:
            logger.critical(f"failed to read json:\n{e}")
        dir_name = str(datetime.timestamp(datetime.now()))
        dir_path = f"{EXCEL_LOC + output}"
        os.mkdir(dir_path, 0o0755)
        for feature in ofed_dict.keys():
            print(f'featur: {feature}')
            changed_set = set()
            removed_set = set()
            uniq_new = 0
            uniq_old = 0
            # overall_methods = len(ofed_dict[feature][''])
            for method in ofed_dict[feature]['kernel']:
                if method in kernel_dict['deleted'].keys():
                    removed_set.add(method)
                if method in kernel_dict['modified'].keys():
                    changed_set.add(method)
                    if method in diff_dict.keys():
                        uniq_new += diff_dict[method]['Stats']['New function unique lines']
                        uniq_old += diff_dict[method]['Stats']['Old function unique lines']
                    else:
                        logger.warn(f"Missing Info: method - {method} | feature - {feature}")
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
                                     if kernel_methods_num != 0 else 0,
                                 "Old lines unique": uniq_old,
                                 "New lines unique": uniq_new
                                 }
            if feature not in feature_to_function.keys():
                feature_to_function[feature] = []
            if removed_set:
                feature_to_function = update_current_feature_methods(feature_to_function, list(removed_set),
                                                                     feature, diff_dict,dir_path, 'Removed')
            if changed_set:
                feature_to_function = update_current_feature_methods(feature_to_function, list(changed_set),
                                                                     feature, diff_dict, dir_path, 'Changed')
            if len(ofed_dict[feature]['ofed_only']):
                feature_to_function = update_current_feature_methods(feature_to_function, ofed_dict[feature]['ofed_only'],
                                                                     feature, diff_dict, dir_path, 'OFED added')
            unchanged_set = set(ofed_dict[feature]['kernel'])
            unchanged_set = unchanged_set.difference(changed_set, removed_set)
            if unchanged_set:
                feature_to_function = update_current_feature_methods(feature_to_function, list(unchanged_set),
                                                                     feature, diff_dict, dir_path, 'Unchanged')
        return main_res, feature_to_function

    @staticmethod
    def build_commit_dicts(kernel_json: str, ofed_json: str, diff_json: str, output: str):
        """
        Take processor Json's output and analyze result, build data for Excel display
        :return:
        """
        kernel_dict = Analyzer.combine_kernel_dicts(kernel_json)
        commit_list = []
        try:
            with open(JSON_LOC + ofed_json) as o_file:
                commit_list = json.load(o_file)
            with open(JSON_LOC + diff_json) as d_file:
                diff_dict = json.load(d_file)
        except IOError as e:
            logger.critical(f"failed to read json:\n{e}")
        main_res = create_main_dict(kernel_dict, commit_list, diff_dict)
        dir_path = f"{EXCEL_LOC + output}"
        os.mkdir(dir_path, 0o0755)
        commit_to_function = create_commit_to_function_dict(commit_list, diff_dict, dir_path)
        return main_res, commit_to_function


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
        feature_function_status = {}
        kernel_filename = []
        kernel_filename.append(kernel_json)
        kernel_dict = Analyzer.combine_kernel_dicts(kernel_filename)
        try:
            with open(JSON_LOC+old_ofed_json) as o_file:
                old_ofed_dict = json.load(o_file)
            with open(JSON_LOC+new_ofed_json) as n_file:
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
            for method in function_modified_in_old:
                if method in kernel_dict['deleted'].keys():
                    if method not in removed_list:
                        removed_list.append(method)
                if method in kernel_dict['modified'].keys():
                    if method not in changed_list:
                        changed_list.append(method)
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
            if len(only_old_methods) or len(only_new_methods) or len(overlapping_methods) or len(changed_list) or len(removed_list):
                feature_function_status[feature] = []
                feature_function_status = post_update_excel_dict(only_new_methods, feature_function_status,
                                                                 feature, removed_list, changed_list, 'Add')
                feature_function_status = post_update_excel_dict(only_old_methods, feature_function_status,
                                                                 feature, removed_list, changed_list, 'Abandon')
                feature_function_status = post_update_excel_dict(overlapping_methods, feature_function_status,
                                                                 feature, removed_list, changed_list, 'Overlap')
        return main_res, feature_function_status



    @staticmethod
    def pre_create_changed_functions_excel(results: dict, feature_to_functiom: dict, filename: str, src: str, dst: str,
                                           ofed: str):
        """
        Build excel file from analyzed results
        :param results: dict contain result for main page

        :param filename: name for output excel file
        :param src: kernel source version tag
        :param dst: kernel destination version tag
        :param ofed: Ofed specific tag
        :return:
        """
        # pprint(feature_to_functiom)
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
        colored_condition_column(workbook, worksheet, 'E', len(df_main.index), 30, 10)
        # apply conditions for deletions
        colored_condition_column(workbook, worksheet, 'G', len(df_main.index), 15, 0)
        # Modified worksheet
        dicts_list_from_modify = [feature_to_functiom[feature][index] for
                                  feature in feature_to_functiom.keys() for
                                  index in range(len(feature_to_functiom[feature]))]
        # pprint(dicts_list_from_modify)
        df_mod = pd.DataFrame(dicts_list_from_modify)
        df_mod.set_index('Feature name')
        df_mod.to_excel(writer, sheet_name='Feature function status', startrow=1, header=False, index=False)
        worksheet_mod = writer.sheets['Feature function status']
        for col_num, value in enumerate(df_mod.columns.values):
            worksheet_mod.write(0, col_num, value, header_format)

        writer.save()
        logger.info(f"Excel {filename} was created in {os.path.abspath(filename)}")

    @staticmethod
    def post_create_changed_functions_excel(results: dict, function_status: dict,
                                            filename: str, src: str, dst: str, ofed: str):
        """
        Build excel file from analyzed results
        :param results: dict contain result for main page
        :param function_status: dict contain features functions status between kernels
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
        colored_condition_row(workbook, worksheet, 'H', len(df_main.index))
        # header
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1})
        for col_num, value in enumerate(df_main.columns.values):
            worksheet.write(1, col_num, value, header_format)

        dicts_list_from_modify = [function_status[feature][index] for
                                  feature in function_status.keys() for
                                  index in range(len(function_status[feature]))]

        df_mod = pd.DataFrame(dicts_list_from_modify)
        df_mod.set_index('Feature name')
        df_mod.to_excel(writer, sheet_name='Feature function status', startrow=1, header=False, index=False)
        worksheet_mod = writer.sheets['Feature function status']
        for col_num, value in enumerate(df_mod.columns.values):
            worksheet_mod.write(0, col_num, value, header_format)

        writer.save()
        logger.info(f"Excel was created in {EXCEL_LOC+filename}.xlsx")
