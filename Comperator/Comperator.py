from difflib import Differ
from Comperator.comperator_helpers import *
from utils.setting_utils import get_logger

logger = get_logger('Comperator', 'Comperator.log')


class Comperator(object):
    def __init__(self):
        """
        Init Comperator, create instance of Comperator can be used for static method calls
        """

    @staticmethod
    def get_functions_diff_stats(func_a: str, func_b: str, func_name: str):
        diff_stats_dict = {}
        t1 = func_a.replace('\t', '    ').splitlines(keepends=True)
        t2 = func_b.replace('\t', '    ').splitlines(keepends=True)
        old_scope = count_scopes(func_a)
        new_scope = count_scopes(func_b)
        old_func_lines = len(t1)
        new_func_lines = len(t2)
        d = Differ()
        diff = list(d.compare(t1, t2))
        prototype_changed, context_changed = is_prototype_changed(diff, func_name)
        plus, minus, unchanged = count_changes(diff)
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


