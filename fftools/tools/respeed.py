import pathlib

from ..tool import OneToOneTool
from .. import utils


def parse_target(target: str, probe: utils.FFProbeResult):
    import re
    if re.match(r"^x(\d+)(\.\d+)?$", target.strip()):
        return float(target.strip()[1:])
    duration = utils.parse_duration(target)
    if probe.duration is None:
        raise ValueError("Video has no duration")
    return probe.duration / duration


def format_number(x: int | float) -> str:
    if int(x) == x:
        return str(int(x))
    return "%.2f" % x


class Respeed(OneToOneTool):

    NAME = "respeed"
    DESC = "Change the playback speed of a video, with smart features."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_x{speedup}{suffix}"

    def __init__(self, template: str, target: str, raw: bool = False):
        OneToOneTool.__init__(self, template)
        self.target = target
        self.raw = raw

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("target", type=str, help="target speedup (xF) or duration (HH:MM:SS.FFF)")
        parser.add_argument("-r", "--raw", action="store_true", help="lossless (raw bitstream method, for H264)")

    def process(self, input_file: utils.InputFile) -> pathlib.Path:
        speedup = parse_target(self.target, input_file.probe)
        output_path = self.inflate(input_file.path, {"speedup": f"{speedup:.1f}"})
        if self.raw:
            with utils.tempdir() as folder:
                utils.ffmpeg(
                    "-i", input_file.path,
                    "-map", "0:v",
                    "-c:v", "copy",
                    "-bsf:v", "h264_mp4toannexb",
                    folder / "raw.h264",
                    show_stats=not self.quiet
                )
                utils.ffmpeg(
                    "-fflags", "+genpts",
                    "-r", str(input_file.probe.framerate * speedup),
                    "-i", folder / "raw.h264",
                    "-c:v", "copy",
                    output_path,
                    show_stats=not self.quiet
                )
        else:
            utils.ffmpeg(
                "-i", input_file.path,
                "-an",
                "-vf", f"setpts={1/speedup}*PTS",
                output_path,
                show_stats=not self.quiet
            )
        return output_path
