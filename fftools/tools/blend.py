import pathlib

from ..tool import OneToOneTool
from .. import utils


class Blend(OneToOneTool):

    NAME = "blend"
    DESC = "Blend consecutive frames of a video into a single image."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_blend.png"
    
    def __init__(self,
            template: str,
            operation: str = "average",
            start: str = "00:00:00",
            duration: str = "1/10"):
        OneToOneTool.__init__(self, template)
        self.start = start
        self.duration = utils.parse_fraction_duration(duration)
        self.operation = lambda a: 0
        import numpy
        match operation:
            case "average":
                self.operation = lambda a: numpy.average(a, axis=0)
            case "brighter":
                self.operation = lambda a: numpy.max(a, axis=0)
            case "darker":
                self.operation = lambda a: numpy.min(a, axis=0)
            case "sum":
                self.operation = lambda a: numpy.sum(a, axis=0)
            case "difference":
                self.operation = lambda a: a[0] - numpy.sum(a[1:], axis=0)
            case _:
                raise ValueError(f"Illegal operation '{operation}'")

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-op", "--operation", type=str, help="Operation to blend the images together", default="average", choices=["average", "brighter", "darker", "sum", "difference"])
        parser.add_argument("-s", "--start", type=str, help="Starting timestamp, in FFMPEG format (HH:MM:SS.FFF)", default="00:00:00.000")
        parser.add_argument("-d", "--duration", type=str, help="Exposure duration as a camera setting in seconds (1/100, 1/10, 1/4, 2, 30, ...)", default="1/10")

    def _extract_frames(self, input_path: pathlib.Path, folder: pathlib.Path):
        utils.ffmpeg(
            "-i", input_path.as_posix(),
            "-ss", self.start,
            "-t", self.duration,
            folder / "%06d.png",
        )
    
    def _merge_frames(self, folder: pathlib.Path, output_path: pathlib.Path):
        import numpy, PIL.Image
        frame_paths = list(filter(lambda p: p.is_file(), folder.glob("*")))
        if not frame_paths:
            raise RuntimeError("No frame to merge")
        images = []
        for frame_path in frame_paths:
            with PIL.Image.open(frame_path) as file:
                images.append(numpy.array(file))
        stack = numpy.array(images)
        merger = self.operation(stack)
        PIL.Image.fromarray(numpy.uint8(merger)).save(output_path)
    
    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        with utils.tempdir() as folder:
            self._extract_frames(input_path, folder)
            output_path = self.inflate(input_path)
            self._merge_frames(folder, output_path)
        return output_path