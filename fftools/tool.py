import json
import glob
import os
import re
import subprocess
import typing


def parse_r_frame_rate(string):
    up, down = string.split("/")
    return float(up) / float(down)


class FFProbeResult(typing.NamedTuple):
    width: int
    height: int
    framerate: float
    duration: float
    size: int


class Tool:

    def __init__(self):
        pass

    @staticmethod
    def add_arguments(parser):
        pass

    @classmethod
    def from_keys(cls, args, args_keys, kwargs_keys):
        return cls(
            *[getattr(args, key) for key in args_keys],
            **{key: getattr(args, key) for key in kwargs_keys})
    
    @staticmethod
    def probe(path, ffprobe_path="ffprobe"):
        cmd = [
            ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            path
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True)
        data = json.loads(result.stdout)
        width = None
        height = None
        framerate = None
        duration = None
        size = None
        for stream in data["streams"]:
            if stream["codec_type"] == "video":
                width = stream["width"]
                height = stream["height"]
                framerate = parse_r_frame_rate(stream["r_frame_rate"])
                break
        if "duration" in data["format"]:
            duration = float(data["format"]["duration"])
        size = int(data["format"]["size"])
        return FFProbeResult(width, height, framerate, duration, size)

    @staticmethod
    def ffmpeg(*args, loglevel="error", show_stats=True, ffmpeg_path="ffmpeg", 
               wait=True, overwrite=True):
        cmd = [
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            loglevel,
        ]
        if show_stats:
            cmd.append("-stats")
        cmd += args
        if overwrite:
            cmd.append("-y")
        process = subprocess.Popen(cmd)
        if wait:
            process.wait()

    @staticmethod
    def format_timestamp(total_seconds):
        h = int(total_seconds / 3600)
        m = int((total_seconds - 3600 * h) / 60)
        s = int((total_seconds - 3600 * h - 60 * m))
        ms = round((total_seconds - 3600 * h - 60 * m - s) * 1000)
        return f"{str(h).rjust(2, '0')}:{str(m).rjust(2, '0')}:{str(s).rjust(2, '0')}.{str(ms).rjust(3, '0')}"
    
    @staticmethod
    def fts(ts):
        return Tool.format_timestamp(ts)

    def run(self):
        raise NotImplementedError
    
    @staticmethod
    def startfile(path):
        if path is None:
            return
        if os.path.isfile(path) or os.path.isdir(path):
            os.startfile(path)

    @staticmethod
    def parse_source_paths(argstrings):
        source_paths = []
        for argstring in argstrings:
            if os.path.isfile(argstring):
                source_paths.append(argstring)
            elif os.path.isdir(argstring):
                for filename in next(os.walk(argstring))[2]:
                    source_paths.append(os.path.join(argstring, filename))
            else:
                source_paths += glob.glob(argstring)
        return [os.path.realpath(path) for path in source_paths]
    
    @staticmethod
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