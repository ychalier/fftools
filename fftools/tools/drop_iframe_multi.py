import pathlib

from ..tool import ManyToOneTool
from .. import utils
from .drop_iframe_single import DropIFrameSingle


class DropIFrameMulti(ManyToOneTool):

    NAME = "drop-iframe-multi"
    DESC = "Concatenate multiple clips with a datamoshing effect"

    def __init__(self, quality: int = 1):
        ManyToOneTool.__init__(self)
        self.quality = quality

    @staticmethod
    def add_arguments(parser):
        ManyToOneTool.add_arguments(parser)
        parser.add_argument("-q", "--quality", type=int, default=1, choices=list(range(32)),
            help="Quality setting for encoding")

    def process(self, inputs: list[utils.InputFile], output_path: pathlib.Path):
        with utils.tempdir() as tmpdir:
            part_paths: list[pathlib.Path] = []
            for i, input_file in enumerate(inputs):
                if input_file.probe.duration is None:
                    raise ValueError(f"{input_file} has no duration")
                n_frames = int(input_file.probe.duration * input_file.probe.framerate)
                part_path = tmpdir / f"{i:09d}.mp4"
                print(f"[{i+1}/{len(inputs)}]", input_file.path.name)
                utils.ffmpeg(
                    "-i", input_file.path,
                    "-an",
                    "-vcodec", "libxvid",
                    "-q:v", f"{self.quality}",
                    "-g", f"{n_frames + 1}",
                    "-keyint_min", f"{n_frames + 1}",
                    "-flags", "+bitexact",
                    "-sc_threshold", "0",
                    "-me_method", "zero",
                    part_path,
                )
                part_paths.append(part_path)
            list_path = tmpdir / "list.txt"
            with list_path.open("w") as file:
                for part_path in part_paths:
                    file.write(f"file '{part_path.as_posix()}'\n")
            xvid_path = tmpdir / "xvid.mp4"
            utils.ffmpeg(
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-c", "copy",
                xvid_path
            )
            DropIFrameSingle.drop_iframes(xvid_path, output_path)
