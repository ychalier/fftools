import math
import pathlib
import random
from typing import Callable

import tqdm

from ..tool import OneToOneTool
from .. import utils


def parse_lambda_expression(expr_string: str, vars: tuple[str, ...], context: dict[str, object] = {}) -> Callable:
    if len(vars) == 1:
        vars_str = vars[0]
    else:
        vars_str = ",".join(vars)
    return eval(f"lambda {vars_str}: " + expr_string, {"math": math, "random": random, **context}, None)


class DropIFrameSingle(OneToOneTool):

    NAME = "drop-iframe-single"
    DESC = "Exactly set a reference frames in a video clip and apply a datamoshing effect on it"
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_{state}{suffix}"

    def __init__(self,
            template: str,
            quality: int = 1,
            preserve_timings: bool = False,
            no_preprocessing: bool = False,
            iframe: str = ""):
        OneToOneTool.__init__(self, template)
        self.quality: int = quality
        self.preserve_timings = preserve_timings
        self.no_preprocessing = no_preprocessing
        self.iframe_expr = iframe

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-q", "--quality", type=int, default=1, choices=list(range(32)),
            help="Quality setting for encoding")
        parser.add_argument("-p", "--preserve-timings", action="store_true",
            help="Duplicate frames in preprocessing to preserve timings in output video")
        parser.add_argument("-n", "--no-preprocessing", action="store_true",
            help="Skip preprocessing step")
        parser.add_argument("-i", "--iframe", type=str,
            default="i % int(fps) == 0",
            help="Pythonic expression evaluated on variable `i` (frame index) "
            "for deciding whether frame no. `i` should be a reference frame. "
            "`fps` is a constant variable representing input video framerate, "
            "as a float value. `math` and `random` modules are available.")

    def apply_frame_map(self, input_path: pathlib.Path, output_path: pathlib.Path):
        probe_result = utils.ffprobe(input_path)
        if probe_result.duration is None:
            raise ValueError("Video has no duration")
        n_frames = int(probe_result.duration * probe_result.framerate)
        is_iframe = parse_lambda_expression(self.iframe_expr, ("i",), {"fps": probe_result.framerate})
        stops = list(filter(is_iframe, range(n_frames + 1)))
        if stops[-1] != n_frames:
            stops.append(n_frames)
        part_paths: list[pathlib.Path] = []
        with utils.tempdir() as tmpdir:
            pbar = tqdm.tqdm(total=n_frames, unit="frame", desc="Preprocessing")
            for i, (part_start, part_end) in enumerate(zip(stops, stops[1:])):
                part_frames_base = part_end - part_start
                if self.preserve_timings:
                    part_start = max(0, part_start - 1)
                part_frames = part_end - part_start
                part_path = tmpdir / f"{i:09d}.mp4"
                part_paths.append(part_path)
                utils.ffmpeg(
                    "-i", input_path,
                    "-vf", f"trim=start_frame={part_start}:end_frame={part_end},setpts=PTS-STARTPTS",
                    "-an",
                    "-vcodec", "libxvid",
                    "-q:v", f"{self.quality}",
                    "-g", f"{part_frames + 1}",
                    "-keyint_min", f"{part_frames + 1}",
                    "-flags", "+bitexact",
                    "-sc_threshold", "0",
                    "-me_method", "zero",
                    part_path,
                    show_stats=False
                )
                pbar.update(part_frames_base)
            pbar.close()
            list_path = tmpdir / "list.txt"
            with list_path.open("w") as file:
                for part_path in part_paths:
                    file.write(f"file '{part_path.as_posix()}'\n")
            utils.ffmpeg(
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-c", "copy",
                output_path
            )

    @staticmethod
    def is_xvid(path: pathlib.Path) -> bool:
        import av
        container = av.open(path.as_posix())
        video_stream = container.streams.video[0]
        long_name = video_stream.codec_context.codec.long_name
        container.close()
        return long_name == "MPEG-4 part 2"

    @staticmethod
    def drop_iframes(input_path: pathlib.Path, output_path: pathlib.Path):
        import av
        assert DropIFrameSingle.is_xvid(input_path), input_path
        with utils.tempdir() as tmpdir:
            badpts_path = tmpdir / "badpts.mp4"
            container = av.open(input_path.as_posix())
            output = av.open(badpts_path.as_posix(), mode="w")
            video_stream = container.streams.video[0]
            output.add_stream(
                video_stream.codec.name,
                pix_fmt=video_stream.pix_fmt,
                width=video_stream.width,
                height=video_stream.height,
                bit_rate=video_stream.bit_rate,
            )
            first_iframe_written = False
            for packet in container.demux(video_stream):
                if packet.is_keyframe:
                    if not first_iframe_written:
                        first_iframe_written = True
                        output.mux(packet)
                    else:
                        continue
                else:
                    output.mux(packet)
            container.close()
            output.close()
            probe = utils.ffprobe(input_path)
            utils.ffmpeg(
                "-fflags", "+genpts",
                "-r", str(probe.framerate),
                "-i", badpts_path,
                output_path
            )

    def process(self, input_file: utils.InputFile) -> pathlib.Path:
        if self.no_preprocessing:
            preprocessed_path = input_file.path
        else:
            preprocessed_path = self.inflate(input_file.path, {"state": "mosh_pre"})
            self.apply_frame_map(input_file.path, preprocessed_path)
        output_path = self.inflate(input_file.path, {"state": "mosh_post"})
        self.drop_iframes(preprocessed_path, output_path)
        return output_path
