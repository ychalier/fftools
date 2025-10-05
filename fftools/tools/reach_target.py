import pathlib

from ..tool import OneToOneTool
from .. import utils

import numpy
import PIL.Image
from skimage.color import rgb2lab


def cie76_diff(img1: numpy.ndarray, img2: numpy.ndarray) -> numpy.ndarray:
    img1_float = img1.astype(numpy.float32) / 255.0
    img2_float = img2.astype(numpy.float32) / 255.0
    lab1 = rgb2lab(img1_float)
    lab2 = rgb2lab(img2_float)
    delta_e = numpy.linalg.norm(lab1 - lab2, axis=-1).astype(numpy.float32)
    return delta_e


class ReachTarget(OneToOneTool):

    NAME = "reach-target"
    DESC = "TODO"
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_reach_{target_stem}{suffix}"
    
    def __init__(self, template: str):
        OneToOneTool.__init__(self, template)
        self.target_path = pathlib.Path("../transflow/assets/Deer.jpg") # TODO
        self.tol: float = 3 # TODO
    
    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
    
    def process(self, input_path: pathlib.Path) -> pathlib.Path | None:
        output_path = self.inflate(input_path, {"target_stem": self.target_path.stem})
        target = numpy.array(PIL.Image.open(self.target_path))
        with utils.VideoInput(input_path) as vin:
            mask = numpy.zeros((vin.height, vin.width), dtype=numpy.int32)
            with utils.VideoOutput(output_path, vin.width, vin.height, vin.framerate, vin.length) as vout:
                for frame in vin:
                    diff = cie76_diff(frame, target)
                    where = numpy.where(diff < self.tol)
                    mask[where] = 1
                    where = numpy.nonzero(mask)
                    frame[where] = target[where]
                    vout.feed(frame)
        return output_path
