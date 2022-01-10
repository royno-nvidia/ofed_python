import re
import numpy as np
import pandas as pd
from Comperator.Comperator import get_func_stats, get_diff_stats
from utils.setting_utils import *

logger = get_logger('Analyzer', 'Analyzer.log')


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
    purple_format = workbook.add_format({'bg_color': '#8A2BE2',
                                        'font_color': '#8A2BE2'})
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
    worksheet.conditional_format(place,
                                 {'type': 'cell',
                                  'criteria': '==',
                                  'value': NA,
                                  'format': purple_format})


def colored_condition_row(workbook, worksheet, col: chr, col_len: int):
    red_format = workbook.add_format({'bg_color': '#FFC7CE',
                                      'font_color': '#9C0006'})
    worksheet.conditional_format(f'A3:{col}{col_len + 2}',
                                 {'type': 'formula',
                                  'criteria': '=AND($G3+H3=0,$E3+FC3>0)',
                                  'format': red_format})


def write_and_link(name, info, dir, title):
    filename = f'{dir}/{name}.diff'
    if not os.path.isfile(filename):
        with open(filename, 'w') as handle:
            for line in info:
                handle.write(line+'\n')
    hyperlink = f'=HYPERLINK("{os.path.basename(dir)}\{name}.diff", "{title}")'
    return hyperlink


def create_diff_file_and_link(method_name: str, info_dict: str, directory: str):
    if method_name not in info_dict.keys():
        return 'NA'
    if info_dict[method_name]['View'] == 'NA':
        return 'NA'
    method_diff = info_dict[method_name]['View']
    return write_and_link(method_name, method_diff, directory, 'view')


def get_stat_or_none(method: str, info_dict: dict, stat: str):
    if method in info_dict.keys() and info_dict[method]['Stats'][stat] != 'NA':
        return info_dict[method]['Stats'][stat]
    else:
        return ''


def create_risk_explanation(function_by_risk):
    ret = []
    rev_risks = reversed(range(REDESIGN))
    for risk in rev_risks:
        if len(function_by_risk[risk]) > 0:
            ret.append(f'{get_risk_mining(risk)}')
            [ret.append(f'{index}. {func}') for index, func in enumerate(function_by_risk[risk])]
    return ret


def create_main_dict(kernel_dict, ofed_list, diff_dict, sources, explain_dir):
    main_res = []
    patch_number = 0
    commits_risks_cause = {}
    full_path_explain = f'{EXCEL_LOC}{explain_dir}/{explain_dir}_explain'
    check_and_create_dir(full_path_explain, logger)
    for commit in ofed_list:
        patch_number += 1
        max_risk = LOW
        upstream_aligned_functions = []
        function_by_risk = [[] for _ in range(REDESIGN)]
        # In case status is 'accepted' - risk always LOW
        if commit['Status'] != 'accepted':
            for func in commit['Functions']:
                if func in sources.keys():
                    if sources[func]['Aligned']:
                        upstream_aligned_functions.append(func)
                # Added by OFED - not relevant
                if commit['Functions'][func]['Status'] == 'Add':
                    logger.debug(f'Ignore {func} - Added by OFED patch')
                    continue
                # Able to process function - have info
                if func in diff_dict.keys():
                    logger.debug(f"{func} - Have info - risk {diff_dict[func]['Stats']['Risk']}")
                    cur_risk = string_to_enum(diff_dict[func]['Stats']['Risk'])
                    max_risk = max(max_risk, cur_risk)
                    function_by_risk[cur_risk].append(func)
                # Fail to process
                else:
                    # function changed between base codes
                    if func in kernel_dict.keys():
                        status = kernel_dict[func]['Status']
                        # function removed from kernel - High risk
                        if status == 'Delete':
                            logger.debug(f"{func} - Removed from kernel - risk Severe")
                            max_risk = SEVERE
                            function_by_risk[SEVERE].append(func)
                        # function changed but not removed - High risk (worst case scenario) - missing change info
                        else:
                            logger.debug(f"{func} - Unable to process, missing info - risk High")
                            max_risk = HIGH
                            function_by_risk[HIGH].append(func)
                    # function didn't changed between base codes
                    else:
                        logger.debug(f"{func} - Not changed - No risk")
                        function_by_risk[LOW].append(func)
            explanation = create_risk_explanation(function_by_risk)
        main_res.append({
            "Hash": commit['Hash'][:12],
            "Subject": commit['Subject'],
            "Risk Level": max_risk,
            "Risk explanation": write_and_link(commit['Hash'][:12], explanation, full_path_explain, "Info")
            if explanation else '',
            "Note": '',
            "Action": '',
            "Compilation status": '',
            "CI status": '',
            "Aligned to upstream functions": '|'.join(upstream_aligned_functions),
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
    check_and_create_dir(root_path, logger)
    dir_path = f"{root_path + '/' +dir_name}_diff"
    check_and_create_dir(dir_path, logger)
    back_path = f"{root_path + '/' + dir_name}_back"
    check_and_create_dir(back_path, logger)
    ext_path = f"{root_path + '/' +dir_name}_ext"
    check_and_create_dir(ext_path, logger)
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
    risks = [get_risk_mining(risk) for risk in range(5)]
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


def get_max_length(split_list):
    return max([len(li) for li in split_list])


def column_string(n):
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


def draw_on_sheet(workbook, split_list):
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
        col = column_string(len(li) + 1)
        colored_condition_cell(workbook, 'Charts', col, 0, ROW, False)
        ROW += TWO
        day += 1


def create_color_timeline(main_results, workbook, work_days):
    col_num = len(main_results)
    risks = [f'=Tree!C{col_num - index + TWO}' for index in range(col_num)]
    split_list = np.array_split(risks, work_days)
    draw_on_sheet(workbook, split_list)


def is_diff_exist(function_diff):
    return function_diff['+'] != 0 or function_diff['-'] != 0


def get_modificatins_only(mod_list):
    return [line.replace(line[0], '', 1) for line in mod_list
            if re.match("^[+|-]", line) and not re.match("^[+|-] +\\n$", line)]


def get_modifications_diff_stats(func, last_mod, new_mod):
    last_only_mod = get_modificatins_only(last_mod)
    new_only_mod = get_modificatins_only(new_mod)
    return get_diff_stats(last_only_mod, new_only_mod, func, False)


def get_review_urgency(bases_diff, apply_diff, mod_diff, ofed_only):
    # function similar in both OFED versions
    is_ofed_function_equal = not is_diff_exist(apply_diff)
    # if function is ofed only make sure the final version is equal
    if ofed_only:
        return LOW if is_ofed_function_equal else SEVERE
    # function didn't changed during kernel versions
    is_kernel_function_equal = not is_diff_exist(bases_diff)
    # modifiacations similar in both OFED versions
    # same base, same end version
    if is_kernel_function_equal and is_ofed_function_equal:
        return LOW
    # same base, different end version
    elif is_kernel_function_equal and not is_ofed_function_equal:
        return SEVERE
    # different base, same end version
    elif not is_kernel_function_equal and is_ofed_function_equal:
        return SEVERE
    # different base, different end version
    # same modifications
    else:
        return MEDIUM


def check_stat_and_create_dict(func, src_info, dst_info, last_info, rebase_info):
    last_modifications, rebase_modifications, modifications_diff, bases_diff = '', '', '', ''
    ofed_only = False
    if src_info and dst_info:
        bases_diff = get_diff_stats(src_info['Splited'], dst_info['Splited'], func)
        last_modifications = get_diff_stats(src_info['Splited'], last_info['Splited'], func)
        rebase_modifications = get_diff_stats(dst_info['Splited'], rebase_info['Splited'], func)
        modifications_diff = get_modifications_diff_stats(func, last_modifications['Diff newline'],
                                                          rebase_modifications['Diff newline'])
    else:
        ofed_only = True
    apply_diff = get_diff_stats(last_info['Splited'], rebase_info['Splited'], func)
    return {
        'Review Need Level': get_review_urgency(bases_diff, apply_diff, modifications_diff, ofed_only),
        'Src': src_info,
        'Dst': dst_info,
        'Last': last_info,
        'Rebase': rebase_info,
        'Bases diff': bases_diff,
        'Apply diff': apply_diff,
        'Last modifications': last_modifications,
        'Rebase modifications': rebase_modifications,
        'Modifications diff': modifications_diff,
    }


def genarate_results_for_excel(stats_info, dir_name):
    root_path = f"{EXCEL_LOC + dir_name}"
    check_and_create_dir(root_path, logger)
    last = f"{root_path}/last"
    check_and_create_dir(last, logger)
    rebase = f"{root_path}/rebase"
    check_and_create_dir(rebase, logger)
    src = f"{root_path}/src"
    check_and_create_dir(src, logger)
    dst = f"{root_path}/dst"
    check_and_create_dir(dst, logger)
    ofed_mod = f"{root_path}/ofed_mod"
    check_and_create_dir(ofed_mod, logger)
    rebase_mod = f"{root_path}/rebase_mod"
    check_and_create_dir(rebase_mod, logger)
    mod_diff = f"{root_path}/mod_diff"
    check_and_create_dir(mod_diff, logger)
    base_diff = f"{root_path}/bases_diff"
    check_and_create_dir(base_diff, logger)
    apply_diff = f"{root_path}/apply_diff"
    check_and_create_dir(apply_diff, logger)

    data_frame_info = []
    for func, info in stats_info.items():
        review = info['Review Need Level']
        data_frame_info.append({
            'Function': func,
            'Need Review Level': review,
            'OFED2 Diff OFED1': write_and_link(f'{func}-ofed2_vs_ofed_1', info['Apply diff']['Diff'], apply_diff, 'view')
            if info['Apply diff'] else '',
            'Korg2 Diff Korg1': write_and_link(f'{func}-korg2_vs_korg1', info['Bases diff']['Diff'], base_diff, 'view')
            if info['Bases diff'] else '',
            'OFED1 Diff Korg1': write_and_link(f'{func}-ofed1_vs_korg1', info['Last modifications']['Diff'], mod_diff, 'view')
            if info['Last modifications'] else '' ,
            'OFED2 Diff Korg2': write_and_link(f'{func}-ofed2_vs_korg2', info['Rebase modifications']['Diff'], rebase_mod, 'view')
            if info['Rebase modifications'] else '',
            'Rebase2 Diff Rebase1': write_and_link(f'{func}-rebase2_vs_rebase1', info['Modifications diff']['Diff'], ofed_mod, 'view')
            if info['Modifications diff'] else '',
            'Review notes': '',
            'Sign-off by': '',
            'Src': write_and_link(f'{func}-Ksrc', info['Src']['Splited'], src, 'view')
            if info['Src'] else '',
            'Dst': write_and_link(f'{func}-Kdst', info['Dst']['Splited'], dst, 'view')
            if info['Dst'] else '',
            'Last': write_and_link(f'{func}-last', info['Last']['Splited'], last, 'view')
            if info['Last'] else '',
            'Rebase': write_and_link(f'{func}-rebase', info['Rebase']['Splited'], rebase, 'view')
            if info['Rebase'] else '',
        })
    return data_frame_info


def check_alert(d):
    if 'Aligned to upstream functions' in d.keys():
        return True if d['Aligned to upstream functions'] != "" else False


def write_data(workbook, worksheet, data, startline):
    cell_format = workbook.add_format({'bold': True, 'font_color': 'red'})
    row = startline
    for row_dict in data:
        col = 0
        need_alert = check_alert(row_dict)
        for key, value in row_dict.items():
            if need_alert and (key == 'Subject' or key == 'Hash'):
                worksheet.write(row, col, value, cell_format)
            else:
                worksheet.write(row, col, value)
            col += 1
        row += 1


def add_title(workbook, worksheet, ofed, src, dst, col_num):
    title_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#00E4BC',
        'border': 1})
    title = f"MSR Analyze [OFED: {ofed} | Kernel src: {src} | kernel dst: {dst}]"
    worksheet.merge_range(f'A1:{chr(ord("A") + col_num - 1)}1', title, title_format)


def add_headers(workbook, worksheet, keys, line):
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#D7E4BC',
        'border': 1})
    for col_num, value in enumerate(keys):
        worksheet.write(line, col_num, value, header_format)


def create_main_sheet(workbook, main_results, src, dst, ofed):
    worksheet = workbook.add_worksheet('Tree')
    keys = main_results[0].keys()
    # title
    add_title(workbook, worksheet, ofed, src, dst, len(keys))
    # header
    add_headers(workbook, worksheet, keys, 1)
    write_data(workbook, worksheet, main_results[::-1], 2)
    # apply conditions for modification
    colored_condition_cell(workbook, 'Tree', 'C', len(main_results), 0, True)


def create_commit_to_function(workbook, dicts_list_from_modify):
    worksheet_mod = workbook.add_worksheet('Functions to commits')
    add_headers(workbook, worksheet_mod, dicts_list_from_modify[0].keys(), 0)
    write_data(workbook, worksheet_mod, dicts_list_from_modify, 1)


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
        ofed_dict = open_json(ofed_json)
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
    def build_commit_dicts(kernel_json: str, ofed_json: str, loc: str,
                           extracted_json: str, backports_json: str, output: str):
        """
        Take processor Json's output and analyze result, build data for Excel display
        :return:
        """
        #kernel_dict = Analyzer.combine_kernel_dicts(kernel_json)
        kernel_dict = open_json(kernel_json)
        commit_list = open_json(ofed_json)
        diff_dict = open_json(loc['stats'])
        extracted = open_json(extracted_json)
        sources = open_json(loc['ext'])
        backports = open_json(backports_json)
        commit_to_function = create_commit_to_function_dict(commit_list, diff_dict, kernel_dict,
                                                            extracted, backports, output)
        main_res = create_main_dict(kernel_dict, commit_list, diff_dict, sources, output)
        save_to_json(main_res, f'{output}_main_res', output)
        save_to_json(commit_to_function, f'{output}_com_to_func', output)
        return main_res, commit_to_function

    @staticmethod
    def create_colored_tree_excel(main_results: dict, commit_to_function: dict, filename: str,
                                  src: str, dst: str, ofed: str):

        """
        Build excel file from analyzed results
        :return:
        """

        writer = pd.ExcelWriter(f"{EXCEL_LOC}{filename}/{filename}.xlsx", engine='xlsxwriter')
        workbook = writer.book
        create_main_sheet(workbook, main_results, src, dst, ofed)
        dicts_list_from_modify = commit_to_function
        create_commit_to_function(workbook, dicts_list_from_modify)
        create_pie_chart(workbook, main_results)
        create_color_timeline(main_results, workbook, WORK_DAYS)

        # save
        writer.save()
        logger.info(f"Excel {filename} was created in {os.path.abspath(filename)}")

    @staticmethod
    def create_diffs_from_extracted(ext_loc: str, directory: str):
        stats_dict = {}
        missing_func_list = []
        ext_info = open_json(ext_loc)
        for func, info in ext_info.items():
            if func == 'Missing info':
                for f in ext_info['Missing info']:
                    missing_func_list.append(f)
                continue
            # if not info['Last'] or not info['Rebase'] or not info['Src'] or not info['Dst']:
            #     logger.warn(f"{func} - Missing info.. skipped")
            #     missing_func_list.append(func)
            #     continue
            src_stats, dst_stats = '', ''
            if info['Src'] and info['Dst']:
                src_stats = get_func_stats(info['Src'])
                dst_stats = get_func_stats(info['Dst'])
            last_stats = get_func_stats(info['Last'])
            rebase_stats = get_func_stats(info['Rebase'])
            stats_dict[func] = check_stat_and_create_dict(func, src_stats, dst_stats, last_stats, rebase_stats)

        for func in missing_func_list:
            stats_dict[func] = {
                'Review Need Level': NA,
                'Src': '',
                'Dst': '',
                'Last': '',
                'Rebase': '',
                'Bases diff': '',
                'Apply diff': '',
                'Last modifications': '',
                'Rebase modifications': '',
                'Modifications diff': '',
            }
        return save_to_json(stats_dict, f'{directory}_stats_dict_post', directory)

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
