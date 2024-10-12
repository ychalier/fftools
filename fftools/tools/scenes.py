import os
from pathlib import Path

from ..tool import Tool


class Scenes(Tool):

    NAME = "scenes"
    DESC = "Extract a thumbnail of every different scene in a video."

    def __init__(self, video_path: str, frames_path: str, bin_width: int = 10,
                 threshold: float = 0.002):
        Tool.__init__(self)
        self.video_path = Path(video_path)
        self.frames_path = Path(frames_path)
        self.bin_width = bin_width
        self.threshold = threshold

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("video_path", type=str, help="Path to the source video")
        parser.add_argument("frames_path", type=str, help="Path to the output folder containing the frames (will be created)")
        parser.add_argument("-b", "--bin-width", type=int, default=10)
        parser.add_argument("-t", "--threshold", type=float, default=0.002)

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["video_path", "frames_path"], ["bin_width", "threshold"])
    
    def extract_keyframes(self):
        self.ffmpeg(
            "-skip_frame", "nokey",
            "-i", self.video_path,
            "-vsync", "vfr",
            "-frame_pts", "true",
            self.frames_path / "%06d.jpg",
        )
    
    def load_frame(self, image_path: Path):
        import numpy, PIL.Image
        bins = list(range(0, 256, self.bin_width))
        with PIL.Image.open(image_path) as file:
            arr = numpy.array(file)
        r = numpy.histogram(numpy.ravel(arr[:,:,0]), bins=bins, density=True)[0]
        g = numpy.histogram(numpy.ravel(arr[:,:,1]), bins=bins, density=True)[0]
        b = numpy.histogram(numpy.ravel(arr[:,:,2]), bins=bins, density=True)[0]
        return numpy.stack([r, g, b])
    
    def frame_comparator(self, left, right) -> bool:
        import numpy
        diff = numpy.average(numpy.abs(left - right))
        return diff < self.threshold
    
    def delete_duplicates(self):
        import tqdm
        paths = sorted(self.frames_path.glob("*.jpg"))
        frame_count = len(paths)
        removed_count = 0
        if not paths:
            return
        current_frame = self.load_frame(paths.pop(0))
        for path in tqdm.tqdm(paths, desc="Removing duplicates"):
            next_frame = self.load_frame(path)
            if self.frame_comparator(current_frame, next_frame):
                os.remove(path)
                removed_count += 1
            else:
                current_frame = next_frame
        print("Removed", removed_count, "of", frame_count, "frames")
    
    def run(self):
        self.frames_path.mkdir(exist_ok=True)
        self.extract_keyframes()
        self.delete_duplicates()
        self.startfile(self.frames_path)