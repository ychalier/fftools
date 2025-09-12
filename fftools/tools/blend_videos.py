import contextlib
import pathlib
import warnings

from ..tool import ManyToOneTool
from .. import utils


class BlendVideos(ManyToOneTool):

    NAME = "blend-videos"
    DESC = "Blend multiple videos into one."

    def __init__(self,
            operation: str = "average",
            time_start: str | None = None,
            time_end: str | None = None,
            duration: str | None = None,
            framerate: float | None = None,
            offline: bool = False):
        ManyToOneTool.__init__(self)
        self.time_start = time_start
        self.time_end = time_end
        self.duration = duration
        self.opname = operation
        self.framerate = framerate
        self.offline = offline
        self.operation = utils.getop(operation)

    @staticmethod
    def add_arguments(parser):
        ManyToOneTool.add_arguments(parser)
        parser.add_argument("-p", "--operation", type=str, help="Operation to blend the images together", default="average", choices=["average", "brighter", "darker", "sum", "difference", "random"])
        parser.add_argument("-ss", "--time-start", type=str, help="Starting timestamp, in FFMPEG format (HH:MM:SS.FFF)", default=None)
        parser.add_argument("-to", "--time-end", type=str, help="Ending timestamp, in FFMPEG format (HH:MM:SS.FFF)", default=None)
        parser.add_argument("-t", "--duration", type=str, help="Duration of the clip to extract, in FFMPEG format (HH:MM:SS.FFF)", default=None)
        parser.add_argument("-r", "--framerate", type=float, help="Framerate output (used if all inputs are folders)", default=None)
        parser.add_argument("--offline", action="store_true", help="Use offline frame extraction (as files), which is slower but less RAM intensive")

    def _process_online(self, input_paths: list[pathlib.Path], output_path: pathlib.Path):
        import numpy
        video_inputs = [utils.VideoInput(input_path) for input_path in input_paths]
        if not video_inputs:
            return
        with contextlib.ExitStack() as stack:
            for video_input in video_inputs:
                stack.enter_context(video_input)
            min_length = min(vin.length for vin in video_inputs)
            with utils.VideoOutput(output_path, video_inputs[0].width, video_inputs[0].height, video_inputs[0].framerate, min_length) as vout:
                while True:
                    frames: list[numpy.ndarray] = []
                    stop = False
                    for video_input in video_inputs:
                        try:
                            frames.append(next(video_input))
                        except StopIteration:
                            stop = True
                            break
                    if stop:
                        break
                    vout.feed(self.operation(numpy.array(frames)))

    def _process_offline(self, input_paths: list[pathlib.Path], output_path: pathlib.Path):
        import numpy, PIL.Image
        with utils.tempdir() as temp_root:
            folders: list[pathlib.Path] = []
            width, height, framerate = None, None, None

            for i, input_path in enumerate(input_paths):
                if input_path.is_dir():
                    folders.append(input_path)
                    continue
                if width is None:
                    probe = utils.ffprobe(input_path)
                    width = probe.width
                    height = probe.height
                    framerate = probe.framerate
                temp_folder = temp_root / f"{i}"
                temp_folder.mkdir()
                cmd = ["-i", input_path]
                if self.time_start is not None:
                    cmd += ["-ss", self.time_start]
                if self.time_end is not None:
                    cmd += ["-to", self.time_end]
                if self.duration is not None:
                    cmd += ["-t", self.duration]
                template = temp_folder / "%09d.png"
                cmd += [template]
                utils.ffmpeg(*cmd)
                folders.append(temp_folder)
            if not folders:
                warnings.warn("No input found")
                return
            min_size = min([len(list(folder.glob("*.png"))) for folder in folders])
            if min_size == 0:
                warnings.warn("(At least) one input is empty")
                return
            if width is None:
                if self.framerate is None:
                    raise ValueError("Please provide a framerate")
                image = PIL.Image.open(folders[0] / f"{1:09d}.png")
                width = image.width
                height = image.height
                framerate = self.framerate
            if height is None or framerate is None:
                raise ValueError("Some video output parameters are not defined")
            with utils.VideoOutput(output_path, width, height, framerate, min_size) as vout:
                for j in range(min_size):
                    frames = []
                    for folder in folders:
                        frame = PIL.Image.open(folder / f"{(j+1):09d}.png")
                        frames.append(frame)
                    vout.feed(self.operation(numpy.array(frames)))

    def process(self, input_paths: list[pathlib.Path], output_path: pathlib.Path):
        if self.offline:
            self._process_offline(input_paths, output_path)
        else:
            self._process_online(input_paths, output_path)
