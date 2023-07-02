import os
import re
import tempfile

from ..tool import Tool


def parse_duration(string):
    match = re.match(r"^(\d+:)?(\d+:)?(\d+)(\.\d+)?$", string)
    seconds = int(match.group(3))
    if match.group(2) is not None:
        seconds += 3600 * int(match.group(1)[:-1]) + 60 * int(match.group(2)[:-1])
    elif match.group(1) is not None:
        seconds += 60 * int(match.group(1)[:-1])
    if match.group(4) is not None:
        seconds += int(match.group(4)[1:].ljust(3, "0")) / 1000
    return seconds
    

def parse_target(target, probe):
    if re.match(r"^x(\d+)(\.\d+)?$", target.strip()):     
        return float(target.strip()[1:])
    duration = parse_duration(target)
    return probe.duration / duration


def format_number(x):
    if int(x) == x:
        return str(int(x))
    return "%.2f" % x


class Respeed(Tool):

    NAME = "respeed"

    def __init__(self, input_path, target, raw=False):
        Tool.__init__(self)
        self.input_path = input_path
        self.probe_result = self.probe(input_path)
        self.speedup = parse_target(target, self.probe_result)
        splitext = os.path.splitext(self.input_path)
        self.output_path = splitext[0] + f"x{format_number(self.speedup)}" + splitext[1]
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
            with tempfile.TemporaryDirectory() as folder:
                self.ffmpeg(
                    "-i",
                    self.input_path,
                    "-map",
                    "0:v",
                    "-c:v",
                    "copy",
                    "-bsf:v",
                    "h264_mp4toannexb",
                    os.path.join(folder, "raw.h264")
                )
                self.ffmpeg(
                    "-fflags",
                    "+genpts",
                    "-r",
                    str(self.probe_result.framerate * self.speedup),
                    "-i",
                    os.path.join(folder, "raw.h264"),
                    "-c:v",
                    "copy",
                    self.output_path,
                )
        else:
            self.ffmpeg(
                "-i",
                self.input_path,
                "-an",
                "-vf",
                f"setpts={1/self.speedup}*PTS",
                self.output_path,
            )
        self.startfile(self.output_path)
