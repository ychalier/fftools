import re
import pathlib

from ..tool import ManyToOneTool
from .. import utils


class Merge(ManyToOneTool):

    NAME = "merge"
    DESC = "Merge mulitple images to create a single video file."

    def __init__(self, target: str):
        ManyToOneTool.__init__(self)
        self.target = target
    
    @staticmethod
    def add_arguments(parser):
        ManyToOneTool.add_arguments(parser)
        parser.add_argument("target", type=str, help="video framerate or duration")

    def process(self, input_paths: list[pathlib.Path], output_path: pathlib.Path):
        with utils.tempdir() as folder:
            listpath = folder / "list.txt"
            with listpath.open("w") as file:
                for source_path in input_paths:
                    file.write(f"file '{source_path.absolute()}'\n")
            if re.match(r"^\d+$", self.target):
                framerate = int(self.target)
            else:
                duration = utils.parse_duration(self.target)
                framerate = len(input_paths) / duration
            utils.ffmpeg(
                "-r", str(framerate),
                "-f", "concat",
                "-safe", "0",
                "-i", listpath,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                output_path
            )
