from pathlib import Path

from ..tool import Tool


class Merge(Tool):

    NAME = "merge"
    DESC = "Merge mulitple images to create a single video file."

    def __init__(self, video_path: str, target: str, frame_paths: list[str]):
        Tool.__init__(self)
        self.video_path = Path(video_path)
        self.target = target
        self.frame_paths = self.parse_source_paths(frame_paths)
    
    @staticmethod
    def add_arguments(parser):
        parser.add_argument("video_path", type=str, help="path to the output video")
        parser.add_argument("target", type=str, help="video framerate or duration")
        parser.add_argument("frame_paths", type=str, nargs="+", help="path to the frames (folder, invidual files, glob)")
    
    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["video_path", "target", "frame_paths"], [])

    def run(self):
        import re
        with Tool.tempdir() as folder:
            listpath = folder / "list.txt"
            with listpath.open("w") as file:
                for source_path in self.frame_paths:
                    file.write(f"file '{source_path.absolute()}'\n")
            if re.match(r"^\d+$", self.target):
                framerate = int(self.target)
            else:
                duration = self.parse_duration(self.target)
                framerate = len(self.frame_paths) / duration
            self.ffmpeg(
                "-r", str(framerate),
                "-f", "concat",
                "-safe", "0",
                "-i", listpath,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                self.video_path
            )
        self.startfile(self.video_path)
