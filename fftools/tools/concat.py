import pathlib

from ..tool import ManyToOneTool
from .. import utils


class Concat(ManyToOneTool):
    """
    @see https://trac.ffmpeg.org/wiki/Concatenate
    """

    NAME = "concat"
    DESC = "Concatenate multiple image or video files into one video file."

    def __init__(self, copy: bool = False, framerate: float | None = None, duration: str | None = None):
        ManyToOneTool.__init__(self)
        self.copy = copy
        self.framerate = framerate
        self.duration = None if duration is None else utils.parse_duration(duration)

    @staticmethod
    def add_arguments(parser):
        ManyToOneTool.add_arguments(parser)
        parser.add_argument("-c", "--copy", action="store_true", help="Directly copy streams instead of reencoding them (faster but does not handle various sizes well) (when concatenating videos only)")
        parser.add_argument("-r", "--framerate", type=float, help="Target video framerate (when concatenating images only)")
        parser.add_argument("-t", "--duration", type=str, help="Target video duration (when concatenating images only)")
    
    def process(self, input_paths: list[pathlib.Path], output_path: pathlib.Path):
        are_images = list(map(utils.is_image, input_paths))
        are_videos = list(map(utils.is_video, input_paths))
        all_images = all(are_images)
        all_videos = all(are_videos)
        mixed = any(are_images) and any(are_videos)
        if mixed:
            raise NotImplementedError("Concatenation of a mix of images and videos not implemented yet. FFmpeg can do it though, but you'll have to do it manually.")
        with utils.tempdir() as folder:
            listpath = folder / "list.txt"
            with listpath.open("w") as file:
                for source_path in input_paths:
                    file.write(f"file '{source_path.absolute()}'\n")
            args = []
            if all_images:
                framerate = 1.0
                if self.framerate is not None:
                    framerate = self.framerate
                elif self.duration is not None:
                    framerate = len(input_paths) / self.duration
                args += ["-r", str(framerate)]
            args += [
                "-f", "concat",
                "-safe", "0",
                "-i", listpath
            ]
            if all_videos and self.copy:
                args += ["-c", "copy"]
            if all_images:
                args += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
            args.append(output_path)
            utils.ffmpeg(*args)
