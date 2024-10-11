import argparse

from .tools import TOOL_LIST
from .tool import ArgumentError


HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKCYAN = '\033[96m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(dest="tool")
    for cls in TOOL_LIST:
        subparser = subparsers.add_parser(cls.NAME, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        cls.add_arguments(subparser)
    args = parser.parse_args()
    tool = None
    for cls in TOOL_LIST:
        if args.tool == cls.NAME:
            try:
                tool = cls.from_args(args)
            except ArgumentError as err:
                print(FAIL + f"Argument Error: {err}" + ENDC)
            break
    if tool is None:
        parser.exit(0)
    try:
        tool.run()
    except KeyboardInterrupt:
        print(OKBLUE + "Interrupting" + ENDC)

