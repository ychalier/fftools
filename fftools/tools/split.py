import math
import pathlib

from ..tool import OneToOneTool
from .. import utils


class Split(OneToOneTool):

    NAME = "split"
    DESC = "Split a video file into parts of same duration."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_{i}{suffix}"

    def __init__(self,
            template: str,
            parts: int | None = None,
            duration: str | None = None):
        OneToOneTool.__init__(self, template)
        self.parts = parts
        self.duration = None if duration is None else utils.parse_duration(duration)
        if self.parts is None and self.duration is None:
            raise ValueError("Parts or duration should be specified")

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-p", "--parts", type=int, default=None, help="number of parts to split into")
        parser.add_argument("-d", "--duration", type=str, default=None, help="limit duration")

    def _compute_stops(self, duration: float) -> list[float]:
        stops = []
        limit = self.duration if self.parts is None else duration / self.parts
        t = 0
        while t < duration + limit:
            stops.append(min(duration, t))
            t += limit
        return stops

    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        probe_result = utils.ffprobe(input_path)
        stops = self._compute_stops(probe_result.duration)
        padi = max(1, math.ceil(math.log10(len(stops) - 1)))
        for i, (time_start, time_end) in enumerate(zip(stops, stops[1:])):
            output_path = self.inflate(input_path, {"i": f"{i:0{padi}d}"})
            utils.ffmpeg(
                "-i", input_path,
                "-ss", utils.format_timestamp(time_start),
                "-to", utils.format_timestamp(time_end),
                output_path
            )
        return output_path.parent
