import pathlib
import random

import numpy

from ..tool import OneToOneTool
from .. import utils


class Squeeze(OneToOneTool):

    NAME = "squeeze"
    DESC = "Vertically squeeze a video with an irregular shape."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_squeeze_o{octaves}_r{resolution}_a{amplitude}_s{speed}_p{pad_start}_l{parallel}_d{duplication}_e{seed}{suffix}"

    def __init__(self,
            template: str,
            octaves: int = 4,
            seed: int | None = None,
            resolution: float = 1,
            amplitude: float = 200,
            speed: float = 20,
            pad_start: float = 0.1,
            pad_end: float = 0.1,
            parallel: bool = False,
            duplication: int = 1):
        OneToOneTool.__init__(self, template)
        self.octaves = octaves
        self.seed = seed if seed is not None else random.randint(0, 2 ** 32 - 1)
        self.resolution = resolution / 1000
        self.amplitude = amplitude
        self.speed = speed
        self.pad_start = pad_start
        self.pad_end = pad_end
        self.parallel = parallel
        self.duplication = duplication

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("--seed", type=int, default=None,
            help="random seed")
        parser.add_argument("--octaves", type=int, default=4,
            help="Perlin noise octaves (irregularities/fractal frontier)")
        parser.add_argument("--resolution", type=float, default=1,
            help="Perlin noise resolution, in tile per 1000 pixel")
        parser.add_argument("--amplitude", type=float, default=200,
            help="Perlin noise amplitude, in pixels")
        parser.add_argument("--speed", type=float, default=20,
            help="enveloppe horizontal scrolling speed, in pixels per frame")
        parser.add_argument("--pad-start", type=float, default=0.1,
            help="ratio of the output duration where the squeezing is forced "
            "to 0")
        parser.add_argument("--pad-end", type=float, default=0.1,
            help="ratio of the output duration where the squeezing is forced "
            "to maximum")
        parser.add_argument("--parallel", action="store_true",
            help="force enveloppe top and bottom to be relatively parallel "
            "(height-wise, not noise-wise) at each frame")
        parser.add_argument("--duplication", type=int, default=1,
            help="number of output frame per input frame; this may be used0 "
            "with the `blend-frames` tool with the `--fixed` and `--retime` "
            "flags to recreate motion blur and smoothen the output; this does "
            "not alter output duration but increases output framerate")

    def slopes(self, positions: numpy.ndarray):
        seeds = numpy.bitwise_xor(positions, self.seed * 0x9E3779B97F4A7C15 & 0xFFFFFFFF)
        seeds = (seeds * 0x85EBCA6B) & 0xFFFFFFFF
        return (seeds / 0xFFFFFFFF).astype(numpy.float32) * 2 - 1

    def squeeze(self,
            frame: numpy.ndarray,
            input_length: int,
            input_frame_index: int,
            duplication_index: int,
            width: int,
            height: int) -> numpy.ndarray:
        output_length = input_length * self.duplication
        pad_start = output_length * self.pad_start
        pad_length = output_length * (self.pad_start + self.pad_end)
        j = numpy.arange(width)
        t = input_frame_index * self.duplication + duplication_index
        if self.parallel:
            top = (t - pad_start) / (output_length - pad_length) * height / 2
            bottom = height - (t - pad_start) / (output_length - pad_length) * height / 2
        else:
            top = ((t - pad_start) + j / self.speed) / (output_length - pad_length) * height / 2
            bottom = height - ((t - pad_start) + j / self.speed) / (output_length - pad_length) * height / 2
        x = (j + self.speed * t) * self.resolution
        for octave in range(self.octaves):
            x_scaled = x * (2 ** octave)
            j_left = numpy.floor(x_scaled).astype(int)
            j_right = j_left + 1
            z = x_scaled - j_left
            smoothstep = 3 * z ** 2 - 2 * z ** 3
            slope_a = self.slopes(j_left * self.octaves + octave)
            slope_b = self.slopes(j_right * self.octaves + octave)
            ya = slope_a * smoothstep
            yb = slope_b * (smoothstep - 1)
            top += self.amplitude * 2 ** (-octave) * ((1 - smoothstep) * ya + smoothstep * yb)
            slope_a = self.slopes(j_left * self.octaves + octave + output_length * self.speed)
            slope_b = self.slopes(j_right * self.octaves + octave + output_length * self.speed)
            ya = numpy.multiply(slope_a, smoothstep)
            yb = numpy.multiply(slope_b, (smoothstep - 1))
            bottom += self.amplitude * 2 ** (-octave) * ((1 - smoothstep) * ya + smoothstep * yb)
        imin = numpy.clip(numpy.floor(top), 0, height - 1).astype(int)
        imax = numpy.clip(numpy.floor(bottom), 0, height - 1).astype(int)
        X = numpy.indices((height, width)).transpose(1, 2, 0)
        diff = imax - imin
        where = numpy.where(diff > 0)
        X[:,where,0] = numpy.divide(X[:,where,0] - imin[where], diff[where]) * height
        mask_diff = diff <= 0
        mask_above = X[..., 0] < 0
        mask_below = X[..., 0] >= height
        X[:,:,0] = numpy.clip(X[:,:,0], 0, height - 1)
        out = frame[X[..., 0], X[..., 1]]
        out[:,mask_diff,:] = 0
        out[mask_above] = 0
        out[mask_below] = 0
        return out

    def process(self, input_file: utils.InputFile) -> pathlib.Path:
        output_path = self.inflate(input_file.path, {
            "octaves": self.octaves,
            "seed": self.seed,
            "resolution": self.resolution,
            "amplitude": self.amplitude,
            "speed": self.speed,
            "pad_start": self.pad_start,
            "parallel": self.parallel,
            "duplication": self.duplication,
        })
        with utils.VideoInput(input_file.path) as vin:
            with utils.VideoOutput(output_path, vin.width, vin.height, vin.framerate * self.duplication, vin.length * self.duplication, hide_progress=self.quiet) as vout:
                for input_frame_index, inframe in enumerate(vin):
                    for duplication_index in range(self.duplication):
                        outframe = self.squeeze(inframe, vin.length, input_frame_index, duplication_index, vin.width, vin.height)
                        vout.feed(outframe)
        return output_path
