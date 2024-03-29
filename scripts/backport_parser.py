'''
  python script that order any programing file
'''
import os
import re
import argparse
from difflib import Differ

# Create the parser
from utils.setting_utils import TAB_SIZE


def handle_info(args, number, tabs, data):
    number_info = f"line {number}:"
    line_info = f"{' ' * tabs}{data}\n"

    if args.include_numbers:
        final_info = number_info + line_info
    else:
        final_info = line_info

    if args.debug:
        print(final_info)

    with open(args.output, 'a') as output_file:
        output_file.write(final_info)

    return final_info



def parse_args():
    parser = argparse.ArgumentParser(description='Automatic full file '
                                     'review for defines and functions order')
    # Add Arguments
    parser.add_argument('--review', type=str, default="", required=True,
                        help='Set a file path to review')
    parser.add_argument('--reference', type=str, default="",
                        help='Set a file path to use as reference')
    parser.add_argument('--output', type=str, default="", required=True,
                        help='File to flush reviewer output into')
    parser.add_argument('-l', '--with-line-number', dest='include_numbers', action='store_true',
                        help='Get output with line number')
    parser.add_argument('--debug', action='store_true',
                        help='Add debug prints')

    # Parse the argument
    options = parser.parse_args()
    return options


def inc_tab(tab):
    return tab + TAB_SIZE


def dec_tab(tab):
    if tab - TAB_SIZE < 0:
        print("-Error- Tab tried to go under 0")
        return 0
    else:
        return tab - TAB_SIZE


def create_review_diffs(review, reference):
    d = Differ()
    diff = list(d.compare(reference, review))
    diff_strip = [line for line in diff if not line.startswith('?')]
    with open('reviewer.csv', 'w') as output_file:
        for line in diff_strip:
            print(line)
            output_file.write(line)


def file_parser(args, work_on_file):
    print(f'start processing {work_on_file}')
    # My variable
    if_statements = "#if"
    else_statements = ["#else", "#elif"]
    endif_statements = "#endif"
    include_statements = '#include'
    func_end = "}"

    tab = 0
    backports_tree = []
    force_take_line = False
    inside_function = False
    hold_info = ""
    hold_write = False

    with open(work_on_file, 'r') as review_file:
        # reading loop from a programing file
        for i, line in enumerate(review_file.readlines()):
            info = ""
            end_with_backslash = line.endswith('\\\n')
            if force_take_line:
                info = handle_info(args, i, tab, line)
                force_take_line = False

            # searching for the regular expression that we need
            if_pattern = re.search(f"^\s*{if_statements}.*", line)
            else_pattern = re.search(f"^\s*{'|'.join(else_statements)}.*", line)
            endif_pattern = re.search(f"^\s*{endif_statements}.*", line)
            include_pattern = re.search(f"^\s*{include_statements}.*", line)
            func_start_pattern = re.search(fr"(\w+)(\()", line)
            func_end_pattern = re.search(f"^{func_end}", line)
            # check if we have any regular expression in the reading line

            if if_pattern:  # have if_statements
                if hold_write:
                    info = handle_info(args, i, tab, hold_info)
                    tab = inc_tab(tab)
                    inside_function = True
                    backports_tree.append(info)
                    info = ""
                    hold_write = False

                info = handle_info(args, i, tab, if_pattern.group())
                tab = inc_tab(tab)
                force_take_line = end_with_backslash

            elif else_pattern:  # have else_statements
                tab = dec_tab(tab)
                info = handle_info(args, i, tab, else_pattern.group())
                tab = inc_tab(tab)
                force_take_line = end_with_backslash

            elif endif_pattern:  # have endif_statements
                tab = dec_tab(tab)
                info = handle_info(args, i, tab, endif_pattern.group())

            elif include_pattern and tab > 0:  # have include_statements
                info = handle_info(args, i, tab, include_pattern.group())

            elif func_start_pattern and not inside_function:
                inside_function = True
                # wait with writing function name till backports found
                if tab == 0:
                    hold_write = True
                    hold_info = func_start_pattern.group(1)
                # write function name inside #ifdef
                else:
                    info = handle_info(args, i, tab, func_start_pattern.group(1))
                    tab = inc_tab(tab)

            elif func_end_pattern and inside_function:
                # Function doesn't contains backports
                if hold_write:
                    hold_write = False
                    hold_info = ""
                # Function was handled
                else:
                    tab = dec_tab(tab)
                # Function ended
                inside_function = False

            if info:
                backports_tree.append(info)

    return backports_tree


def main():
    args = parse_args()
    if os.path.exists(args.output):
        print(f'-W- File {args.output} will be override')
        clean_file = open(args.output, 'w')
        clean_file.close()
    if args.review:
        review_tree_list = file_parser(args, args.review)
    if args.reference:
        reference_tree_list = file_parser(args, args.reference)
    if args.review and args.reference:
        create_review_diffs(review_tree_list, reference_tree_list)


if __name__ == '__main__':
    main()