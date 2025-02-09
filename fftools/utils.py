import contextlib
import dataclasses
import glob
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import typing

import dateutil.parser


def expand_paths(argstrings: list[str | pathlib.Path]) -> list[pathlib.Path]:
    """Given a list of string (file paths, folder paths, glob patterns), returns
    a flat list of file paths.
    """
    source_paths = []
    for argstring in argstrings:
        if os.path.isfile(argstring):
            source_paths.append(argstring)
        elif os.path.isdir(argstring):
            for filename in next(os.walk(argstring))[2]:
                source_paths.append(os.path.join(argstring, filename))
        elif isinstance(argstring, str):
            source_paths += glob.glob(argstring)
        elif isinstance(argstring, pathlib.Path):
            source_paths += glob.glob(str(argstring))
        else:
            raise ValueError(f"Invalid argument type {type(argstring)}")
    return [pathlib.Path(path) for path in source_paths]


def ffmpeg(*args: str,
        loglevel: str = "error",
        show_stats: bool = True,
        ffmpeg: str = "ffmpeg",
        wait: bool = True,
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


@dataclasses.dataclass
class FFProbeResult:
    width: int
    height: int
    framerate: float
    duration: float
    size: int
    creation: int


def ffprobe(path: pathlib.Path, ffprobe="ffprobe") -> FFProbeResult:
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
        ct = data["format"]["tags"]["creation_time"]
        creation = int(dateutil.parser.parse(ct).timestamp())
    else:
        creation = int(os.path.getctime(path))
    return FFProbeResult(width, height, framerate, duration, size, creation)


def find_unique_path(base_path: pathlib.Path) -> pathlib.Path:
    path = pathlib.Path(base_path)
    while path.exists():
        m = re.search(r"_(\d+)$", path.stem)
        if m is None:
            path = path.with_stem(path.stem + f"_1")
        else:
            path = path.with_stem(path.stem[:m.start()] + f"_{int(m.group(1))+1}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def escape_path_chars(string: str) -> str:
    return re.sub(r"[\*\"/\\<>:\|]", "", string)


def format_path(template: str, kwargs: dict) -> pathlib.Path:
    return pathlib.Path(template.format(**{
        key: escape_path_chars(str(value))
        for key, value in kwargs.items()
    }))


def format_timestamp(total_seconds: float) -> str:
    h = int(total_seconds / 3600)
    m = int((total_seconds - 3600 * h) / 60)
    s = int((total_seconds - 3600 * h - 60 * m))
    ms = round((total_seconds - 3600 * h - 60 * m - s) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def parse_aspect_ratio(string: str | None) -> float | None:
    if string is None:
        return None
    up, down = re.split(r"[/:]", string)
    return float(up) / float(down)


def parse_bytes(string: str | None) -> int | None:
    if string is None:
        return None
    m = re.match(r"^(\d+)(\.\d+)?([kmg])?[bo]?$", string, re.IGNORECASE)
    if m is None:
        return int(string)
    base = int(m.group(1))
    if m.group(2) is not None:
        base = float(m.group(1) + m.group(2))
    factor = {
        None: 1,
        "k": 1000,
        "m": 1000000,
        "g": 1000000000,
    }[m.group(3)]
    return int(base * factor)


def parse_fraction_duration(duration_string: str) -> str:
    match = re.match(r"^\d+$", duration_string)
    if match is not None:
        total_seconds = int(duration_string)
    else:
        up, down = duration_string.split("/")
        total_seconds = float(up) / float(down)
    return format_timestamp(total_seconds)


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


def parse_r_frame_rate(string: str) -> float:
    up, down = string.split("/")
    return float(up) / float(down)


def startfile(path: pathlib.Path | None) -> None:
    if path is None:
        return
    if path.exists():
        if sys.platform == "win32":
            os.startfile(path)
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, path.as_posix()])


@contextlib.contextmanager
def tempdir() -> typing.Generator[pathlib.Path, typing.Any, None]:
    with tempfile.TemporaryDirectory() as td:
        yield pathlib.Path(td)
