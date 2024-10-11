import argparse
import contextlib
import json
import glob
import os
import pathlib
import re
import subprocess
import tempfile
import typing

import dateutil.parser


def parse_r_frame_rate(string: str) -> float:
    up, down = string.split("/")
    return float(up) / float(down)


class FFProbeResult(typing.NamedTuple):
    width: int
    height: int
    framerate: float
    duration: float
    size: int
    creation: int


class Tool:

    def __init__(self):
        pass

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        pass

    @classmethod
    def from_keys(cls, args: argparse.Namespace, args_keys: list[str],
                  kwargs_keys: list[str]):
        return cls(
            *[getattr(args, key) for key in args_keys],
            **{key: getattr(args, key) for key in kwargs_keys})
    
    @staticmethod
    def probe(path: pathlib.Path, ffprobe="ffprobe") -> FFProbeResult:
        cmd = [
            ffprobe,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            path
        ]
        result = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout = result.stdout.read()
        data = json.loads(stdout)
        width = None
        height = None
        framerate = None
        duration = None
        size = None
        creation = None
        for stream in data["streams"]:
            if stream["codec_type"] == "video":
                width = stream["width"]
                height = stream["height"]
                framerate = parse_r_frame_rate(stream["r_frame_rate"])
                break
        if "duration" in data["format"]:
            duration = float(data["format"]["duration"])
        size = int(data["format"]["size"])
        if "tags" in data["format"] and "creation_time" in data["format"]["tags"]:
            creation = int(dateutil.parser.parse(data["format"]["tags"]["creation_time"]).timestamp())
        else:
            creation = int(os.path.getctime(path))
        return FFProbeResult(width, height, framerate, duration, size, creation)

    @staticmethod
    def ffmpeg(*args: str, loglevel: str = "error", show_stats: bool = True,
               ffmpeg: str = "ffmpeg", wait: bool = True,
               overwrite: bool = True):
        cmd = [
            ffmpeg,
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
    def format_timestamp(total_seconds: float) -> str:
        h = int(total_seconds / 3600)
        m = int((total_seconds - 3600 * h) / 60)
        s = int((total_seconds - 3600 * h - 60 * m))
        ms = round((total_seconds - 3600 * h - 60 * m - s) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
    
    @staticmethod
    def fts(ts: float) -> str:
        return Tool.format_timestamp(ts)

    def run(self):
        raise NotImplementedError
    
    @staticmethod
    def startfile(path: pathlib.Path | None):
        if path is None:
            return
        if path.exists():
            os.startfile(path)

    @staticmethod
    def parse_source_paths(argstrings: list[str | pathlib.Path]) -> list[pathlib.Path]:
        source_paths = []
        for argstring in argstrings:
            if os.path.isfile(argstring):
                source_paths.append(argstring)
            elif os.path.isdir(argstring):
                for filename in next(os.walk(argstring))[2]:
                    source_paths.append(os.path.join(argstring, filename))
            else:
                source_paths += glob.glob(argstring)
        return [pathlib.Path(path) for path in source_paths]
    
    @staticmethod
    def parse_duration(string: str) -> float:
        m = re.match(r"^(\d+:)?(\d+:)?(\d+)(\.\d+)?$", string)
        seconds = int(m.group(3))
        if m.group(2) is not None:
            seconds += 3600 * int(m.group(1)[:-1]) + 60 * int(m.group(2)[:-1])
        elif m.group(1) is not None:
            seconds += 60 * int(m.group(1)[:-1])
        if m.group(4) is not None:
            seconds += int(m.group(4)[1:].ljust(3, "0")) / 1000
        return seconds
    
    @contextlib.contextmanager
    @staticmethod
    def tempdir():
        with tempfile.TemporaryDirectory() as td:
            yield pathlib.Path(td)