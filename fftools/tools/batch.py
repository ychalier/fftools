import pathlib
import shlex

from ..tool import OneToOneTool
from .. import utils


class Batch(OneToOneTool):

    NAME = "batch"
    DESC = "FFmpeg wrapper"
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}{suffix}"

    def __init__(self, template: str, args: str):
        OneToOneTool.__init__(self, template)
        self.args: list[str] = shlex.split(args)

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("args", type=str, nargs="?", default="", help="arguments to pass to FFmpeg")

    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        output_path = self.inflate(input_path)
        utils.ffmpeg(
            "-i", input_path.as_posix(),
            *self.args,
            output_path.as_posix()
        )
        return output_path
