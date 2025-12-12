import contextlib
import dataclasses
import glob
import json
import math
import os
import pathlib
import random
import re
import subprocess
import sys
import tempfile
import typing

import dateutil.parser
import tqdm


def generate_nonce(length: int) -> str:
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.choice(chars) for _ in range(length))


class InputFile:
    
    def __init__(self, path: pathlib.Path, trim_start: str | None = None, trim_end: str | None = None):
        self.path: pathlib.Path = path
        self.real_path: pathlib.Path = path
        self.trim_start: str | None = trim_start
        if self.trim_start == "":
            self.trim_start = None
        self.trim_end: str | None = trim_end
        if self.trim_end == "":
            self.trim_end = None
        self._probe: 'FFProbeResult | None' = None
    
    @property
    def probe(self) -> 'FFProbeResult':
        if self._probe is None:
            self._probe = ffprobe(self.path)
        return self._probe
    
    def __eq__(self, value: object) -> bool:
        if isinstance(value, InputFile):
            return self.path == value.path
        return False
    
    def __lt__(self, value: object):
        if isinstance(value, InputFile):
            return self.path < value.path
        raise TypeError()

    def preprocess(self, use_temporary_file: bool = True):
        if self.trim_start is None and self.trim_end is None:
            return
        if self.path.is_dir():
            return
        start_frame = 0
        start_timestamp = None
        if self.trim_start is not None:
            if re.match(r"^\d+$", self.trim_start):
                start_frame = int(self.trim_start)
                start_timestamp = format_timestamp(start_frame / self.probe.framerate)
            else:
                start_frame = int(parse_timestamp(self.trim_start) * self.probe.framerate)
                start_timestamp = self.trim_start
        end_frame = -1
        end_timestamp = None
        if self.probe.duration is not None:
            end_frame = int(self.probe.duration * self.probe.framerate)
        if self.trim_end is not None:
            if re.match(r"^\d+$", self.trim_end):
                end_frame = int(self.trim_end)
                end_timestamp = format_timestamp(end_frame / self.probe.framerate)
            else:
                end_frame = int(parse_timestamp(self.trim_end) * self.probe.framerate)
                end_timestamp = self.trim_end
        self.path = self.real_path.with_stem(f"{self.real_path.stem}_{start_frame}-{end_frame}")
        print(f"Trimming {self.real_path.name} to [{start_frame}, {end_frame}]")
        if use_temporary_file:
            nonce = generate_nonce(4)
            self.path = pathlib.Path(tempfile.gettempdir()) / f"{nonce}_{self.path.name}"
        command = []
        if start_timestamp is not None:
            command += ["-ss", start_timestamp]
        if end_timestamp is not None:
            command += ["-to", end_timestamp]
        ffmpeg("-i", self.real_path, *command, self.path)
        self._probe = None


def expand_paths(argstrings: list[str], sort: bool = False) -> list[InputFile]:
    """Given a list of string (file paths, folder paths, glob patterns), returns
    a flat list of file inputs.
    """
    trim_pattern = re.compile(r"^(.*?)(?:#([\d:\.]*)\-([\d:\.]*))?$")
    inputs: list[InputFile] = []
    smart_filters = [
        lambda path: os.path.basename(path) != "desktop.ini",
        lambda path: not os.path.isdir(path)
    ]
    for argstring in argstrings:
        m = trim_pattern.match(argstring)
        trim_start = None
        trim_end = None
        if m is not None:
            argstring = m.group(1)
            trim_start = m.group(2)
            trim_end = m.group(3)
        new_paths = []
        if os.path.isfile(argstring):
            new_paths = [argstring]
        elif os.path.isdir(argstring):
            for filename in next(os.walk(argstring))[2]:
                new_paths.append(os.path.join(argstring, filename))
        else:
            new_paths = glob.glob(argstring)
        if not new_paths:
            raise FileNotFoundError(argstring)
        for f in smart_filters:
            new_paths = filter(f, new_paths)
        inputs += [InputFile(pathlib.Path(path), trim_start, trim_end) for path in new_paths]
    if sort:
        inputs.sort()
    return inputs


def is_image(path: pathlib.Path) -> bool:
    return path.suffix.lower() in [".jpg", ".jpeg", ".apng", ".png", ".avif", ".bmp", ".tiff", ".dng", ".webp", ".tif"]


def is_video(path: pathlib.Path) -> bool:
    return path.suffix.lower() in [".mp4", ".avi", ".mov", ".mkv", ".flv", ".webm", ".gif", ".gifv", ".mpg", ".mpeg", ".m4v", ".mod", ".3gp", ".wmv", ".yuv"]


def ffmpeg(*args: str | pathlib.Path,
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
    cmd += [
        arg.as_posix() if isinstance(arg, pathlib.Path) else arg
        for arg in args
    ]
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
    duration: float | None
    size: int
    creation: int
    
    @property
    def aspect(self) -> float:
        return self.width / self.height


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
    stdout = subprocess.check_output(cmd)
    data = json.loads(stdout)
    if not "streams" in data:
        raise ValueError(f"Invalid FFprobe output at {path}")
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
    if width is None:
        raise ValueError("Could not read 'width' attribute with FFprobe")
    if height is None:
        raise ValueError("Could not read 'height' attribute with FFprobe")
    if framerate is None:
        raise ValueError("Could not read 'framerate' attribute with FFprobe")
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
    return re.sub(r"[\*\"\\<>:\|]", "", string)


def format_path(template: str, kwargs: dict) -> pathlib.Path:
    return pathlib.Path(template.format(**{
        key: value if key == "parent" else escape_path_chars(str(value))
        for key, value in kwargs.items()
    }))


def format_timestamp(total_seconds: float) -> str:
    h = int(total_seconds / 3600)
    m = int((total_seconds - 3600 * h) / 60)
    s = int((total_seconds - 3600 * h - 60 * m))
    ms = round((total_seconds - 3600 * h - 60 * m - s) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def parse_timestamp(timestamp: str) -> float:
    """Parse timestamp with format (HH:)?MM:SS(.FFF)? and returns a value in seconds.
    """
    m = re.match(r"^(?:(\d\d):)?(\d\d):(\d\d)(?:\.(\d\d\d))?$", timestamp)
    if m is None:
        raise ValueError(f"Timestap has invalid format: {timestamp}")
    seconds = 60 * int(m.group(2)) + int(m.group(3))
    if m.group(1) is not None:
        seconds = 3600 * int(m.group(1))
    if m.group(4) is not None:
        seconds += int(m.group(4)) / 1000
    return seconds


def format_eta(total_seconds: float) -> str:
    h = int(total_seconds / 3600)
    m = int((total_seconds - 3600 * h) / 60)
    s = int((total_seconds - 3600 * h - 60 * m))
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_aspect_ratio(string: str | None) -> float | None:
    if string is None:
        return None
    if re.match(r"^\d*(\.\d*)?$", string):
        return float(string)
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


def parse_exposure_duration(duration_string: str) -> str:
    match = re.match(r"^\d+$", duration_string)
    if match is not None:
        total_seconds = int(duration_string)
    else:
        up, down = duration_string.split("/")
        total_seconds = float(up) / float(down)
    return format_timestamp(total_seconds)


def parse_duration(string: str) -> float:
    m = re.match(r"^(\d+:)?(\d+:)?(\d+)(\.\d+)?$", string)
    if m is None:
        raise ValueError(f"String '{string}' is not a valid duration string")
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


class VideoInput:

    def __init__(self, path: pathlib.Path, hide_progress: bool = True):
        self.path = path
        import cv2
        self.capture: cv2.VideoCapture
        self.width: int
        self.height: int
        self.framerate: float
        self.length: int
        self.hide_progress = hide_progress
        self.pbar = None

    def __enter__(self):
        import cv2
        self.capture = cv2.VideoCapture(self.path.as_posix())
        self.width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.framerate = self.capture.get(cv2.CAP_PROP_FPS) or 30.0
        self.length = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if not self.hide_progress:
            self.pbar = tqdm.tqdm(total=self.length, unit="frame")
        return self

    def __iter__(self):
        return self

    def __next__(self):
        import numpy, cv2
        success, frame = self.capture.read()
        if not success or frame is None:
            raise StopIteration
        if self.pbar is not None:
            self.pbar.update(1)
            self.pbar.set_postfix({"time": format_timestamp(self.pbar.n / self.framerate)}, refresh=False)
        return numpy.array(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    def at(self, i: int):
        import cv2
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, i)
        return next(self)

    def rewind(self):
        import cv2
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pbar is not None:
            self.pbar.close()
        self.capture.release()


class VideoOutput:

    def __init__(self,
            path: pathlib.Path,
            width: int,
            height: int,
            framerate: float,
            length: int | None = None,
            vcodec: str = "h264",
            ffmpeg_args: list[str] = [],
            hide_progress: bool = False):
        self.path = path
        self.width = width
        self.height = height
        self.framerate = framerate
        self.length = length
        self.vcodec = vcodec
        self.ffmpeg_args = ffmpeg_args
        self.hide_progress = hide_progress
        self.process: subprocess.Popen[bytes]
        self.pbar = None

    def __enter__(self, ffmpeg="ffmpeg"):
        cmd = [ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-f", "rawvideo"]
        if not self.hide_progress:
            if self.length is None:
                cmd.append("-stats")
            else:
                self.pbar = tqdm.tqdm(total=self.length, unit="frame")
        cmd += [
            # "-vcodec","rawvideo",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{self.width}x{self.height}",
            "-r", f"{self.framerate}",
            "-i", "-",
            "-an",
            "-pix_fmt", "yuv420p",
            "-vcodec", self.vcodec,
            *self.ffmpeg_args,
            self.path.as_posix(),
            "-y"
        ]
        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        return self

    def feed(self, frame):
        import numpy
        assert self.process.stdin is not None
        self.process.stdin.write(frame.astype(numpy.uint8).tobytes())
        if self.pbar is not None:
            self.pbar.update(1)
            self.pbar.set_postfix({"time": format_timestamp(self.pbar.n / self.framerate)}, refresh=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.process.stdin is not None:
            self.process.stdin.close()
        if self.pbar is not None:
            self.pbar.close()
        self.process.wait()


def gauss(n: int, sigma: float, normalized: bool = False) -> list[float]:
    weights = [
        1 / (sigma * math.sqrt(2 * math.pi)) * math.exp(-float(x) ** 2 / (2 * sigma **2 ))
        for x in range(-int(n / 2), int(n / 2) + 1)
    ][:n]
    if not normalized:
        return weights
    total = sum(weights)
    return [w/total for w in weights]


def weighted_sum(sigma: float) -> typing.Callable:
    import numpy
    def aux(frames):
        n = frames.shape[0]
        weights = numpy.reshape(gauss(n, sigma, True), (n, 1, 1, 1))
        return numpy.sum(numpy.multiply(weights, frames), axis=0)
    return aux


def random_blend(frames):
    import numpy
    n, height, width, depth = frames.shape
    indices = numpy.random.randint(0, n, (height, width))
    row_indices, col_indices = numpy.meshgrid(numpy.arange(height), numpy.arange(width), indexing="ij")
    return frames[indices, row_indices, col_indices, :]


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
        case "random":
            return random_blend
        case _:
            raise ValueError(f"Illegal operation '{opname}'")
