import re
from datetime import datetime
import json
from pprint import pprint

import numpy as np
import pandas as pd
import os

from Comperator.Comperator import Comperator, get_func_stats, get_diff_stats
from repo_processor.Processor import save_to_json, get_actual_ofed_info, get_ofed_functions_info, extract_function
from utils.setting_utils import *

logger = get_logger('Analyzer', 'Analyzer.log')

# def color_cell_if_equal(workbook, sheet_name, col: chr, col_len: int, value):
#     red_format = workbook.add_format({'bg_color': '#FF0000',
#                                       'font_color': '#000000'})
#     place = f'{col}2:{col}{col_len + 1}'
#     worksheet = workbook.get_worksheet_by_name(sheet_name)
#     worksheet.conditional_format(place,
#                              {'type': 'cell',
#                               'criteria': '==',
#                               'value': value,
#                               'format': red_format})


def colored_condition_cell(workbook, sheet_name, col: chr, col_len: int, row: int, is_col: bool):
    """
    create 3 color condition in wanted col over worksheet
    :param workbook: xlsxlwriter workbook
    :param sheet_name: xlsxwriter worksheet name
    :param col: Excel col char (e.g 'A','B'..)
    :param col_len: number of rows in col
    :return:
    """

    worksheet = workbook.get_worksheet_by_name(sheet_name)
    if is_col:
        place = f'{col}3:{col}{col_len + 2}'
    else:
        place = f'A{row}:{col}{row}'
    # formatting
    red_format = workbook.add_format({'bg_color': '#FF0000',
                                      'font_color': '#FF0000'})
    yellow_format = workbook.add_format({'bg_color': '#FFEB9C',
                                         'font_color': '#FFEB9C'})
    green_format = workbook.add_format({'bg_color': '#C6EFCE',
                                        'font_color': '#C6EFCE'})
    orange_format = workbook.add_format({'bg_color': '#FFA500',
                                        'font_color': '#FFA500'})
    aqua_format = workbook.add_format({'bg_color': '#41DFEB',
                                        'font_color': '#41DFEB'})
    worksheet.conditional_format(place,
                                 {'type': 'cell',
                                  'criteria': '==',
                                  'value': LOW,
                                  'format': green_format})
    worksheet.conditional_format(place,
                                 {'type': 'cell',
                                  'criteria': '==',
                                  'value': MEDIUM,
                                  'format': yellow_format})
    worksheet.conditional_format(place,
                                 {'type': 'cell',
                                  'criteria': '==',
                                  'value': HIGH,
                                  'format': orange_format})
    worksheet.conditional_format(place,
                                 {'type': 'cell',
                                  'criteria': '==',
                                  'value': SEVERE,
                                  'format': red_format})
    worksheet.conditional_format(place,
                                 {'type': 'cell',
                                  'criteria': '==',
                                  'value': REDESIGN,
                                  'format': aqua_format})


def colored_condition_row(workbook, worksheet, col: chr, col_len: int):
    red_format = workbook.add_format({'bg_color': '#FFC7CE',
                                      'font_color': '#9C0006'})
    yellow_format = workbook.add_format({'bg_color': '#FFEB9C',
                                         'font_color': '#9C6500'})
    worksheet.conditional_format(f'A3:{col}{col_len + 2}',
                                 {'type': 'formula',
                                  'criteria': '=AND($G3+H3=0,$E3+FC3>0)',
                                  'format': red_format})

def write_and_link(name, diff, dir):
    filename = f'{dir}/{name}.diff'
    if not os.path.isfile(filename):
        with open(filename, 'w') as handle:
            for line in diff:
                handle.write(line+'\n')
    hyperlink = f'=HYPERLINK("{os.path.basename(dir)}\{name}.diff","View")'
    return hyperlink

def create_diff_file_and_link(method_name: str, info_dict: str, directory: str):
    if method_name not in info_dict.keys():
        return 'NA'
    if info_dict[method_name]['View'] == 'NA':
        return 'NA'
    method_diff = info_dict[method_name]['View']
    return write_and_link(method_name, method_diff, directory)


def get_stat_or_none(method: str, info_dict: dict, stat: str):
    if method in info_dict.keys() and info_dict[method]['Stats'][stat] != 'NA':
        return info_dict[method]['Stats'][stat]
    else:
        return ''


def get_kernel_status(method, rm_list, ch_list):
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


def create_main_dict(kernel_dict, ofed_list, diff_dict):
    main_res = []
    patch_number = 0
    for commit in ofed_list:
        patch_number += 1
        commit_risk = LOW
        for func in commit['Functions']:
            # Added by OFED - not relevant
            if commit['Functions'][func]['Status'] == 'Add':
                logger.debug(f'Ignore {func} - Added by OFED patch')
                continue
            # Able to process function - have info
            if func in diff_dict.keys():
                logger.debug(f"{func} - Have info - risk {diff_dict[func]['Stats']['Risk']}")
                commit_risk = max(commit_risk, string_to_enum(diff_dict[func]['Stats']['Risk']))
            # Fail to process
            else:
                # function changed between base codes
                if func in kernel_dict.keys():
                    status = kernel_dict[func]['Status']
                    # function removed from kernel - High risk
                    if status == 'Delete':
                        logger.debug(f"{func} - Removed from kernel - risk Severe")
                        commit_risk = SEVERE
                    # function changed but not removed - Medium risk (worst case scenario) - missing change info
                    else:
                        logger.debug(f"{func} - Unable to process, missing info - risk High")
                        commit_risk = HIGH
                # function didn't changed between base codes
                else:
                    logger.debug(f"{func} - Not changed - No risk")
        main_res.append({
            "Hash": commit['Hash'][:12],
            "Subject": commit['Subject'],
            "Risk Level": commit_risk,
            "Feature": commit['Feature'],
            "Status": commit['Status'],
            "Author": commit['Author'],
            "Patch Number": patch_number,
            "Change-Id": commit['Change-Id'],
        })
    return main_res


def get_info_from_diff(func_name, chash, diff_dict, dir_path, extracted, ext_path, backports, back_path):
    ret_stats = {
        "Hash": chash[:12],
        "Function": func_name,
        "Diff": create_diff_file_and_link(func_name, diff_dict, dir_path),
        "Last OFED version": create_diff_file_and_link(func_name, extracted, ext_path),
        "Last backports version": create_diff_file_and_link(func_name, backports, back_path),
        "Risk level": get_stat_or_none(func_name, diff_dict, 'Risk'),
        "Removed": get_stat_or_none(func_name, diff_dict, 'Removed'),
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


def create_with_missing_info(func_name, chash, diff_dict, dir_path, extracted, ext_path,
                             backports, back_path, risk):
    ret_stats = {
        "Hash": chash[:12],
        "Function": func_name,
        "Diff": create_diff_file_and_link(func_name, diff_dict, dir_path),
        "Last OFED version": create_diff_file_and_link(func_name, extracted, ext_path),
        "Last backports version": create_diff_file_and_link(func_name, backports, back_path),
        "Risk level": risk_to_string(risk),
        "Removed": risk_to_string(risk) == 'Severe',
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


def create_func_stats_line(func_name, chash, diff_dict, kernel_dict, extracted,
                           dir_path, ext_path, backports, back_path):
    # Got info about function
    if func_name in diff_dict.keys():
        ret = get_info_from_diff(func_name, chash, diff_dict, dir_path, extracted, ext_path, backports, back_path)
        return ret
    # Missing info
    else:
        # Known as modified
        if func_name in kernel_dict.keys():
            status = kernel_dict[func_name]['Status']
            # removed
            if status == 'Delete':
                ret = create_with_missing_info(func_name, chash, diff_dict, dir_path,
                                               extracted, ext_path, backports, back_path, SEVERE)
                return ret
            # missing modification info
            else:
                ret = create_with_missing_info(func_name, chash, diff_dict, dir_path,
                                               extracted, ext_path, backports, back_path, HIGH)
                return ret
        # Didn't changed
        else:
            ret = create_with_missing_info(func_name, chash, diff_dict, dir_path,
                                           extracted, ext_path, backports, back_path, LOW)
            return ret



def create_commit_to_function_dict(ofed_list, diff_dict, kernel_dict, extracted, backports, dir_name):
    root_path = f"{EXCEL_LOC + dir_name}"
    os.mkdir(root_path, 0o0755)
    dir_path = f"{root_path + '/' +dir_name}_diff"
    os.mkdir(dir_path, 0o0755)
    back_path = f"{root_path + '/' + dir_name}_back"
    os.mkdir(back_path, 0o0755)
    ext_path = f"{root_path + '/' +dir_name}_ext"
    os.mkdir(ext_path, 0o0755)
    commit_to_function = []
    for commit in ofed_list:
        for func in commit['Functions'].keys():
            if commit['Functions'][func]['Status'] == 'Add':
                continue
            commit_to_function.append(create_func_stats_line(func, commit['Hash'], diff_dict, kernel_dict,
                                                             extracted, dir_path, ext_path,
                                                             backports, back_path))
    return commit_to_function


def create_pie_chart(workbook, main_results):
    headings = ['Levels', 'Number of commits']
    risks = ['Low', 'Medium', 'High', 'Severe', 'Redesign']
    res = [f'=COUNTIF(Tree!C3:C{len(main_results) + 2},{risk})' for risk in range(5)]
    # res.append(f'=COUNTIF(Tree!C3:C{len(main_results) + 2}, {REDESIGN})')
    bold = workbook.add_format({'bold': 1})
    chart_sheet = workbook.add_worksheet('Charts')
    chart_sheet.write_row('A1', headings, bold)
    chart_sheet.write_column('B2', res)
    chart_sheet.write_column('A2', risks)
    pie = workbook.add_chart({'type': 'pie'})
    pie.add_series({
        'name':       'Levels',
        'categories': f'=Charts!$A$2:$A$6',
        'values':     f'=Charts!$B$2:$B$6',
        'data_labels': {'value': True,
                        'percentage': True,
                        'separator': "\n"},
        'points': [
            {'fill': {'color': '#C6EFCE'}},
            {'fill': {'color': '#FFEB9C'}},
            {'fill': {'color': '#FFA500'}},
            {'fill': {'color': '#FF0000'}},
            {'fill': {'color': '#41DFEB'}},
        ]
    })
    pie.set_title({'name': 'Commits Risk Division'})
    pie.set_style(10)
    chart_sheet.insert_chart('A1', pie, {'x_offset': 0, 'y_offset': 0})
    return workbook


def create_line_chatr(workbook, df_main):
    line = workbook.add_chart({'type': 'line'})
    line.add_series({
        'name':       'Commit timeline risk',
        'categories': f'=Tree!$A$3:$A${len(df_main.index)}',
        'values':     f'=Tree!$C$3:$C${len(df_main.index)}',
        'line':       {'none': True},
        'marker': {'type': 'square',
                   'size,': 2,
                   'border': {'color': 'green'},
                   'fill':   {'color': 'white'}
                   },

    })

    line.set_title({'name': 'REABAE - Work Plane'})
    line.set_x_axis({'name': 'Commit number'})
    line.set_y_axis({'name': 'Risk'})
    line.set_style(10)
    chart_sheet = workbook.get_worksheet_by_name('Charts')
    chart_sheet.insert_chart('A6', line, {'x_offset': 25, 'y_offset': 10})


def get_max_length(split_list):
    return max([len(li) for li in split_list])


def colnum_string(n):
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


def write_data_to_sheet(workbook, split_list):
    ROW = 17
    end_commit = 0
    day = 1

    max_length = get_max_length(split_list)
    chart_sheet = workbook.get_worksheet_by_name('Charts')
    chart_sheet.set_column(1, max_length + 1, WIDTH)
    for li in split_list:
        li = list(li)
        start_commit = end_commit + 1
        end_commit = start_commit + len(li) - 1
        li.insert(0, f'Day {day}: commits {start_commit}-{end_commit}')
        chart_sheet.write_row(f'A{ROW}', li)
        col = colnum_string(len(li) + 1)
        colored_condition_cell(workbook, 'Charts', col, 0, ROW, False)
        ROW += TWO
        day += 1


def create_color_timeline(main_results, workbook, work_days, df_main):
    col_num = len(df_main)
    risks = [f'=Tree!C{col_num - index + TWO}' for index in range(col_num)]
    # risks = [commit['Risk Level'] for commit in main_results]
    split_list = np.array_split(risks, work_days)
    write_data_to_sheet(workbook, split_list)


def need_review(func, stat, src_info, dst_info, last_info, rebase_info, same_final):
    diff = last_info[stat] - src_info[stat]
    expected = dst_info[stat] + diff
    ret = {
        'Src': src_info[stat],
        'Dst': dst_info[stat],
        'Last': last_info[stat],
        'Rebase': rebase_info[stat],
        'Diff': diff,
        'Expected': expected,
        f'{stat} Review': (expected != rebase_info[stat]) and not same_final
    }
    return ret


def is_diff_exist(function_diff):
    return function_diff['+'] != 0 or function_diff['-'] != 0

def get_modificatins_only(mod_list):
    # return [line.replace('+', '').replace('-', '') for line in mod_list if line.startswith('-') or line.startswith('+')]
    return [line.replace(line[0], '', 1) for line in mod_list
            if re.match("^[+|-]", line) and not re.match("^[+|-] +\\n$", line)]

def get_modifications_diff_stats(func, last_mod, new_mod):
    last_only_mod = get_modificatins_only(last_mod)
    new_only_mod = get_modificatins_only(new_mod)
    return get_diff_stats(last_only_mod, new_only_mod, func)

def get_partial_diff_stats(mod_stas):
    ret = {}
    for key in ['+', '-', 'X']:
        ret[key] = mod_stas[key]
    return ret

def get_review_urgency(bases_diff, apply_diff, mod_diff):
    # function didn't changed during kernel versions
    is_kernel_function_equal = not is_diff_exist(bases_diff)
    # function similar in both OFED versions
    is_ofed_function_equal = not is_diff_exist(apply_diff)
    # modifiacations similar in both OFED versions
    is_mod_equal = not is_diff_exist(mod_diff)
    # same base, same end version
    if is_kernel_function_equal and is_ofed_function_equal:
        return LOW
    # same modifications
    elif is_mod_equal:
        return LOW
    # same base, different end version
    elif is_kernel_function_equal and not is_ofed_function_equal:
        return SEVERE
    # different base, same end version
    elif not is_kernel_function_equal and is_ofed_function_equal:
        return SEVERE
    # different base, different end version
    else:
        return MEDIUM


def check_stat_and_create_dict(func, src_info, dst_info, last_info, rebase_info):
    # same_final_function = is_diff_exist(apply_diff)
    # if same_final_function:
    #     logger.info(f'{func} - Same End Version')
    bases_diff = get_diff_stats(src_info['Splited'], dst_info['Splited'], func)
    apply_diff = get_diff_stats(last_info['Splited'], rebase_info['Splited'], func)
    last_modifications = get_diff_stats(src_info['Splited'], last_info['Splited'], func)
    rebase_modifications = get_diff_stats(dst_info['Splited'], rebase_info['Splited'], func)
    modifications_diff = get_modifications_diff_stats(func, last_modifications['Diff newline'],
                                                      rebase_modifications['Diff newline'])
    return {
        'Review Need Level': get_review_urgency(bases_diff, apply_diff, modifications_diff),
        'Src': src_info,
        'Dst': dst_info,
        'Last': last_info,
        'Rebase': rebase_info,
        'Bases diff': bases_diff,
        'Apply diff': apply_diff,
        'Last modifications': last_modifications,
        'Rebase modifications': rebase_modifications,
        'Modifications diff': modifications_diff,
        # 'Src': src_info,
        # 'Dst': dst_info,
        # 'Last': last_info,
        # 'Rebase': rebase_info,
        # 'Bases diff': bases_diff,
        # 'Apply diff': apply_diff,
        # 'Last modifications': last_modifications,
        # 'Rebase modifications': rebase_modifications,
        # 'Modifications diff': modifications_diff,
        # 'Modification diff exist': is_diff_exist(modifications_diff),
        # 'Modifications': {
        #     'Last': get_partial_diff_stats(last_modifications),
        #     'Rebase': get_partial_diff_stats(rebase_modifications),
        #     'Diff': get_partial_diff_stats(modifications_diff)
        # },
        # 'Lines': need_review(func, 'Lines', src_info, dst_info, last_info, rebase_info, False),
        # 'Scopes': need_review(func, 'Scopes', src_info, dst_info, last_info, rebase_info, False),
    }


def genarate_results_for_excel(stats_info, dir_name):
    root_path = f"{EXCEL_LOC + dir_name}"
    os.mkdir(root_path, 0o0755)
    last_path = f"{root_path + '/' +dir_name}_last"
    os.mkdir(last_path, 0o0755)
    rebase_path = f"{root_path + '/' + dir_name}_rebase"
    os.mkdir(rebase_path, 0o0755)
    src_path = f"{root_path + '/' +dir_name}_src"
    os.mkdir(src_path, 0o0755)
    dst_path = f"{root_path + '/' +dir_name}_dst"
    os.mkdir(dst_path, 0o0755)
    ofed_mod_path = f"{root_path + '/' +dir_name}_ofed_mod"
    os.mkdir(ofed_mod_path, 0o0755)
    rebase_mod_path = f"{root_path + '/' +dir_name}_rebase_mod"
    os.mkdir(rebase_mod_path, 0o0755)
    mod_diff_path = f"{root_path + '/' +dir_name}_mod_diff"
    os.mkdir(mod_diff_path, 0o0755)
    bases_diff_path = f"{root_path + '/' +dir_name}_bases_diff"
    os.mkdir(bases_diff_path, 0o0755)
    apply_diff_path = f"{root_path + '/' +dir_name}_apply_diff"
    os.mkdir(apply_diff_path, 0o0755)
    data_frame_info = []
    for func, info in stats_info.items():
        data_frame_info.append({
            'Function': func,
            'Need Review Level': info['Review Need Level'],
            'Modification diffs': write_and_link(func, info['Modifications diff']['Diff'], ofed_mod_path),
            'Rebase modifications': write_and_link(func, info['Rebase modifications']['Diff'], rebase_mod_path),
            'OFED modifications': write_and_link(func, info['Last modifications']['Diff'], mod_diff_path),
            'Bases diff':  write_and_link(func, info['Bases diff']['Diff'], bases_diff_path),
            'Apply diff':  write_and_link(func, info['Apply diff']['Diff'], apply_diff_path),
            'Src': write_and_link(func, info['Src']['Splited'], src_path),
            'Dst': write_and_link(func, info['Dst']['Splited'], dst_path),
            'Last': write_and_link(func, info['Last']['Splited'], last_path),
            'Rebase': write_and_link(func, info['Rebase']['Splited'], rebase_path),
        })
    return data_frame_info



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
                kernel_dict = open_json(j_file)
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
    def build_commit_dicts(kernel_json: str, ofed_json: str, diff_json: str,
                           extracted_json: str, backports_json: str, output: str):
        """
        Take processor Json's output and analyze result, build data for Excel display
        :return:
        """
        #kernel_dict = Analyzer.combine_kernel_dicts(kernel_json)
        kernel_dict = open_json(kernel_json)
        commit_list = open_json(ofed_json)
        diff_dict = open_json(diff_json)
        extracted = open_json(extracted_json)
        backports = open_json(backports_json)
        commit_to_function = create_commit_to_function_dict(commit_list, diff_dict, kernel_dict,
                                                            extracted, backports,output)
        main_res = create_main_dict(kernel_dict, commit_list, diff_dict)
        save_to_json(main_res, f'{output}_main_res')
        save_to_json(commit_to_function, f'{output}_com_to_func')
        return main_res, commit_to_function



    @staticmethod
    def create_colored_tree_excel(main_results: dict, commit_to_function: dict, filename: str,
                                  src: str, dst: str, ofed: str):

        """
        Build excel file from analyzed results
        :return:
        """

        title = f"MSR Analyze [OFED: {ofed} | Kernel src: {src} | kernel dst: {dst}]"
        df_main = pd.DataFrame(main_results[::-1])
        df_main.set_index('Hash')
        writer = pd.ExcelWriter(f"{EXCEL_LOC}{filename}/{filename}.xlsx", engine='xlsxwriter')
        df_main.to_excel(writer, sheet_name='Tree', startrow=2, header=False, index=False)

        workbook = writer.book
        worksheet = writer.sheets['Tree']

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
        colored_condition_cell(workbook, 'Tree', 'C', len(df_main.index), 0, True)

        dicts_list_from_modify = commit_to_function
        df_mod = pd.DataFrame(dicts_list_from_modify)
        df_mod.set_index('Hash')
        df_mod.to_excel(writer, sheet_name='Functions to commits', startrow=1, header=False, index=False)
        worksheet_mod = writer.sheets['Functions to commits']
        for col_num, value in enumerate(df_mod.columns.values):
            worksheet_mod.write(0, col_num, value, header_format)


        # create chart_stock
        # worksheet_chart = writer.sheets['Work plan charts']
        # PIE chart
        create_pie_chart(workbook, main_results)
        # Create timeline
        create_color_timeline(main_results, workbook, WORK_DAYS, df_main)
        # create_line_chatr(workbook, df_main)

        # save
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
        colored_condition_row(workbook, 'Analyzed_result', 'H', len(df_main.index))
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

    @staticmethod
    def create_diffs_from_extracted(ext_loc: str):
        stats_dict = {}
        ext_info = open_json(ext_loc)
        for func, info in ext_info.items():
            if func == 'Missing info':
                continue
            if not info['Last'] or not info['Rebase'] or not info['Src'] or not info['Dst']:
                logger.warn(f"{func} - Missing info.. skipped")
                continue
            src_stats = get_func_stats(info['Src'])
            dst_stats = get_func_stats(info['Dst'])
            last_stats = get_func_stats(info['Last'])
            rebase_stats = get_func_stats(info['Rebase'])

            stats_dict[func] = check_stat_and_create_dict(func, src_stats, dst_stats, last_stats, rebase_stats)

        return save_to_json(stats_dict, 'stats_dict_post1')

    @staticmethod
    def create_rebase_reviews_excel(info_json, output):
        stats_info = open_json(info_json)
        results = genarate_results_for_excel(stats_info, output)

        title = f"Review After Rebase"
        df_main = pd.DataFrame(results)
        df_main.set_index('Function')
        writer = pd.ExcelWriter(f"{EXCEL_LOC}{output}/{output}.xlsx", engine='xlsxwriter')
        df_main.to_excel(writer, sheet_name='Review', startrow=2, header=False, index=False)

        workbook = writer.book
        worksheet = writer.sheets['Review']

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

        colored_condition_cell(workbook, 'Review', 'B', len(df_main.index), '', True)
        # color_cell_if_equal(workbook, 'Review', 'B', len(df_main.index), True)
        # save
        writer.save()
        logger.info(f"Excel {output} was created in {os.path.abspath(output)}")
        # apply conditions for modification
        # colored_condition_cell(workbook, worksheet, 'C', len(df_main.index), 0, True)

        # dicts_list_from_modify = commit_to_function
        # df_mod = pd.DataFrame(dicts_list_from_modify)
        # df_mod.set_index('Hash')
        # df_mod.to_excel(writer, sheet_name='Functions to commits', startrow=1, header=False, index=False)
        # worksheet_mod = writer.sheets['Functions to commits']
        # for col_num, value in enumerate(df_mod.columns.values):
        #     worksheet_mod.write(0, col_num, value, header_format)
# @staticmethod
# def pre_analyze_changed_method(kernel_json: str, ofed_json: str, diff_json: str, output: str):
#     """
#     Take processor Json's output and analyze result, build data for Excel display
#     :param kernel_json:
#     :param ofed_json:
#     :return:
#     """
#     main_res = {}
#     feature_to_modified = {}
#     feature_to_deleted = {}
#     feature_to_function = {}
#     kernel_dict = Analyzer.combine_kernel_dicts(kernel_json)
#     ofed_dict = {}
#     try:
#         with open(JSON_LOC+ofed_json) as o_file:
#             ofed_dict = json.load(o_file)
#         with open(JSON_LOC + diff_json) as d_file:
#             diff_dict = json.load(d_file)
#     except IOError as e:
#         logger.critical(f"failed to read json:\n{e}")
#     dir_name = str(datetime.timestamp(datetime.now()))
#     dir_path = f"{EXCEL_LOC + output}"
#     os.mkdir(dir_path, 0o0755)
#     for feature in ofed_dict.keys():
#         print(f'featur: {feature}')
#         changed_set = set()
#         removed_set = set()
#         uniq_new = 0
#         uniq_old = 0
#         # overall_methods = len(ofed_dict[feature][''])
#         for method in ofed_dict[feature]['kernel']:
#             if method in kernel_dict['deleted'].keys():
#                 removed_set.add(method)
#             if method in kernel_dict['modified'].keys():
#                 changed_set.add(method)
#                 if method in diff_dict.keys():
#                     uniq_new += diff_dict[method]['Stats']['New function unique lines']
#                     uniq_old += diff_dict[method]['Stats']['Old function unique lines']
#                 else:
#                     logger.warn(f"Missing Info: method - {method} | feature - {feature}")
#         changed_set -= removed_set
#         ofed_only_methods_num = len(ofed_dict[feature]['ofed_only'])
#         kernel_methods_num = len(ofed_dict[feature]['kernel'])
#         main_res[feature] = {"Feature name": feature,
#                              "OFED only methods": ofed_only_methods_num,
#                              "Kernel methods": kernel_methods_num,
#                              # "Overall methods feature depend":
#                              #     ofed_only_methods_num + kernel_methods_num,
#                              "Changed in kernel": len(changed_set),
#                              "Changed % [comparison to kernel methods]":
#                                  int((len(changed_set) / kernel_methods_num) * 100)
#                                  if kernel_methods_num != 0 else 0,
#                              "Deleted from kernel": len(removed_set),
#                              "Deleted % [comparison to kernel methods]":
#                                  int((len(removed_set) / kernel_methods_num) * 100)
#                                  if kernel_methods_num != 0 else 0,
#                              "Old lines unique": uniq_old,
#                              "New lines unique": uniq_new
#                              }
#         if feature not in feature_to_function.keys():
#             feature_to_function[feature] = []
#         if removed_set:
#             feature_to_function = update_current_feature_methods(feature_to_function, list(removed_set),
#                                                                  feature, diff_dict,dir_path, 'Removed')
#         if changed_set:
#             feature_to_function = update_current_feature_methods(feature_to_function, list(changed_set),
#                                                                  feature, diff_dict, dir_path, 'Changed')
#         if len(ofed_dict[feature]['ofed_only']):
#             feature_to_function = update_current_feature_methods(feature_to_function, ofed_dict[feature]['ofed_only'],
#                                                                  feature, diff_dict, dir_path, 'OFED added')
#         unchanged_set = set(ofed_dict[feature]['kernel'])
#         unchanged_set = unchanged_set.difference(changed_set, removed_set)
#         if unchanged_set:
#             feature_to_function = update_current_feature_methods(feature_to_function, list(unchanged_set),
#                                                                  feature, diff_dict, dir_path, 'Unchanged')
#     return main_res, feature_to_function

    # @staticmethod
    # def pre_create_changed_functions_excel(results: dict, feature_to_functiom: dict, filename: str, src: str, dst: str,
    #                                        ofed: str):
    #     """
    #     Build excel file from analyzed results
    #     :param results: dict contain result for main page
    #
    #     :param filename: name for output excel file
    #     :param src: kernel source version tag
    #     :param dst: kernel destination version tag
    #     :param ofed: Ofed specific tag
    #     :return:
    #     """
    #     # pprint(feature_to_functiom)
    #     title = f"MSR Analyze [OFED: {ofed} | Kernel src: {src} | kernel dst: {dst}]"
    #     df_main = pd.DataFrame([results[feature] for feature in results.keys()])
    #     df_main.set_index('Feature name')
    #     writer = pd.ExcelWriter(EXCEL_LOC + filename + '.xlsx', engine='xlsxwriter')
    #     df_main.to_excel(writer, sheet_name='Analyzed_result', startrow=2, header=False, index=False)
    #
    #     workbook = writer.book
    #     worksheet = writer.sheets['Analyzed_result']
    #
    #     title_format = workbook.add_format({
    #         'bold': True,
    #         'text_wrap': True,
    #         'valign': 'top',
    #         'fg_color': '#00E4BC',
    #         'border': 1})
    #     worksheet.merge_range(f'A1:{chr(ord("A") + len(df_main.columns) - 1)}1', title, title_format)
    #
    #     # header
    #     header_format = workbook.add_format({
    #         'bold': True,
    #         'text_wrap': True,
    #         'valign': 'top',
    #         'fg_color': '#D7E4BC',
    #         'border': 1})
    #     for col_num, value in enumerate(df_main.columns.values):
    #         worksheet.write(1, col_num, value, header_format)
    #
    #     # apply conditions for modification
    #     colored_condition_column(workbook, worksheet, 'E', len(df_main.index), 30, 10)
    #     # apply conditions for deletions
    #     colored_condition_column(workbook, worksheet, 'G', len(df_main.index), 15, 0)
    #     # Modified worksheet
    #     dicts_list_from_modify = [feature_to_functiom[feature][index] for
    #                               feature in feature_to_functiom.keys() for
    #                               index in range(len(feature_to_functiom[feature]))]
    #     # pprint(dicts_list_from_modify)
    #     df_mod = pd.DataFrame(dicts_list_from_modify)
    #     df_mod.set_index('Feature name')
    #     df_mod.to_excel(writer, sheet_name='Feature function status', startrow=1, header=False, index=False)
    #     worksheet_mod = writer.sheets['Feature function status']
    #     for col_num, value in enumerate(df_mod.columns.values):
    #         worksheet_mod.write(0, col_num, value, header_format)
    #
    #     writer.save()
    #     logger.info(f"Excel {filename} was created in {os.path.abspath(filename)}")



    # @staticmethod
    # def post_analyze_changed_method(kernel_json: str, new_ofed_json: str, old_ofed_json: str):
    #
    #     main_res = {}
    #     kernel_modified = {}
    #     only_new_methods = {}
    #     only_old_methods = {}
    #     modified_in_kernel = {}
    #     kernel_dict = {}
    #     new_ofed_dict = {}
    #     old_ofed_dict = {}
    #     feature_function_status = {}
    #     kernel_filename = []
    #     kernel_filename.append(kernel_json)
    #     kernel_dict = Analyzer.combine_kernel_dicts(kernel_filename)
    #     try:
    #         with open(JSON_LOC+old_ofed_json) as o_file:
    #             old_ofed_dict = json.load(o_file)
    #         with open(JSON_LOC+new_ofed_json) as n_file:
    #             new_ofed_dict = json.load(n_file)
    #     except IOError as e:
    #         logger.critical(f"failed to read json:\n{e}")
    #     # newly added features
    #     new_features = list(set(new_ofed_dict.keys()) - set(old_ofed_dict.keys()))
    #     # accepted/abandon features
    #     old_features = list(set(old_ofed_dict.keys()) - set(new_ofed_dict.keys()))
    #     combine_features = list(set(old_ofed_dict.keys()).intersection(set(new_ofed_dict.keys())))
    #     for feature in combine_features:
    #         changed_list = []
    #         removed_list = []
    #         function_modified_in_new = [method for method in new_ofed_dict[feature]['kernel']]
    #         function_modified_in_old = [method for method in old_ofed_dict[feature]['kernel']]
    #         for method in function_modified_in_old:
    #             if method in kernel_dict['deleted'].keys():
    #                 if method not in removed_list:
    #                     removed_list.append(method)
    #             if method in kernel_dict['modified'].keys():
    #                 if method not in changed_list:
    #                     changed_list.append(method)
    #         only_new_methods = list(set(function_modified_in_new) - set(function_modified_in_old))
    #         only_old_methods = list(set(function_modified_in_old) - set(function_modified_in_new))
    #         overlapping_methods = list(set(function_modified_in_new).intersection(set(function_modified_in_old)))
    #         main_res[feature] = {"Feature name": feature,
    #                              "Old OFED version methods dependencies": len(only_old_methods) + len(overlapping_methods),
    #                              "New OFED version methods dependencies": len(only_new_methods) + len(overlapping_methods),
    #                              "Overlapping methods dependencies": len(overlapping_methods),
    #                              "Added methods dependencies": len(only_new_methods),
    #                              "Missing methods dependencies": len(only_old_methods),
    #                              "Modified methods in kernel": len(changed_list),
    #                              "Removed methods from kernel": len(removed_list)}
    #         if len(only_old_methods) or len(only_new_methods) or len(overlapping_methods) or len(changed_list) or len(removed_list):
    #             feature_function_status[feature] = []
    #             feature_function_status = post_update_excel_dict(only_new_methods, feature_function_status,
    #                                                              feature, removed_list, changed_list, 'Add')
    #             feature_function_status = post_update_excel_dict(only_old_methods, feature_function_status,
    #                                                              feature, removed_list, changed_list, 'Abandon')
    #             feature_function_status = post_update_excel_dict(overlapping_methods, feature_function_status,
    #                                                              feature, removed_list, changed_list, 'Overlap')
    #     return main_res, feature_function_status
