import dataclasses
import math
import pathlib

from ..tool import OneToOneTool
from .. import utils


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
    width: int | None
    height: int | None
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


class Resize(OneToOneTool):
    """
    @see https://ffmpeg.org/ffmpeg-filters.html#scale
    @see https://ffmpeg.org/ffmpeg-filters.html#pad
    @see https://ffmpeg.org/ffmpeg-filters.html#crop
    """

    NAME = "resize"
    DESC = "Resize any media (image or video), with smart features."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_{fit}_{width}x{height}{suffix}"

    def __init__(self,
            template: str,
            width: int | None = None,
            height: int | None = None,
            longest_edge: int | None = None,
            scale: float = 1,
            aspect_ratio: str | None = None,
            fit: str = "fill",
            expand: bool = False,
            filter: str = "bicubic",
            bytes_limit: str | None = None):
        OneToOneTool.__init__(self, template)
        self.width = width
        self.height = height
        self.longest_edge = longest_edge
        self.scale = scale
        self.aspect_ratio = utils.parse_aspect_ratio(aspect_ratio)
        self.fit = fit
        self.expand = expand
        self.filter = filter
        self.bytes_limit = utils.parse_bytes(bytes_limit)

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-w", "--width", type=int, default=None, help="target width in pixels")
        parser.add_argument("-g", "--height", type=int, default=None, help="target height in pixels")
        parser.add_argument("-d", "--longest-edge", type=int, default=None, help="longest edge size in pixels")
        parser.add_argument("-s", "--scale", type=float, default=1, help="scaling factor")
        parser.add_argument("-a", "--aspect-ratio", type=str, default=None, help="target aspect ratio")
        parser.add_argument("-f", "--fit", type=str, default="fill", choices=["fill", "cover", "contain"])
        parser.add_argument("-e", "--expand", action="store_true")
        parser.add_argument("-l", "--filter", type=str, default="bicubic", choices=RESIZE_FILTERS)
        parser.add_argument("-b", "--bytes-limit", type=str, default=None, help="maximum file size (roughly)")

    def _compute_output_parameters(self, input_path: pathlib.Path) -> ResizeParameters:
        params = ResizeParameters(
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
        probe_result = utils.ffprobe(input_path)
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
        if params.width is not None and params.height is not None:
            params.width = round(params.width * params.scale)
            params.height = round(params.height * params.scale)
        elif params.width is not None and params.height is None:
            params.height = round(params.width / params.aspect_ratio * params.scale)
            params.width = round(params.width * params.scale)
        elif params.width is None and params.height is not None:
            params.width = round(params.height * params.aspect_ratio * params.scale)
            params.height = round(params.height * params.scale)
        else:
            raise ValueError("Could not determine resizing width or height")
        params.crop_width = probe_result.width
        params.crop_height = probe_result.height
        if params.fit == "cover":
            if params.aspect_ratio > base_aspect_ratio:
                params.crop_height = round(probe_result.width / params.aspect_ratio)
            elif params.aspect_ratio < base_aspect_ratio:
                params.crop_width = round(probe_result.height * params.aspect_ratio)
        params.pad_width = probe_result.width
        params.pad_height = probe_result.height
        if params.fit == "contain":
            if params.aspect_ratio < base_aspect_ratio:
                params.pad_height = round(probe_result.width / params.aspect_ratio)
            elif params.aspect_ratio > base_aspect_ratio:
                params.pad_width = round(probe_result.height * params.aspect_ratio)
        return params

    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        params = self._compute_output_parameters(input_path)
        vf = ""
        if params.fit == "cover":
            vf += f"crop={params.crop_width}:{params.crop_height},"
        elif params.fit == "contain":
            vf += f"pad={params.pad_width}:{params.pad_height}:(ow-iw)/2:(oh-ih)/2,"
        vf += f"scale={params.width}:{params.height}:flags={params.filter}"
        output_path = self.inflate(input_path, {
            "width": params.width,
            "height": params.height,
            "scale": params.scale,
            "fit": params.fit,
        })
        utils.ffmpeg(
            "-i", input_path,
            "-vf", vf,
            output_path,
        )
        return output_path
