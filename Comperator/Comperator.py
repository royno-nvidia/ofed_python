from difflib import Differ
from pprint import pprint
from utils.setting_utils import get_logger, JSON_LOC

logger = get_logger('Comperator', 'Comperator.log')

class Comperator(object):
    def __init__(self):
        """
        Init Comperator, create instance of Comperator can be used for static method calls
        """
    @staticmethod
    def is_prototype_changed(diff:list) -> bool:
        for line in diff:
            if '{' in line:
                return False
            if line.startswith('+') or line.startswith('-') or line.startswith('?'):
                return True

    @staticmethod
    def get_functions_diff_stats(func_a: str, func_b: str):
        diff_stats_dict = {}
        t1 = func_a.replace('\t', '    ').splitlines(keepends=True)
        t2 = func_b.replace('\t', '    ').splitlines(keepends=True)
        # pprint(t2)
        d = Differ()
        diff = list(d.compare(t1, t2))
        plus_diff = 0
        minus_diff = 0
        unchanged_diff = 0
        old_func_lines = len(t1)
        new_func_lines = len(t2)
        lines_diff = new_func_lines - old_func_lines
        prototype_changed = Comperator.is_prototype_changed(diff)
        diff_strip = []
        for line in diff:
            diff_strip.append(line.replace('\n', ''))
            if line.startswith('+'):
                plus_diff += 1
            elif line.startswith('-'):
                minus_diff += 1
            else:
                unchanged_diff += 1

        diff_stats_dict = {'Diff': diff_strip,
                           'Stats': {
                               'Prototype changed': prototype_changed,
                               'Line number diff': lines_diff,
                               'Old version lines': old_func_lines,
                               'New version lines': new_func_lines,
                               'Added new version:': plus_diff,
                               'Missing new version': minus_diff,
                               'Lines unchanged': unchanged_diff
                               }
                           }
        logger.debug(diff_stats_dict)
        return diff_stats_dict

    @staticmethod
    # def extract_method_from_file(filepath: str, proto_line: str) -> str:
    def extract_method_from_file(filepath: str, func_name: str) -> str:
        """
        Extract whole function from given file
        :param filepath: function's file location
        :param func_name: searched function name
        :return:
        """
        function_string = ""
        # line_start = int(proto_line)
        par_counter = 0
        changed = False
        found = False
        with open(filepath) as handle:
            # for i, line in enumerate(handle):
            #     if i >= line_start - 1:
            for line in handle:
                if f'{func_name}(' in line or found:
                    found = True
                    function_string += line
                    if '{' in line:
                        changed = True
                        par_counter += 1
                    if '}' in line:
                        par_counter -= 1
                    if par_counter == 0 and changed:
                        return function_string