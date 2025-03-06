import pathlib

from ..tool import OneToOneTool
from .. import utils


class Convert(OneToOneTool):

    NAME = "convert"
    DESC = "Convert a file"
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}{target}"

    def __init__(self,
            template: str,
            target: str = "mp4"):
        OneToOneTool.__init__(self, template)
        self.target = "." + target

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-t", "--target", type=str, help="Target format", default="mp4")

    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        output_path = self.inflate(input_path, {"target": self.target})
        utils.ffmpeg("-i", input_path, output_path)
        return output_path
