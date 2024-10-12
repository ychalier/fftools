from pathlib import Path

from ..tool import Tool, FFProbeResult
 

def parse_target(target: str, probe: FFProbeResult):
    import re
    if re.match(r"^x(\d+)(\.\d+)?$", target.strip()):     
        return float(target.strip()[1:])
    duration = Tool.parse_duration(target)
    return probe.duration / duration


def format_number(x: int | float) -> str:
    if int(x) == x:
        return str(int(x))
    return "%.2f" % x


class Respeed(Tool):

    NAME = "respeed"
    DESC = "Change the playback speed of a video, with smart features."

    def __init__(self, input_path: str, target: str, raw: bool = False):
        Tool.__init__(self)
        self.input_path = Path(input_path)
        self.probe_result = self.probe(input_path)
        self.speedup = parse_target(target, self.probe_result)
        self.output_path = self.input_path.with_stem(self.input_path.stem + f"x{format_number(self.speedup)}")
        self.raw = raw

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("input_path", type=str, help="input path")
        parser.add_argument("target", type=str, help="target speedup (xF) or duration (HH:MM:SS.FFF)")
        parser.add_argument("-r", "--raw", action="store_true", help="lossless (raw bitstream method, for H264)")

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["input_path", "target"], ["raw"])     
    
    def run(self):
        if self.raw:
            with Tool.tempdir() as folder:
                self.ffmpeg(
                    "-i", self.input_path,
                    "-map", "0:v",
                    "-c:v", "copy",
                    "-bsf:v", "h264_mp4toannexb",
                    folder / "raw.h264"
                )
                self.ffmpeg(
                    "-fflags", "+genpts",
                    "-r", str(self.probe_result.framerate * self.speedup),
                    "-i", folder / "raw.h264",
                    "-c:v", "copy",
                    self.output_path,
                )
        else:
            self.ffmpeg(
                "-i", self.input_path,
                "-an",
                "-vf", f"setpts={1/self.speedup}*PTS",
                self.output_path,
            )
        self.startfile(self.output_path)
