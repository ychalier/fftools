import math
import pathlib

from ..tool import OneToOneTool
from .. import utils


class Cut(OneToOneTool):

    NAME = "cut"
    DESC = "Cut a media (image or video) in a grid given the size of the cells."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_{row}_{col}{suffix}"

    def __init__(self,
            template: str,
            max_width: int | None = None,
            max_height: int | None = None):
        OneToOneTool.__init__(self, template)
        self.max_width = max_width
        self.max_height = max_height
    
    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-w", "--max-width", type=int, default=None, help="Max slice width")
        parser.add_argument("-g", "--max-height", type=int, default=None, help="Max slice height")
    
    def process(self, input_file: utils.InputFile) -> pathlib.Path:
        """https://ffmpeg.org/ffmpeg-filters.html#crop
        """
        width = input_file.probe.width if self.max_width is None else self.max_width
        height = input_file.probe.height if self.max_height is None else self.max_height
        rows = math.ceil(input_file.probe.height / height)
        cols = math.ceil(input_file.probe.width / width)
        if rows == 0 or cols == 0:
            raise ValueError(f"Output will be empty: rows: {rows}, cols: {cols}")
        padi = max(1, math.ceil(math.log10(rows)))
        padj = max(1, math.ceil(math.log10(cols)))
        output_path = None
        for i in range(rows):
            for j in range(cols):
                output_path = self.inflate(input_file.path, {
                    "row": f"{i:0{padi}d}",
                    "col": f"{j:0{padj}d}"
                })
                utils.ffmpeg(
                    "-i",
                    input_file.path,
                    "-vf",
                    f"crop={width}:{height}:{j * width}:{i * height}",
                    output_path
                )
        assert output_path is not None
        return output_path.parent
