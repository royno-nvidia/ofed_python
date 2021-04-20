from utils.setting_utils import get_logger

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
        if "{" in line:
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