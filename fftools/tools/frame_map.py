import pathlib

from ..tool import OneToOneTool
from .. import utils


class FrameMap(OneToOneTool):

    NAME = "frame-map"
    DESC = "Apply a specific frame map (reference or non-reference frames) to a video file"
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_framemap{suffix}"

    def __init__(self,
            template: str,
            quality: int = 0):
        OneToOneTool.__init__(self, template)
        self.quality: int = quality

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-q", "--quality", type=int, default=0, choices=list(range(52)))
        # TODO: specify map with an eval string that takes time or frame index and returns wether or not naninana
        # TODO: add flag to output one frame earlier to preserve timings

    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        probe_result = utils.ffprobe(input_path)
        if probe_result.duration is None:
            raise ValueError("Video has no duration")
        output_path = self.inflate(input_path)
        n_frames = int(probe_result.duration * probe_result.framerate)
        stops: list[int] = list(range(0, n_frames, 30))
        part_paths: list[pathlib.Path] = []
        with utils.tempdir() as tmpdir:
            for i, (part_start, part_end) in enumerate(zip(stops, stops[1:])):
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
                    "-sc_threshold", "0",
                    "-keyint_min", f"{part_frames + 1}",
                    part_path
                )
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
        return output_path
