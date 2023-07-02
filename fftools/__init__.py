import argparse

from .tools import TOOL_LIST


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
            tool = cls.from_args(args)
            break
    if tool is None:
        parser.exit(0)
    tool.run()

