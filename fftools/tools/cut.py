from pathlib import Path

from ..tool import Tool


class Cut(Tool):

    NAME = "cut"

    def __init__(self, input_path: str, max_width: int | None = None,
                 max_height: int | None = None):
        Tool.__init__(self)
        self.input_path = Path(input_path)
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
    
    def process_file(self, input_path: Path):
        """https://ffmpeg.org/ffmpeg-filters.html#crop
        """
        import math
        probe_result = self.probe(input_path)
        width = probe_result.width if self.max_width is None else self.max_width
        height = probe_result.height if self.max_height is None else self.max_height
        rows = math.ceil(probe_result.height / height)
        cols = math.ceil(probe_result.width / width)
        padi = max(1, math.ceil(math.log10(rows)))
        padj = max(1, math.ceil(math.log10(cols)))
        for i in range(rows):
            for j in range(cols):
                a = 10
                output_path = input_path.with_stem(input_path.stem + f"_{i:0{padi}d}_{j:0{padj}d}")
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
