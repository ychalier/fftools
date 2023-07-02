import glob
import os
import tempfile

from ..tool import Tool


def parse_source_paths(argstrings):
    source_paths = []
    for argstring in argstrings:
        if os.path.isfile(argstring):
            source_paths.append(argstring)
        elif os.path.isdir(argstring):
            for filename in next(os.walk(argstring))[2]:
                source_paths.append(os.path.join(argstring, filename))
        else:
            source_paths += glob.glob(argstring)
    return source_paths


class Concat(Tool):
    """
    @see https://trac.ffmpeg.org/wiki/Concatenate
    """

    NAME = "concat"

    def __init__(self, output_path, source_paths, copy=False):
        Tool.__init__(self)
        self.output_path = output_path
        self.source_paths = parse_source_paths(source_paths)
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
        with tempfile.TemporaryDirectory() as folder:
            listpath = os.path.join(folder, "list.txt")
            with open(listpath, "w") as file:
                for source_path in self.source_paths:
                    file.write(f"file '{os.path.realpath(source_path)}'\n")
            args = [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                listpath
            ]
            if self.copy:
                args += ["-c", "copy"]
            args += [self.output_path, "-y"]
            self.ffmpeg(*args)
        self.startfile(self.output_path)
