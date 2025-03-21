import pathlib

from ..tool import OneToOneTool, ManyToOneTool
from .. import utils


class Extract(OneToOneTool):

    NAME = "extract"
    DESC = "Extract frames of a video"
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}-frames"

    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        output_path = self.inflate(input_path)
        output_path.mkdir(exist_ok=True)
        utils.ffmpeg(
            "-i", input_path.as_posix(),
            output_path / "%09d.png"
        )
        return output_path