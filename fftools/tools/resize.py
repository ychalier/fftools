import os
import re

from ..tool import Tool


def parse_aspect_ratio(string):
    up, down = re.split("[/:]", string)
    return float(up) / float(down)


RESIZE_FILTERS = [
    "fast_bilinear",
    "bilinear",
    "bicubic",
    "experimental",
    "neighbor",
    "area",
    "bicublin",
    "gauss",
    "sinc",
    "lanczos",
]


class Resize(Tool):
    """
    @see https://ffmpeg.org/ffmpeg-filters.html#scale
    @see https://ffmpeg.org/ffmpeg-filters.html#pad
    @see https://ffmpeg.org/ffmpeg-filters.html#crop
    """

    NAME = "resize"

    def __init__(self, input_path, width=None, height=None, scale=1, aspect_ratio=None, fit="fill", expand=False, filter="bicubic"):
        Tool.__init__(self)
        self.input_path = input_path
        self.width = width
        self.height = height
        self.scale = scale
        self.aspect_ratio = parse_aspect_ratio(aspect_ratio) if aspect_ratio is not None else None
        self.fit = fit
        self.expand = expand
        self.filter = filter
        self.crop_width = None
        self.crop_height = None
        self.pad_width = None
        self.pad_height = None
        self.probe_result = None
        self.output_path = None

    def compute_output_parameters(self):
        self.probe_result = self.probe(self.input_path)
        base_aspect_ratio = self.probe_result.width / self.probe_result.height
        if self.aspect_ratio is None:
            if self.width is not None and self.height is not None:
                self.aspect_ratio = self.width / self.height
            else:
                self.aspect_ratio = base_aspect_ratio
        if self.width is None and self.height is None:
            if self.aspect_ratio >= base_aspect_ratio:
                if self.expand:
                    self.height = self.probe_result.height
                else:
                    self.width = self.probe_result.width
            else:
                if self.expand:
                    self.width = self.probe_result.width
                else:
                    self.height = self.probe_result.height
        if self.width is not None and self.height is None:
            self.height = self.width / self.aspect_ratio
        if self.width is None and self.height is not None:
            self.width = self.height * self.aspect_ratio
        self.width = round(self.width * self.scale)
        self.height = round(self.height * self.scale)
        splitext = os.path.splitext(self.input_path)
        self.output_path = splitext[0] + f"_{self.width}_{self.height}" + splitext[1]
        self.crop_width = self.probe_result.width
        self.crop_height = self.probe_result.height
        if self.fit == "cover":
            if self.aspect_ratio > base_aspect_ratio:
                self.crop_height = self.probe_result.width / self.aspect_ratio
            elif self.aspect_ratio < base_aspect_ratio:
                self.crop_width = self.probe_result.height * self.aspect_ratio
        self.pad_width = self.probe_result.width
        self.pad_height = self.probe_result.height
        if self.fit == "contain":
            if self.aspect_ratio < base_aspect_ratio:
                self.pad_height = self.probe_result.width / self.aspect_ratio
            elif self.aspect_ratio > base_aspect_ratio:
                self.pad_width = self.probe_result.height * self.aspect_ratio

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("input_path", type=str, help="input path")
        parser.add_argument("-w", "--width", type=int, default=None, help="target width in pixels")
        parser.add_argument("-g", "--height", type=int, default=None, help="target height in pixels")
        parser.add_argument("-s", "--scale", type=float, default=1, help="scaling factor")
        parser.add_argument("-a", "--aspect-ratio", type=str, default=None, help="target aspect ratio")
        parser.add_argument("-f", "--fit", type=str, default="fill", choices=["fill", "cover", "contain"])
        parser.add_argument("-e", "--expand", action="store_true")
        parser.add_argument("-l", "--filter", type=str, default="bicubic", choices=RESIZE_FILTERS)

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["input_path"], ["width", "height", "scale", "aspect_ratio", "fit", "expand", "filter"])     
    
    def run(self):
        self.compute_output_parameters()
        vf = ""
        if self.fit == "cover":
            vf += f"crop={self.crop_width}:{self.crop_height}"
        elif self.fit == "contain":
            vf += f"pad={self.pad_width}:{self.pad_height}:(ow-iw)/2:(oh-ih)/2"
        vf += f",scale={self.width}:{self.height}:flags={self.filter}"
        self.ffmpeg(
            "-i",
            self.input_path,
            "-vf",
            vf,
            self.output_path,
        )
        self.startfile(self.output_path)
