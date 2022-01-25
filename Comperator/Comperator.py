from difflib import Differ
from utils.setting_utils import *
import re

logger = get_logger('Comperator', 'Comperator.log')


def split_api_and_body(diff):
    api_lines = []
    ctx_lines = []
    first_curly_found = False
    try:
        if len(diff) == 1:  # one liner function
            reg = re.search('(\{.*\})', diff[0])
            if reg:
                ctx_lines = reg.group(1).strip()
                api_lines = diff[0].replace(ctx_lines, "").strip()
        else:
            for line in diff:
                if '{' in line:
                    first_curly_found = True
                api_lines.append(line) if not first_curly_found else ctx_lines.append(line)
    except Exception as e:
        logger.critical(f'failed in line {line}, {e}')
    return {
        'API': api_lines,
        'CTX': ctx_lines
    }


def split_api_parts(api: list, func_name: str):
    api = ' '.join(api)
    ret_type = re.split('\(|\)', api)[0].replace(func_name, "").strip()
    arguments = [elem.strip() for elem in re.split(',',re.split('\(|\)', api)[1])]

    return {
        'ret_type': ret_type,
        'arguments': arguments
    }


def remove_prefix(text, prefix='static'):
    if text.startswith(prefix):
        return text[len(prefix):].strip()
    return text


def compare_ret_type(old_ret: str, new_ret: str):
    a = remove_prefix(old_ret)
    b = remove_prefix(new_ret)
    if a != b:
        # Return value changed
        ans= 'Yes'
    elif old_ret != new_ret:
        # Only static diff
        ans= f'Static ' + 'removed' if old_ret.startswith('static') else 'added'
    else:
        ans = 'No'
    return {
        'changed': ans,
        'old_ret': old_ret,
        'new_ret': new_ret
    }


def compare_arguments(old_arg: list, new_arg: list):
    old_arg_set = set(old_arg)
    new_arg_set = set(new_arg)
    return {
        'Same': list(old_arg_set & new_arg_set),
        'Removed': list(old_arg_set - new_arg_set),
        'Added': list(new_arg_set - old_arg_set)
    }


def is_prototype_changed(api_change):
    return True if api_change['args']['Removed'] or api_change['args']['Added'] \
            or api_change['ret']['changed'] != 'No' else False


def process_api_diff(old_api, new_api, func_name):
    old_parts = split_api_parts(old_api, func_name)
    new_parts = split_api_parts(new_api, func_name)
    ret_type_changed = compare_ret_type(old_parts['ret_type'], new_parts['ret_type'])
    arguments_changed = compare_arguments(old_parts['arguments'], new_parts['arguments'])
    ret = {
        'ret': ret_type_changed,
        'args': arguments_changed
    }
    ret['proto_changed'] = is_prototype_changed(ret)
    return ret


def process_ctx_diff(old_ctx, new_ctx):
    d = Differ()
    diff = list(d.compare(old_ctx, new_ctx))
    ctx_changed = False
    try:
        for line in diff:
            if line.startswith('+') or line.startswith('-') or line.startswith('?'):
                ctx_changed = True
        return ctx_changed
    except Exception as e:
        logger.critical(f'failed in line {line}, {e}')


def what_was_changed(old_func, new_func, func_name: str) -> dict:
    """Check if function prototype and context has changed"""
    splited_old = split_api_and_body(old_func)
    splited_new = split_api_and_body(new_func)
    api_ret = process_api_diff(splited_old['API'], splited_new['API'], func_name)
    ctx_ret = process_ctx_diff(splited_old['CTX'], splited_new['CTX'])

    return {
        'API': api_ret,
        'CTX': ctx_ret,
        'Same': api_ret['proto_changed'] and ctx_ret
    }


def count_scopes(func: str):
    """Return bumber of scopes inside function"""
    cnt = 0
    split_func = func.replace('\t', '    ').splitlines(keepends=True)
    for line in split_func:
        if re.match("^ *}\\n$", line):
            cnt += 1
    return cnt


def count_changes(diff) -> dict:
    """Return counts for unique new/old lines and unchanged lines"""
    plus = 0
    minus = 0
    unchanged = 0
    for line in diff:
        if line.startswith('+'):
            plus += 1
        elif line.startswith('-'):
            minus += 1
        elif line.startswith('?'):
            continue
        else:
            unchanged += 1
    return {
        '+': plus,
        '-': minus,
        'X': unchanged
    }


def get_function_risk(is_removed, api, context_changed) -> str:
    if is_removed:
        return SEVERE
    elif api['args']['Removed']:
        return HIGH
    elif context_changed:
        return MEDIUM
    else:
        return LOW


def extract_method_from_file(filepath: str, func_name: str) -> str:
    """
    Extract whole function from given file
    :param filepath: function's file location
    :param func_name: searched function name
    :return:
    """
    function_string = ""
    par_counter = 0
    changed = False
    found = False
    inside_note = False
    last_line = ""
    try:
        with open(filepath) as handle:
            start_line_types = [f'{func_name}(', f'*{func_name}(']
            middle_line_types = [f' {func_name}(', f' *{func_name}(', f'* {func_name}(']
            for line in handle:
                if '/*' in line:
                    inside_note = True
                if '*/' in line:
                    inside_note = False
                if inside_note:
                    continue
                if found or any(s_type in line for s_type in start_line_types) or any(type in line for type in middle_line_types):
                # if f' {func_name}(' in line or found or line.startswith(f'{func_name}('):
                    if line.startswith(f'{func_name}('):
                        function_string += last_line
                    found = True
                    function_string += line
                # for cases function declaration and function implementation in the same file
                    if ';' in line and not changed:
                        function_string = ""
                        found = False
                    if '{' in line:
                        changed = True
                        par_counter += 1
                    if '}' in line:
                        par_counter -= 1
                    if par_counter == 0 and changed:
                        return function_string
                last_line = line
    except Exception as e:
        logger.critical(f"Something went wrong: {e}")


def make_readable_function(func):
    if func is None:
        return None
    read_func = func.replace('\t', '    ').splitlines(keepends=True)
    # remvoe empty lines
    rej = re.compile("^ _*$")
    return [line for line in read_func if not rej.match(line)]


def count_lines(func):
    cnt = 0
    split_func = func.replace('\t', '    ').splitlines(keepends=True)
    for line in split_func:
        if not re.match("^ *\\n$", line):
            cnt += 1
    return cnt


def get_func_stats(func):
    if not func:
        return ''
    splited = make_readable_function(func)
    scopes = count_scopes(func)
    func_lines = count_lines(func)
    return {
        'Splited': splited,
        'Scopes': scopes,
        'Lines': func_lines
    }


def get_diff_stats(old_func, new_func, func_name, with_api=True):
    if not old_func or not new_func:
        return None
    d = Differ()
    diff = list(d.compare(old_func, new_func))
    if with_api:
        changes = what_was_changed(old_func, new_func, func_name)
    counter = count_changes(diff)
    diff_strip = [line.replace('\n', '') for line in diff if not line.startswith('?')]
    return {
        'Aligned': changes['Same'] if with_api else '',
        'Diff newline': diff,
        'Diff': diff_strip,
        'API': changes['API'] if with_api else '',
        'CTX': changes['CTX'] if with_api else '',
        '+': counter['+'],
        '-': counter['-'],
        'X': counter['X']
    }


def removed_func_stats():
    return {'View': 'NA',
            'Stats': {
                 'Risk': 'Severe',
                 'Removed': True,
                 'Prototype changed': 'NA',
                 'Content changed': 'NA',
                 'Old function size': 'NA',
                 'New function size': 'NA',
                 'Old function unique lines': 'NA',
                 'New function unique lines': 'NA',
                 'Lines unchanged': 'NA',
                 'Old function scope': 'NA',
                 'New function scope': 'NA',
                 'Actual api changes': 'NA'
                 }
            }


def unmodified_func_stats():
    return {'View': 'NA',
            'Stats': {
                'Risk': 'Low',
                'Removed': False,
                'Prototype changed': False,
                'Content changed': False,
                'Old function size': 'NA',
                'New function size': 'NA',
                'Old function unique lines': 'NA',
                'New function unique lines': 'NA',
                'Lines unchanged': 'NA',
                'Old function scope': 'NA',
                'New function scope': 'NA',
                'Actual api changes': 'NA'
                }
            }


def get_functions_diff_stats(func_a: str, func_b: str, func_name: str,
                             is_removed: bool, risk: int):
    if is_removed:
        return removed_func_stats()
    if risk == LOW:
        return unmodified_func_stats()
    old_func = get_func_stats(func_a)
    new_func = get_func_stats(func_b)
    diff_stats = get_diff_stats(old_func['Splited'], new_func['Splited'], func_name)
    diff_stats_dict = {'View': diff_stats['Diff'],
                       'Stats': {
                           'Risk': risk_to_string(get_function_risk(is_removed, diff_stats['API'], diff_stats['CTX'])),
                           'Removed': is_removed,
                           'Prototype changed': diff_stats['API']['proto_changed'],
                           'Content changed': diff_stats['CTX'],
                           'Old function size': old_func['Lines'],
                           'New function size': new_func['Lines'],
                           'Old function unique lines': diff_stats['-'],
                           'New function unique lines': diff_stats['+'],
                           'Lines unchanged': diff_stats['X'],
                           'Old function scope': old_func['Scopes'],
                           'New function scope': new_func['Scopes'],
                           'Actual api changes': diff_stats['API']
                           }
                       }
    logger.debug(diff_stats_dict)
    return diff_stats_dict
