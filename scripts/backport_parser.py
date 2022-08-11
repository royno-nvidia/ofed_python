'''
  python script that order any programing file
'''
import re
import argparse


# Create the parser
from utils.setting_utils import TAB_SIZE


def parse_args():
    parser = argparse.ArgumentParser(description='Automatic full file '
                                        'review for defines and functions order')  
    # Add Arguments
    parser.add_argument('-p', '--path', type=str, default=False,
                        help='Set a file path to review')
    parser.add_argument('-l', '--with_line_number', action='store_true',
                        help='Set a line number')

    # Parse the argument
    options = parser.parse_args()
    return options


def file_parser(args):
    # My variable
    if_statements = "#if"
    else_statements = "#else"
    elif_statements = "#elif"
    endif_statements = "#endif"
    include_statements = '#include'
    struct_statements = '^struct'
    func_statements = ['void', 'int', 'bool', 'string']

    tab = 0

    with open('output.csv', 'w') as output_file:
        with open(args.path, 'r') as Read_file:
            # reading loop from a programing file
            for i, line in enumerate(Read_file.readlines()):

                # searching for the regular expression that we need
                if_pattern = re.search(f"\s*{if_statements}.*", line)
                elif_pattern = re.search(f"\s*{elif_statements}.*", line)
                else_pattern = re.search(f"\s*{else_statements}.*", line)
                endif_pattern = re.search(f"\s*{endif_statements}.*", line)
                include_pattern = re.search(f"\s*{include_statements}.*", line)
                struct_pattern = re.search(f"(\s*{struct_statements}.*) (\s?)(\w+)(\()", line)
                # check if we have any regular expression in the reading line

                if if_pattern:  # have if_statements
                    debug_print(tab, if_pattern.group())
                    write_into_file(args.with_line_number, i, tab, if_pattern.group(), output_file)
                    tab += TAB_SIZE

                elif else_pattern:  # have else_statements
                    tab -= TAB_SIZE
                    debug_print(tab, else_pattern.group())
                    write_into_file(args.with_line_number, i, tab, else_pattern.group(), output_file)
                    tab += TAB_SIZE

                elif elif_pattern:  # have elif_statements
                    tab -= TAB_SIZE
                    debug_print(tab, elif_pattern.group())
                    write_into_file(args.with_line_number, i, tab, elif_pattern.group(), output_file)
                    tab += TAB_SIZE

                elif endif_pattern:  # have endif_statements
                    tab -= TAB_SIZE
                    debug_print(tab, endif_pattern.group())
                    write_into_file(args.with_line_number, i, tab, endif_pattern.group(), output_file)
                    if tab == 0:
                        debug_print(tab, ' ')
                        write_into_file(args.with_line_number, i, tab, ' ', output_file)

                elif include_pattern and tab > 0:  # have include_statements
                    debug_print(tab, include_pattern.group())
                    write_into_file(args.with_line_number, i, tab, include_pattern.group(), output_file)

                elif struct_pattern:
                    debug_print(tab, struct_pattern.group(2))
                    write_into_file(args.with_line_number, i, tab, struct_pattern.group(2), output_file)

                else:  # have function_statements
                    for statement in func_statements:
                        func_pattern = re.search(fr"(\s*{statement}) (\w+)(\()", line)
                        if func_pattern and tab > 0:
                            debug_print(tab, func_pattern.group(2))
                            write_into_file(args.with_line_number, i, tab, func_pattern.group(2), output_file)


def debug_print(tabs, group):
    print(f"{' ' * tabs}{group}")


def write_into_file(option, number, tabs, data, output_files):

    if option:
        output_files.write(f"line {number}:  {' ' * tabs}{data}\n")
    else:
        output_files.write(f"{' ' * tabs}{data}\n")


def main():
    args = parse_args()
    file_parser(args)


if __name__ == '__main__':
    main()