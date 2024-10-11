from pathlib import Path
import re

import numpy
import PIL.Image

from ..tool import Tool


def parse_arg_duration(duration_string: str) -> str:
    match = re.match(r"^\d+$", duration_string)
    if match is not None:
        total_seconds = int(duration_string)
    else:
        up, down = duration_string.split("/")
        total_seconds = float(up) / float(down)
    return Tool.fts(total_seconds)


OPERATIONS = {
    "average": lambda a: numpy.average(a, axis=0),
    "brighter": lambda a: numpy.max(a, axis=0),
    "darker": lambda a: numpy.min(a, axis=0),
    "sum": lambda a: numpy.sum(a, axis=0),
    "difference": lambda a: a[0] - numpy.sum(a[1:], axis=0),
}


class Blend(Tool):

    NAME = "blend"

    def __init__(self, video_path: str, image_path: str,
                 operation: str = "average", start: str = "00:00:00",
                 duration: str = "1/10"):
        Tool.__init__(self)
        self.video_path = Path(video_path)
        self.image_path = Path(image_path)
        self.operation = operation
        if self.operation not in OPERATIONS:
            raise ValueError(f"Illegal operation '{self.operation}'")
        self.start = start
        self.duration = parse_arg_duration(duration)

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("video_path", type=str, help="Path to the source video")
        parser.add_argument("image_path", type=str, help="Path to the output image")
        parser.add_argument("-o", "--operation", type=str, help="Operation to blend the images together", default="average", choices=OPERATIONS.keys())
        parser.add_argument("-s", "--start", type=str, help="Starting timestamp, in FFMPEG format (HH:MM:SS.FFF)", default="00:00:00.000")
        parser.add_argument("-d", "--duration", type=str, help="Exposure duration as a camera setting in seconds (1/100, 1/10, 1/4, 2, 30, ...)", default="1/10")

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["video_path", "image_path"], ["operation", "start", "duration"])
    
    def extract_frames(self, folder: Path):
        self.ffmpeg(
            "-i",
            self.video_path,
            "-ss",
            self.start,
            "-t",
            self.duration,
            folder / "%06d.png",
        )

    def merge_frames(self, folder: Path):
        frame_paths = list(filter(lambda p: p.is_file(), folder.glob("*")))
        if not frame_paths:
            raise FileNotFoundError("No frame to merge")
        images = []
        for frame_path in frame_paths:
            with PIL.Image.open(frame_path) as file:
                images.append(numpy.array(file))
        stack = numpy.array(images)
        merger = OPERATIONS[self.operation](stack)
        PIL.Image.fromarray(numpy.uint8(merger)).save(self.image_path)
    
    def run(self):
        with Tool.tempdir() as folder:
            self.extract_frames(folder)
            self.merge_frames(folder)
        self.startfile(self.image_path)