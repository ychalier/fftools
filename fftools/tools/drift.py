import math
import pathlib
import random

from ..tool import OneToOneTool
from .. import utils


class Drift(OneToOneTool):

    NAME = "drift"
    DESC = "Pixel wise retiming"
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_drift{suffix}"

    def __init__(self,
            template: str):
        OneToOneTool.__init__(self, template)
        self.buffer_length: int = 150
        # self.coherence: float = 2
        # self.scale: int = 1
        # self.sigma: float = 50

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)

    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        import numpy
        from scipy.ndimage import gaussian_filter
        output_path = self.inflate(input_path, {})
        with utils.VideoInput(input_path) as vin:
            # c_height = math.ceil(vin.height / self.scale)
            # c_width = math.ceil(vin.width / self.scale)
            # cursors = numpy.zeros((c_height, c_width), dtype=numpy.int32)
            cursors = numpy.zeros((vin.height, vin.width), dtype=numpy.int32)
            diff = numpy.zeros((vin.height, vin.width), dtype=numpy.float32)
            buffer_start = 0
            with utils.VideoOutput(output_path, vin.width, vin.height, vin.framerate, vin.length) as vout:
                buffer = []
                while len(buffer) < self.buffer_length:
                    buffer.append(next(vin))
                buffer = numpy.array(buffer)
                rows, cols = numpy.indices((vin.height, vin.width))
                for n in range(vin.length):
                    # cursors_large = numpy.repeat(
                    #     numpy.repeat(cursors, self.scale, axis=0),
                    #     self.scale, axis=1
                    # )[0:vin.height,0:vin.width]
                    frame = buffer[cursors - buffer_start, rows, cols, :]
                    vout.feed(frame)
                    try:
                        buffer = numpy.concatenate([buffer[1:], next(vin)[None, ...]], axis=0)
                    except StopIteration:
                        buffer = buffer[1:]
                    buffer_start += 1
                    min_cursor = numpy.clip(cursors, buffer_start, None)
                    max_cursor = buffer_start + buffer.shape[0] - 1
                    if random.random() < .1:
                        ci = math.floor(random.random() * vin.height)
                        cj = math.floor(random.random() * vin.width)
                        radius = random.random() * vin.height
                        dist2 = (cols - cj) ** 2 + (rows - ci) ** 2
                        gauss = 10 * random.random() * numpy.exp(-dist2 / (2 * radius ** 2))
                        diff += gauss
                    diff *= 0.9
                    cursors = numpy.floor(diff + buffer_start).astype(numpy.int32)
                    # rand = numpy.random.normal(buffer_start, self.buffer_length / self.coherence, (c_height, c_width))
                    # rand_smooth = gaussian_filter(rand, sigma=self.sigma)
                    # cursors = numpy.round(rand_smooth).astype(numpy.int32)
                    cursors = numpy.clip(cursors, min_cursor, max_cursor)
        return output_path
