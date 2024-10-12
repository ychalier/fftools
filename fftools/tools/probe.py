from pathlib import Path

from ..tool import Tool


class Probe(Tool):

    NAME = "probe"
    DESC = "Display information about a media file."

    def __init__(self, input_path: str):
        self.input_path = Path(input_path)

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("input_path", type=str, help="input path")

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["input_path"], [])
    
    def run(self):
        probe_result = self.probe(self.input_path)
        rows = []
        width = 0
        for key, value in zip(probe_result.__annotations__, probe_result):
            width = max(width, len(key))
            rows.append((key, value))
        print(self.input_path)
        for key, value in rows:
            print(key.ljust(width + 3, ".") + str(value))
