'''
  python script that order any programing file
'''
import re
import argparse
from difflib import Differ

# Create the parser
from utils.setting_utils import TAB_SIZE


def debug_print(tabs, group, debug):
    if debug:
        print(f"{' ' * tabs}{group}")

def write_into_file(option, number, tabs, data, output_files):
    number_info = f"line {number}:"
    line_info = f"{' ' * tabs}{data}\n"
    if option:
        final_info = number_info + line_info
    else:
        final_info = line_info

    output_files.write(final_info)
    return final_info


def parse_args():
    parser = argparse.ArgumentParser(description='Automatic full file '
                                        'review for defines and functions order')  
    # Add Arguments
    parser.add_argument('--review', type=str, default="",
                        help='Set a file path to review')
    parser.add_argument('--reference', type=str, default="",
                        help='Set a file path to use as reference')
    parser.add_argument('-l', '--with_line_number', action='store_true',
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
        print("Tab tried to go under 0")
        return 0
    else:
        return tab - TAB_SIZE


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

    with open('output.csv', 'w') as output_file:
        with open(work_on_file, 'r') as review_file:
            # reading loop from a programing file
            for i, line in enumerate(review_file.readlines()):
                info = ""
                end_with_backslash = line.endswith('\\\n')
                if force_take_line:
                    debug_print(tab, line, args.debug)
                    info = write_into_file(args.with_line_number, i, tab, line, output_file)
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
                    debug_print(tab, if_pattern.group(), args.debug)
                    info = write_into_file(args.with_line_number, i, tab, if_pattern.group(), output_file)
                    tab = inc_tab(tab)
                    force_take_line = end_with_backslash

                elif else_pattern:  # have else_statements
                    tab = dec_tab(tab)
                    debug_print(tab, else_pattern.group(), args.debug)
                    info = write_into_file(args.with_line_number, i, tab, else_pattern.group(), output_file)
                    tab = inc_tab(tab)
                    force_take_line = end_with_backslash

                elif endif_pattern:  # have endif_statements
                    tab = dec_tab(tab)
                    debug_print(tab, endif_pattern.group(), args.debug)
                    info = write_into_file(args.with_line_number, i, tab, endif_pattern.group(), output_file)

                elif include_pattern and tab > 0:  # have include_statements
                    debug_print(tab, include_pattern.group(), args.debug)
                    info = write_into_file(args.with_line_number, i, tab, include_pattern.group(), output_file)

                elif func_start_pattern and not inside_function:
                    debug_print(tab, func_start_pattern.group(1), args.debug)
                    info = write_into_file(args.with_line_number, i, tab, func_start_pattern.group(1), output_file)
                    tab = inc_tab(tab)
                    inside_function = True

                elif func_end_pattern and inside_function:
                    tab = dec_tab(tab)
                    inside_function = False

                if info:
                    backports_tree.append(info)

    return backports_tree

def create_review_diffs(review, reference):
    d = Differ()
    print(f'reveiw {review}')
    print(f'reference {reference}')
    diff = list(d.compare(reference, review))
    diff_strip = [line for line in diff if not line.startswith('?')]
    with open('reviewer.csv', 'w') as output_file:
        for line in diff_strip:
            print(line)
            output_file.write(line)

def main():
    args = parse_args()
    if args.review:
        review_tree_list = file_parser(args, args.review)
    if args.reference:
        reference_tree_list = file_parser(args, args.reference)
    if args.review and args.reference:
        create_review_diffs(review_tree_list, reference_tree_list)

if __name__ == '__main__':
    main()