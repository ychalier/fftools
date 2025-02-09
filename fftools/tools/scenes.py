import os
import pathlib

from ..tool import OneToOneTool
from .. import utils


class Scenes(OneToOneTool):

    NAME = "scenes"
    DESC = "Extract a thumbnail of every different scene in a video."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}-scenes"

    def __init__(self,
            template: str,
            bin_width: int = 10,
            threshold: float = 0.002):
        OneToOneTool.__init__(self, template)
        self.bin_width = bin_width
        self.threshold = threshold

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-b", "--bin-width", type=int, default=10)
        parser.add_argument("-t", "--threshold", type=float, default=0.002)
    
    def _extract_keyframes(self, input_path: pathlib.Path, output_path: pathlib.Path):
        utils.ffmpeg(
            "-skip_frame", "nokey",
            "-i", input_path,
            "-vsync", "vfr",
            "-frame_pts", "true",
            output_path / "%06d.png",
        )
    
    def _load_frame(self, image_path: pathlib.Path):
        import numpy, PIL.Image
        bins = list(range(0, 256, self.bin_width))
        with PIL.Image.open(image_path) as file:
            arr = numpy.array(file)
        r = numpy.histogram(numpy.ravel(arr[:,:,0]), bins=bins, density=True)[0]
        g = numpy.histogram(numpy.ravel(arr[:,:,1]), bins=bins, density=True)[0]
        b = numpy.histogram(numpy.ravel(arr[:,:,2]), bins=bins, density=True)[0]
        return numpy.stack([r, g, b])
    
    def _frame_comparator(self, left, right) -> bool:
        import numpy
        diff = numpy.average(numpy.abs(left - right))
        return diff < self.threshold
    
    def _delete_duplicates(self, output_path: pathlib.Path):
        import tqdm
        paths = sorted(output_path.glob("*.png"))
        frame_count = len(paths)
        removed_count = 0
        if not paths:
            return
        current_frame = self._load_frame(paths.pop(0))
        for path in tqdm.tqdm(paths, desc="Removing duplicates"):
            next_frame = self._load_frame(path)
            if self._frame_comparator(current_frame, next_frame):
                os.remove(path)
                removed_count += 1
            else:
                current_frame = next_frame
        print("Removed", removed_count, "of", frame_count, "frames")
    
    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        output_path = self.inflate(input_path)
        output_path.mkdir(exist_ok=True)
        self._extract_keyframes(input_path, output_path)
        self._delete_duplicates(output_path)
        return output_path
