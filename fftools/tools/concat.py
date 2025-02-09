import pathlib

from ..tool import ManyToOneTool
from .. import utils


class Concat(ManyToOneTool):
    """
    @see https://trac.ffmpeg.org/wiki/Concatenate
    """

    NAME = "concat"
    DESC = "Concatenate multiple video files into one video file."

    def __init__(self, copy: bool = False):
        ManyToOneTool.__init__(self)
        self.copy = copy

    @staticmethod
    def add_arguments(parser):
        ManyToOneTool.add_arguments(parser)
        parser.add_argument("-c", "--copy", action="store_true", help="directly copy streams instead of reencoding them (faster but does not handle various sizes well)")
    
    def process(self, input_paths: list[pathlib.Path], output_path: pathlib.Path):
        with utils.tempdir() as folder:
            listpath = folder / "list.txt"
            with listpath.open("w") as file:
                for source_path in input_paths:
                    file.write(f"file '{source_path.absolute()}'\n")
            args = [
                "-f", "concat",
                "-safe", "0",
                "-i", listpath
            ]
            if self.copy:
                args += ["-c", "copy"]
            args.append(output_path)
            utils.ffmpeg(*args)
