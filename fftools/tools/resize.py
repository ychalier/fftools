import os
import re
import types

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

    def compute_output_parameters(self, input_path):
        params = types.SimpleNamespace(
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
        )
        probe_result = self.probe(input_path)
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
        splitext = os.path.splitext(input_path)
        output_path = splitext[0] + f"_{params.width}_{params.height}" + splitext[1]
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
        return params, output_path

    def process_file(self, input_path, params, output_path):
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
            output_path,
        )

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
        input_paths = self.parse_source_paths([self.input_path])
        output_path = None
        for input_path in input_paths:
            params, output_path = self.compute_output_parameters(input_path)
            self.process_file(input_path, params, output_path)
        if len(input_paths) == 1:
            self.startfile(output_path)
