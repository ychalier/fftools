import pathlib
import typing

from ..tool import OneToOneTool, ManyToOneTool
from .. import utils


def weighted_sum(sigma: float) -> typing.Callable:
    import numpy
    def aux(frames):
        n = frames.shape[0]
        weights = numpy.reshape(utils.gauss(n, sigma, True), (n, 1, 1, 1))
        return numpy.sum(numpy.multiply(weights, frames), axis=0)
    return aux


def getop(opname: str) -> typing.Callable:
    import numpy
    match opname:
        case "average":
            return lambda a: numpy.average(a, axis=0)
        case "brighter":
            return lambda a: numpy.max(a, axis=0)
        case "darker":
            return lambda a: numpy.min(a, axis=0)
        case "sum":
            return lambda a: numpy.sum(a, axis=0)
        case "difference":
            return lambda a: a[0] - numpy.sum(a[1:], axis=0)
        case "weight1":
            return weighted_sum(1)
        case "weight3":
            return weighted_sum(3)
        case "weight5":
            return weighted_sum(5)
        case "weight10":
            return weighted_sum(10)
        case _:
            raise ValueError(f"Illegal operation '{opname}'")


class BlendImage(OneToOneTool):

    NAME = "blendi"
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
        self.operation = getop(operation)

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


class BlendFrame(OneToOneTool):

    NAME = "blendf"
    DESC = "Blend consecutive frames of a video into another video."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_{opname}{suffix}"

    def __init__(self,
            template: str,
            operation: str = "average",
            duration: int = 3):
        OneToOneTool.__init__(self, template)
        self.duration = duration
        self.opname = operation
        self.operation = getop(operation)

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-op", "--operation", type=str, help="Operation to blend the images together", default="average", choices=["average", "brighter", "darker", "sum", "difference", "weight1", "weight3", "weight5", "weight10"])
        parser.add_argument("-d", "--duration", type=int, help="Exposure duration as a number of frames", default=3)

    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        import numpy
        output_path = self.inflate(input_path, {
            "opname": self.opname,
            "duration": self.duration
        })
        with utils.VideoInput(input_path) as vin:
            with utils.VideoOutput(output_path, vin.width, vin.height, vin.framerate) as vout:
                frames = []
                for frame in vin:
                    frames.append(frame)
                    while len(frames) > self.duration:
                        frames.pop(0)
                    vout.feed(self.operation(numpy.array(frames)))
                while len(frames) > 1:
                    frames.pop(0)
                    vout.feed(self.operation(numpy.array(frames)))
        return output_path


class BlendVideo(ManyToOneTool):
    
    NAME = "blendv"
    DESC = "Blend multiple videos into one"
    
    def __init__(self,
            operation: str = "average",
            time_start: str | None = None,
            time_end: str | None = None,
            duration: str | None = None):
        ManyToOneTool.__init__(self)
        self.time_start = time_start
        self.time_end = time_end
        self.duration = duration
        self.opname = operation
        self.operation = getop(operation)
    
    @staticmethod
    def add_arguments(parser):
        ManyToOneTool.add_arguments(parser)
        parser.add_argument("-op", "--operation", type=str, help="Operation to blend the images together", default="average", choices=["average", "brighter", "darker", "sum", "difference"])
        parser.add_argument("-ss", "--time-start", type=str, help="Starting timestamp, in FFMPEG format (HH:MM:SS.FFF)", default=None)
        parser.add_argument("-to", "--time-end", type=str, help="Ending timestamp, in FFMPEG format (HH:MM:SS.FFF)", default=None)
        parser.add_argument("-t", "--duration", type=str, help="Duration of the clip to extract, in FFMPEG format (HH:MM:SS.FFF)", default=None)
    
    def process(self, input_paths: list[pathlib.Path], output_path: pathlib.Path):
        import numpy, PIL.Image
        
        with utils.tempdir() as temp_root:
            min_size = None
            probe = None
            
            """
            TODO: add an extract tool to extract frames from one or multiple videos.
            Then, make it so that if the input path is a folder, we expect it to contain frames.
            This way, one may reuse the extracted frames from a previous run.
            If if it a video, we extract it as before.
            """
            
            # 1. Extract frames of each input video
            for i, input_path in enumerate(input_paths):
                if probe is None:
                    probe = utils.ffprobe(input_path)
                temp_folder = temp_root / f"{i}"
                temp_folder.mkdir()
                cmd = ["-i", input_path.as_posix()]
                if self.time_start is not None:
                    cmd += ["-ss", self.time_start]
                if self.time_end is not None:
                    cmd += ["-to", self.time_end]
                if self.duration is not None:
                    cmd += ["-t", self.duration]
                template = temp_folder / "%09d.png"
                cmd += [template.as_posix()]
                utils.ffmpeg(*cmd)
                size = len(list(temp_folder.glob("*.png")))
                if min_size is None or size < min_size:
                    min_size = size
                        
            # 2. Build the output video by blending the frames
            with utils.VideoOutput(output_path, probe.width, probe.height, probe.framerate) as vout:
                for j in range(min_size):
                    frames = []
                    for i, input_path in enumerate(input_paths):
                        frame = PIL.Image.open(temp_root / f"{i}" / f"{(j+1):09d}.png")
                        frames.append(frame)
                    vout.feed(self.operation(numpy.array(frames)))
