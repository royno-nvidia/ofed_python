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
    def is_prototype_changed(diff: list, func_name: str) -> tuple:
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

    @staticmethod
    def count_scopes(func: str):
        cnt = 0
        split_func = func.replace('\t', '    ').splitlines(keepends=True)
        for line in split_func:
            if "{" in line:
                cnt += 1
        return cnt

    @staticmethod
    def count_changes(diff) -> tuple:
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

    @staticmethod
    def get_functions_diff_stats(func_a: str, func_b: str, func_name: str):
        diff_stats_dict = {}
        t1 = func_a.replace('\t', '    ').splitlines(keepends=True)
        t2 = func_b.replace('\t', '    ').splitlines(keepends=True)
        old_scope = Comperator.count_scopes(func_a)
        new_scope = Comperator.count_scopes(func_b)
        old_func_lines = len(t1)
        new_func_lines = len(t2)
        d = Differ()
        diff = list(d.compare(t1, t2))
        prototype_changed, context_changed = Comperator.is_prototype_changed(diff, func_name)
        plus, minus, unchanged = Comperator.count_changes(diff)
        diff_strip = [line.replace('\n', '') for line in diff if not line.startswith('?')]

        diff_stats_dict = {'Diff': diff_strip,
                           'Stats': {
                               'Prototype changed': prototype_changed,
                               'Content changed': context_changed,
                               'Old function size': old_func_lines,
                               'New function size': new_func_lines,
                               'Old function unique lines': minus,
                               'New function unique lines': plus,
                               'Lines unchanged': unchanged,
                               'Old function scope': old_scope,
                               'New function scope': new_scope
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
        inside_note = False
        last_line = ""
        try:
            with open(filepath) as handle:
                # for i, line in enumerate(handle):
                #     if i >= line_start - 1:
                start_line_types = [f'{func_name}', f"*{func_name}"]
                middle_line_types = [f' {func_name}(' ]

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
