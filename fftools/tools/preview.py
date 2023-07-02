import glob
import os
import tempfile

import PIL.Image

from ..tool import Tool


class Preview(Tool):

    NAME = "preview"

    def __init__(self, video_path, image_path, nrows=3, ncols=2):
        Tool.__init__(self)
        self.video_path = video_path
        self.image_path = image_path
        self.nrows = nrows
        self.ncols = ncols

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("video_path", type=str, help="Path to the source video")
        parser.add_argument("image_path", type=str, help="Path to the output image")
        parser.add_argument("-r", "--nrows", type=int, default=3)
        parser.add_argument("-c", "--ncols", type=int, default=2)

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["video_path", "image_path"], ["nrows", "ncols"])
    
    def extract_frames(self, folder):
        probe = self.probe(self.video_path)
        npreviews = self.nrows * self.ncols
        frame_count = int(probe.duration * probe.framerate)
        frame_indices = [i * (frame_count // npreviews) for i in range(npreviews)]
        self.ffmpeg(
            "-i",
            self.video_path,
            "-vf",
            "select='%s'" % ("+".join([
                    "eq(n\\,%d)" % i
                    for i in frame_indices
                ])
            ),
            "-vsync",
            "0",
            os.path.join(folder, "%06d.jpg"),
            "-y"
        )

    def merge_frames(self, folder):
        image = None
        width, height = None, None
        for i, frame_path in enumerate(sorted(glob.glob(os.path.join(folder, "*.jpg")))):
            with PIL.Image.open(frame_path, "r") as frame:
                if image is None:
                    width, height = frame.size
                    image = PIL.Image.new(
                        "RGB",
                        (width * self.ncols, height * self.nrows),
                        (0, 0, 0)
                    )
                row = i // self.ncols
                col = i % self.ncols
                image.paste(frame, (col * width, row * height))
        image.save(self.image_path)
    
    def run(self):
        with tempfile.TemporaryDirectory() as folder:
            self.extract_frames(folder)
            self.merge_frames(folder)
        self.startfile(self.image_path)