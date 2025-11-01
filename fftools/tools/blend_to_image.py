import pathlib

from ..tool import OneToOneTool
from .. import utils


class BlendToImage(OneToOneTool):

    NAME = "blend-to-image"
    DESC = "Extract the first frames of a video and merge them into a single image."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_{operation}_{exposure}.png"

    def __init__(self,
            template: str,
            operation: str = "average",
            start_time: str = "00:00:00",
            exposure: str = "1/10"):
        OneToOneTool.__init__(self, template)
        self.start_time = start_time
        self.exposure = exposure
        self.duration = utils.parse_exposure_duration(exposure)
        self.opname = operation
        self.operation = utils.getop(operation)

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-p", "--operation", type=str, help="Operation to blend the frames together", default="average", choices=["average", "brighter", "darker", "sum", "difference", "random"])
        parser.add_argument("-ss", "--start-time", type=str, help="Starting timestamp, in FFMPEG format (HH:MM:SS.FFF)", default="00:00:00.000")
        parser.add_argument("-e", "--exposure", type=str, help="Exposure duration as a camera setting in seconds (1/100, 1/10, 1/4, 2, 30, ...)", default="1/10")

    def _extract_frames(self, input_path: pathlib.Path, folder: pathlib.Path):
        utils.ffmpeg(
            "-i", input_path,
            "-ss", self.start_time,
            "-t", self.duration,
            folder / "%06d.png",
            show_stats=not self.quiet,
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

    def process(self, input_file: utils.InputFile) -> pathlib.Path:
        with utils.tempdir() as folder:
            self._extract_frames(input_file.path, folder)
            output_path = self.inflate(input_file.path, {
                "operation": self.opname,
                "exposure": self.exposure
            })
            self._merge_frames(folder, output_path)
        return output_path
