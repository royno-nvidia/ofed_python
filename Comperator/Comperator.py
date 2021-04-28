from difflib import Differ
from pprint import pprint

from Comperator.comperator_helpers import *
from utils.setting_utils import get_logger, RiskLevel, enum_risk_to_string

logger = get_logger('Comperator', 'Comperator.log')


def get_func_stats(func):
    splited = func.replace('\t', '    ').splitlines(keepends=True)
    scopes = count_scopes(func)
    func_lines = len(splited)
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
                                 is_removed: bool, risk: RiskLevel):
        diff_stats_dict = {}
        if is_removed:
            # In high risk - function cant be found over DST file (removed)
            # so we don't have stats
            diff_stats_dict = {'Diff': 'NA',
                               'Stats': {
                                    'Risk': 'High',
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

        if risk == RiskLevel.No:
            diff_stats_dict = {'Diff': 'NA',
                               'Stats': {
                                   'Risk': 'No Risk',
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

        diff_stats_dict = {'Diff': diff_stats['Diff'],
                           'Stats': {
                               'Risk': enum_risk_to_string(get_function_risk(is_removed, diff_stats['API'], diff_stats['Ctx'])),
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


