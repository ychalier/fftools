import pathlib

import cv2
import numpy
import tqdm

from ..tool import OneToOneTool
from .. import utils


def filter_random(fft: numpy.ndarray, alpha: float):
    height, width = fft.shape
    fft[numpy.where(numpy.random.random((height, width)) <= alpha)] = 0


def filter_outer(fft: numpy.ndarray, alpha: float):
    height, width = fft.shape
    ralpha = 1 - alpha
    fft[:int(alpha*height),:] = 0
    fft[int(ralpha*height):,:] = 0
    fft[:,:int(alpha*width)] = 0
    fft[:,int(ralpha*width):] = 0


def filter_inner(fft: numpy.ndarray, alpha: float):
    height, width = fft.shape
    i0 = int(height * .5 * (1 - alpha))
    i1 = int(height * .5 * (1 + alpha))
    j0 = int(width * .5 * (1 - alpha))
    j1 = int(width * .5 * (1 + alpha))
    fft[i0:i1,j0:j1] = 0


def filter_scale(fft: numpy.ndarray, alpha: float):
    fft *= alpha


def filter_frame(frame: cv2.Mat | numpy.ndarray, method: str, alpha: float) -> numpy.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    gray = hsv[:,:,2]
    fft = numpy.fft.fft2(gray)
    if method == "random":
        filter_random(fft, alpha)
    if method == "outer":
        filter_outer(fft, alpha)
    if method == "inner":
        filter_inner(fft, alpha)
    if method == "scale":
        filter_scale(fft, alpha)
    return numpy.round(numpy.abs(numpy.fft.ifft2(fft))).astype(numpy.uint8)


def modulate_video(input_path: pathlib.Path, output_path: pathlib.Path, method: str, alpha: float):
    with utils.VideoInput(input_path) as vin:
        with utils.VideoOutput(output_path, vin.width, vin.height, vin.framerate, vin.length) as vout:
            for frame_in in vin:
                frame_out = filter_frame(frame_in, method, alpha)
                vout.feed(cv2.cvtColor(frame_out, cv2.COLOR_GRAY2RGB))


def modulate_image(input_path: pathlib.Path, output_path: pathlib.Path, method: str, alpha: float):
    src = cv2.imread(input_path.as_posix())
    out = filter_frame(src, method, alpha)
    cv2.imwrite(output_path.as_posix(), cv2.cvtColor(out, cv2.COLOR_GRAY2BGR))


class Modulate(OneToOneTool):

    NAME = "modulate"
    DESC = "Apply frequency modulation to images or videos."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_{method}_{alpha}{suffix}"

    def __init__(self,
            template: str,
            method: str,
            alpha: float):
        OneToOneTool.__init__(self, template)
        self.method = method
        self.alpha = float(alpha)

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-m", "--method", type=str, default="outer", help="modulation operation to apply in the frequency space", choices=["outer", "inner", "scale", "random"])
        parser.add_argument("-a", "--alpha", type=float, default=0.01, help="modulation operation parameter")

    def process(self, input_file: utils.InputFile) -> pathlib.Path:
        output_path = self.inflate(input_file.path, {
            "method": self.method,
            "alpha": self.alpha,
        })
        if input_file.path.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".avif"]:
            modulate_image(input_file.path, output_path, self.method, self.alpha)
        else:
            modulate_video(input_file.path, output_path, self.method, self.alpha)
        return output_path
