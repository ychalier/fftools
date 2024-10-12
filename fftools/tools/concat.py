from pathlib import Path

from ..tool import Tool


class Concat(Tool):
    """
    @see https://trac.ffmpeg.org/wiki/Concatenate
    """

    NAME = "concat"
    DESC = "Concatenate multiple video files into one video file."

    def __init__(self, output_path: str, source_paths: str, copy: bool = False):
        Tool.__init__(self)
        self.output_path = Path(output_path)
        self.source_paths = self.parse_source_paths(source_paths)
        self.copy = copy

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("output_path", type=str, help="output path")
        parser.add_argument("source_paths", type=str, nargs="+", help="source paths")
        parser.add_argument("-c", "--copy", action="store_true", help="directly copy streams instead of reencoding them (faster but does not handle various sizes well)")

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["output_path", "source_paths"], ["copy"])     
    
    def run(self):
        with Tool.tempdir() as folder:
            listpath = folder / "list.txt"
            with listpath.open("w") as file:
                for source_path in self.source_paths:
                    file.write(f"file '{source_path.absolute()}'\n")
            args = [
                "-f", "concat",
                "-safe", "0",
                "-i", listpath
            ]
            if self.copy:
                args += ["-c", "copy"]
            args.append(self.output_path)
            self.ffmpeg(*args)
        self.startfile(self.output_path)
