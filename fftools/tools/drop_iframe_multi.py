import pathlib

from ..tool import ManyToOneTool
from .. import utils
from .drop_iframe_single import DropIFrameSingle


class DropIFrameMulti(ManyToOneTool):

    NAME = "drop-iframe-multi"
    DESC = "Concatenate multiple clips with a datamoshing effect"

    def __init__(self,
            quality: int = 1,
            allow_iframes: bool = False,
            scenecut: float = 0,
            me: str = "zero"):
        ManyToOneTool.__init__(self)
        self.quality = quality
        self.allow_iframes = allow_iframes
        self.scenecut = scenecut
        self.me = me

    @staticmethod
    def add_arguments(parser):
        ManyToOneTool.add_arguments(parser)
        parser.add_argument("-q", "--quality", type=int, default=1, choices=list(range(32)),
            help="Quality setting for encoding")
        parser.add_argument("-i", "--allow-iframes", action="store_true",
            help="allow iframes within clips")
        parser.add_argument("--scenecut", type=float, default=0,
            help="scene cut threshold")
        parser.add_argument("--me", type=str, default="zero", choices=["zero", "dia", "epzs", "hex", "umh", "esa", "tesa"],
            help="Motion estimation method, choices are in decreasing order of speed.")

    def process(self, inputs: list[utils.InputFile], output_path: pathlib.Path):
        with utils.tempdir() as tmpdir:
            part_paths: list[pathlib.Path] = []
            for i, input_file in enumerate(inputs):
                if input_file.probe.duration is None:
                    raise ValueError(f"{input_file} has no duration")
                n_frames = int(input_file.probe.duration * input_file.probe.framerate)
                part_path = tmpdir / f"{i:09d}.avi"
                print(f"[{i+1}/{len(inputs)}]", input_file.path.name)
                args = []
                if not self.allow_iframes:
                    args += [
                        "-g", f"{n_frames + 1}",
                        "-keyint_min", f"{n_frames + 1}",
                    ]
                utils.ffmpeg(
                    "-i", input_file.path,
                    "-an",
                    "-vcodec", "libxvid",
                    "-q:v", f"{self.quality}",
                    *args,
                    "-flags", "+bitexact",
                    "-sc_threshold", str(self.scenecut),
                    "-me_method", self.me,
                    "-forced-idr", "1",
                    part_path,
                )
                part_paths.append(part_path)
            list_path = tmpdir / "list.txt"
            with list_path.open("w") as file:
                for part_path in part_paths:
                    file.write(f"file '{part_path.as_posix()}'\n")
            xvid_path = tmpdir / "xvid.avi"
            utils.ffmpeg(
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-c", "copy",
                xvid_path
            )
            DropIFrameSingle.drop_iframes(xvid_path, output_path)
