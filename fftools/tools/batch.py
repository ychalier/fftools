import pathlib
import shlex

from ..tool import OneToOneTool
from .. import utils


class Batch(OneToOneTool):

    NAME = "batch"
    DESC = "Wrapper to execute FFmpeg commands on multiple files."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}{suffix}"

    def __init__(self, template: str, args: str):
        OneToOneTool.__init__(self, template)
        self.args: list[str] = shlex.split(args)

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("args", type=str, nargs="?", default="", help="arguments to pass to FFmpeg")

    def process(self, input_file: utils.InputFile) -> pathlib.Path:
        output_path = self.inflate(input_file.path)
        utils.ffmpeg(
            "-i", input_file.path,
            *self.args,
            output_path
        )
        return output_path
