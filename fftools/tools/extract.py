import pathlib

from ..tool import OneToOneTool
from .. import utils


class Extract(OneToOneTool):

    NAME = "extract"
    DESC = "Extract frames of a video"
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}-frames"

    def __init__(self,
            template,
            skip_existing: bool = False,
            time_start: str | None = None,
            time_end: str | None = None,
            duration: str | None = None,):
        OneToOneTool.__init__(self, template)
        self.skip_existing = skip_existing
        self.time_start = time_start
        self.time_end = time_end
        self.duration = duration

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-se", "--skip-existing", action="store_true", help="skip if output folder already exists")
        parser.add_argument("-ss", "--time-start", type=str, help="Starting timestamp, in FFMPEG format (HH:MM:SS.FFF)", default=None)
        parser.add_argument("-to", "--time-end", type=str, help="Ending timestamp, in FFMPEG format (HH:MM:SS.FFF)", default=None)
        parser.add_argument("-t", "--duration", type=str, help="Duration of the clip to extract, in FFMPEG format (HH:MM:SS.FFF)", default=None)

    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        output_path = self.inflate(input_path)
        if self.skip_existing and output_path.is_dir():
            return output_path
        output_path.mkdir(exist_ok=True)
        cmd = ["-i", input_path.as_posix()]
        if self.time_start is not None:
            cmd += ["-ss", self.time_start]
        if self.time_end is not None:
            cmd += ["-to", self.time_end]
        if self.duration is not None:
            cmd += ["-t", self.duration]
        utils.ffmpeg(
            *cmd,
            output_path / "%09d.png"
        )
        return output_path