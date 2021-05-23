from difflib import Differ
from pprint import pprint
from utils.setting_utils import *
import re

logger = get_logger('Comperator', 'Comperator.log')


def is_prototype_changed(diff: list, func_name: str) -> tuple:
    """Check if function prototype and context has changed"""
    proto = False
    ctx = False
    inside_proto = False
    inside_ctx = False

    for line in diff:
        try:
            if f"{func_name}(" in line and not inside_ctx:
                inside_proto = True
            if '{' in line and inside_proto:
                inside_proto = False
                inside_ctx = True
            if (line.startswith('+') or line.startswith('-') or line.startswith('?')) and inside_proto:
                proto = True
            if (line.startswith('+') or line.startswith('-') or line.startswith('?')) and inside_ctx:
                ctx = True
        except Exception as e:
            logger.critical(f'failed in line {line}, {e}')

    return proto, ctx


def count_scopes(func: str):
    """Return bumber of scopes inside function"""
    cnt = 0
    split_func = func.replace('\t', '    ').splitlines(keepends=True)
    for line in split_func:
        if re.match("^ *}\\n$", line):
            cnt += 1
    return cnt


def count_changes(diff) -> tuple:
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
    return plus, minus, unchanged


def get_function_risk(is_removed, prototype_changed, context_changed) -> str:
    if is_removed:
        return SEVERE
    elif prototype_changed:
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
    splited = make_readable_function(func)
    scopes = count_scopes(func)
    func_lines = count_lines(func)
    return {
        'Splited': splited,
        'Scopes': scopes,
        'Lines': func_lines
    }


def get_diff_stats(old_func, new_func, func_name):
    d = Differ()
    diff = list(d.compare(old_func, new_func))
    prototype_changed, context_changed = is_prototype_changed(diff, func_name)
    plus, minus, unchanged = count_changes(diff)
    diff_strip = [line.replace('\n', '') for line in diff if not line.startswith('?')]
    return {
        'Diff newline': diff,
        'Diff': diff_strip,
        'API': prototype_changed,
        'Ctx': context_changed,
        '+': plus,
        '-': minus,
        'X': unchanged
    }


class Comperator(object):
    def __init__(self):
        """
        Init Comperator, create instance of Comperator can be used for static method calls
        """

    @staticmethod
    def get_functions_diff_stats(func_a: str, func_b: str, func_name: str,
                                 is_removed: bool, risk: int):
        diff_stats_dict = {}
        if is_removed:
            # In high risk - function cant be found over DST file (removed)
            # so we don't have stats
            diff_stats_dict = {'View': 'NA',
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
                                    'New function scope': 'NA'
                                    }
                               }
            return diff_stats_dict

        if risk == LOW:
            diff_stats_dict = {'View': 'NA',
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
                                   'New function scope': 'NA'
                                   }
                               }
            return diff_stats_dict

        old_func = get_func_stats(func_a)
        new_func = get_func_stats(func_b)
        diff_stats = get_diff_stats(old_func['Splited'], new_func['Splited'], func_name)

        diff_stats_dict = {'View': diff_stats['Diff'],
                           'Stats': {
                               'Risk': risk_to_string(get_function_risk(is_removed, diff_stats['API'], diff_stats['Ctx'])),
                               'Removed': is_removed,
                               'Prototype changed': diff_stats['API'],
                               'Content changed': diff_stats['Ctx'],
                               'Old function size': old_func['Lines'],
                               'New function size': new_func['Lines'],
                               'Old function unique lines': diff_stats['-'],
                               'New function unique lines': diff_stats['+'],
                               'Lines unchanged': diff_stats['X'],
                               'Old function scope': old_func['Scopes'],
                               'New function scope': new_func['Scopes']
                               }
                           }
        logger.debug(diff_stats_dict)
        return diff_stats_dict


