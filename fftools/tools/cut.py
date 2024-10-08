import os
import math

from ..tool import Tool


class Cut(Tool):

    NAME = "cut"

    def __init__(self, input_path, max_width=None, max_height=None):
        Tool.__init__(self)
        self.input_path = input_path
        self.max_width = max_width
        self.max_height = max_height
    
    @staticmethod
    def add_arguments(parser):
        parser.add_argument("input_path", type=str, help="input path")
        parser.add_argument("-mw", "--max-width", type=int, default=None, help="max slice width")
        parser.add_argument("-mh", "--max-height", type=int, default=None, help="max slice height")
    
    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["input_path"], ["max_width", "max_height"])
    
    def process_file(self, input_path):
        """
        https://ffmpeg.org/ffmpeg-filters.html#crop
        """
        probe_result = self.probe(input_path)
        width = probe_result.width if self.max_width is None else self.max_width
        height = probe_result.height if self.max_height is None else self.max_height
        rows = math.ceil(probe_result.height / height)
        cols = math.ceil(probe_result.width / width)
        splitext = os.path.splitext(input_path)
        base_path = splitext[0]
        for i in range(rows):
            for j in range(cols):
                output_path = base_path + f"_{i:02d}_{j:02d}" + splitext[1]
                self.ffmpeg(
                    "-i",
                    input_path,
                    "-vf",
                    f"crop={width}:{height}:{j * width}:{i * height}",
                    output_path
                )

    def run(self):
        input_paths = self.parse_source_paths([self.input_path])
        for input_path in input_paths:
            self.process_file(input_path)
