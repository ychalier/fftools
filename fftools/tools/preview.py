from pathlib import Path

from ..tool import Tool


class Preview(Tool):

    NAME = "preview"
    DESC = "Extract thumbnails of evenly spaced moments of a video."

    def __init__(self, video_path: str, nrows: int = 3, ncols: int = 2):
        Tool.__init__(self)
        self.video_path = Path(video_path)
        self.image_path = self.video_path.with_suffix(".jpg").with_stem(self.video_path.stem + "_preview")
        self.nrows = nrows
        self.ncols = ncols

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("video_path", type=str, help="Path to the source video")
        parser.add_argument("-r", "--nrows", type=int, default=3)
        parser.add_argument("-c", "--ncols", type=int, default=2)

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["video_path"], ["nrows", "ncols"])
    
    def extract_frames(self, folder: Path):
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
            folder / "%06d.jpg",
        )

    def merge_frames(self, folder: Path):
        import PIL.Image
        image = None
        width, height = None, None
        for i, frame_path in enumerate(sorted(folder.glob("*.jpg"))):
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
        with Tool.tempdir() as folder:
            self.extract_frames(folder)
            self.merge_frames(folder)
        self.startfile(self.image_path)