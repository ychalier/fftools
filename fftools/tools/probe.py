import dataclasses
import json
import pathlib

from ..tool import OneToOneTool
from .. import utils


class Probe(OneToOneTool):

    NAME = "probe"
    DESC = "Display information about a media file."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}.json"
    
    def __init__(self, template: str, print_output: bool = False):
        OneToOneTool.__init__(self, template)
        self.print = print_output    
    
    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-p", "--print-output", action="store_true", help="print result to stdout")
    
    def process(self, input_path: pathlib.Path) -> pathlib.Path | None:
        probe_result = utils.ffprobe(input_path)
        if self.print:
            rows = []
            width = 0
            for key, value in zip(probe_result.__annotations__, dataclasses.astuple(probe_result)):
                width = max(width, len(key))
                rows.append((key, value))
            print(input_path)
            for key, value in rows:
                print(key.ljust(width + 3, ".") + str(value))
            print("")
        else:
            output_path = self.inflate(input_path)
            with output_path.open("w", encoding="utf8") as file:
                json.dump(dataclasses.asdict(probe_result), file, indent=4)
            return output_path
