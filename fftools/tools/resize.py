import math
from pathlib import Path
import re
import dataclasses

from ..tool import Tool


def parse_aspect_ratio(string: str | None) -> float | None:
    if string is None:
        return None
    up, down = re.split("[/:]", string)
    return float(up) / float(down)


def parse_bytes(string: str | None) -> int | None:
    if string is None:
        return None
    match = re.match(r"^(\d+)(\.\d+)?([kmg])?[bo]?$", string, re.IGNORECASE)
    if match is None:
        return int(string)
    base = int(match.group(1))
    if match.group(2) is not None:
        base = float(match.group(1) + match.group(2))
    factor = {
        None: 1,
        "k": 1000,
        "m": 1000000,
        "g": 1000000000,
    }[match.group(3)]
    return int(base * factor)


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


@dataclasses.dataclass
class ResizeParameters:
    path: Path
    width: int 
    height: int 
    scale: float
    aspect_ratio: float | None
    fit: str
    expand: bool 
    filter: str
    crop_width: int | None
    crop_height: int | None
    pad_width: int | None
    pad_height: int | None
    base_width: int | None
    base_height: int | None


class Resize(Tool):
    """
    @see https://ffmpeg.org/ffmpeg-filters.html#scale
    @see https://ffmpeg.org/ffmpeg-filters.html#pad
    @see https://ffmpeg.org/ffmpeg-filters.html#crop
    """

    NAME = "resize"

    def __init__(self, input_path: str, width: int | None = None,
                 height: int | None = None, longest_edge: int | None = None,
                 scale: float = 1, aspect_ratio: str | None = None,
                 fit: str = "fill", expand: bool = False,
                 filter: str = "bicubic", bytes_limit: str | None = None,
                 output_folder: str | None = None):
        Tool.__init__(self)
        self.input_path = Path(input_path)
        self.width = width
        self.height = height
        self.longest_edge = longest_edge
        self.scale = scale
        self.aspect_ratio = parse_aspect_ratio(aspect_ratio)
        self.fit = fit
        self.expand = expand
        self.filter = filter
        self.bytes_limit = parse_bytes(bytes_limit)
        self.output_folder = output_folder

    def compute_output_parameters(self, input_path: Path) -> ResizeParameters:
        params = ResizeParameters(
            path=None,
            width=self.width,
            height=self.height,
            scale=self.scale,
            aspect_ratio=self.aspect_ratio,
            fit=self.fit,
            expand=self.expand,
            filter=self.filter,
            crop_width=None,
            crop_height=None,
            pad_width=None,
            pad_height=None,
            base_width=None,
            base_height=None,
        )
        probe_result = self.probe(input_path)
        if self.longest_edge is not None:
            if probe_result.width > probe_result.height:
                params.width = self.longest_edge
                params.height = None
            else:
                params.width = None
                params.height = self.longest_edge
        params.base_width = probe_result.width
        params.base_height = probe_result.height
        if self.bytes_limit is not None:
            params.scale = math.sqrt(self.bytes_limit / probe_result.size)
        base_aspect_ratio = probe_result.width / probe_result.height
        if params.aspect_ratio is None:
            if params.width is not None and params.height is not None:
                params.aspect_ratio = params.width / params.height
            else:
                params.aspect_ratio = base_aspect_ratio
        if params.width is None and params.height is None:
            if params.aspect_ratio >= base_aspect_ratio:
                if params.expand:
                    params.height = probe_result.height
                else:
                    params.width = probe_result.width
            else:
                if params.expand:
                    params.width = probe_result.width
                else:
                    params.height = probe_result.height
        if params.width is not None and params.height is None:
            params.height = params.width / params.aspect_ratio
        if params.width is None and params.height is not None:
            params.width = params.height * params.aspect_ratio
        params.width = round(params.width * params.scale)
        params.height = round(params.height * params.scale)
        params.path = input_path.with_stem(input_path.stem + f"_{params.width}_{params.height}")
        if self.output_folder is not None:
            params.path = self.output_folder / params.path.name
        params.crop_width = probe_result.width
        params.crop_height = probe_result.height
        if params.fit == "cover":
            if params.aspect_ratio > base_aspect_ratio:
                params.crop_height = probe_result.width / params.aspect_ratio
            elif params.aspect_ratio < base_aspect_ratio:
                params.crop_width = probe_result.height * params.aspect_ratio
        params.pad_width = probe_result.width
        params.pad_height = probe_result.height
        if params.fit == "contain":
            if params.aspect_ratio < base_aspect_ratio:
                params.pad_height = probe_result.width / params.aspect_ratio
            elif params.aspect_ratio > base_aspect_ratio:
                params.pad_width = probe_result.height * params.aspect_ratio
        return params

    def process_file(self, input_path: Path, params: ResizeParameters):
        vf = ""
        if params.fit == "cover":
            vf += f"crop={params.crop_width}:{params.crop_height},"
        elif params.fit == "contain":
            vf += f"pad={params.pad_width}:{params.pad_height}:(ow-iw)/2:(oh-ih)/2,"
        vf += f"scale={params.width}:{params.height}:flags={params.filter}"
        self.ffmpeg(
            "-i",
            input_path,
            "-vf",
            vf,
            params.path,
        )

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("input_path", type=str, help="input path")
        parser.add_argument("-w", "--width", type=int, default=None, help="target width in pixels")
        parser.add_argument("-g", "--height", type=int, default=None, help="target height in pixels")
        parser.add_argument("-d", "--longest-edge", type=int, default=None, help="longest edge size in pixels")
        parser.add_argument("-s", "--scale", type=float, default=1, help="scaling factor")
        parser.add_argument("-a", "--aspect-ratio", type=str, default=None, help="target aspect ratio")
        parser.add_argument("-f", "--fit", type=str, default="fill", choices=["fill", "cover", "contain"])
        parser.add_argument("-e", "--expand", action="store_true")
        parser.add_argument("-l", "--filter", type=str, default="bicubic", choices=RESIZE_FILTERS)
        parser.add_argument("-b", "--bytes-limit", type=str, default=None, help="maximum file size (roughly)")
        parser.add_argument("-o", "--output-folder", type=str, default=None, help="output folder")

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["input_path"], ["width", "height", "longest_edge", "scale", "aspect_ratio", "fit", "expand", "filter", "bytes_limit", "output_folder"])     
    
    def run(self):
        input_paths = self.parse_source_paths([self.input_path])
        for input_path in input_paths:
            params = self.compute_output_parameters(input_path)
            self.process_file(input_path, params)
        if len(input_paths) == 1:
            self.startfile(params.path)
