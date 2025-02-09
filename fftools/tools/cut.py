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
        parser.add_argument("-mw", "--max-width", type=int, default=None, help="max slice width")
        parser.add_argument("-mh", "--max-height", type=int, default=None, help="max slice height")
    
    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        """https://ffmpeg.org/ffmpeg-filters.html#crop
        """
        probe_result = utils.ffprobe(input_path)
        width = probe_result.width if self.max_width is None else self.max_width
        height = probe_result.height if self.max_height is None else self.max_height
        rows = math.ceil(probe_result.height / height)
        cols = math.ceil(probe_result.width / width)
        padi = max(1, math.ceil(math.log10(rows)))
        padj = max(1, math.ceil(math.log10(cols)))
        for i in range(rows):
            for j in range(cols):
                output_path = self.inflate(input_path, {
                    "row": f"{i:0{padi}d}",
                    "col": f"{j:0{padj}d}"
                })
                utils.ffmpeg(
                    "-i",
                    input_path,
                    "-vf",
                    f"crop={width}:{height}:{j * width}:{i * height}",
                    output_path
                )
        return output_path.parent
