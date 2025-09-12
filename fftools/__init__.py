"""A set of graphical tools built upon FFmpeg and other graphics libraries.
"""
import argparse
import traceback

from .tools import TOOL_LIST


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
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__)
    subparsers = parser.add_subparsers(dest="tool", required=True)
    for cls in TOOL_LIST:
        if cls.NAME is None:
            raise ValueError(f"Class {cls} does not have a valid name")
        subparser = subparsers.add_parser(
            cls.NAME, 
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description=cls.DESC)
        cls.add_arguments(subparser)
    args = parser.parse_args()
    tool_cls = None
    for cls in TOOL_LIST:
        if args.tool == cls.NAME:
            tool_cls = cls
            break
    if tool_cls is None:
        raise ValueError(f"Could not find tool class for tool '{args.tool}'")
    delattr(args, "tool")
    try:
        tool_cls.run(args)
    except KeyboardInterrupt:
        print(OKBLUE + "Interrupting" + ENDC)
    except Exception as err:
        print(FAIL + f"Error: {err}" + ENDC)
        traceback.print_exc()
