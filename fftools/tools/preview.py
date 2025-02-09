import pathlib

from ..tool import OneToOneTool
from .. import utils


class Preview(OneToOneTool):

    NAME = "preview"
    DESC = "Extract thumbnails of evenly spaced moments of a video."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_preview.png"

    def __init__(self, template: str, nrows: int = 3, ncols: int = 2):
        OneToOneTool.__init__(self, template)
        self.nrows = nrows
        self.ncols = ncols

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-r", "--nrows", type=int, default=3)
        parser.add_argument("-c", "--ncols", type=int, default=2)
    
    def _extract_frames(self, input_path: pathlib.Path, folder: pathlib.Path):
        probe = utils.ffprobe(input_path)
        npreviews = self.nrows * self.ncols
        frame_count = int(probe.duration * probe.framerate)
        frame_indices = [i * (frame_count // npreviews) for i in range(npreviews)]
        utils.ffmpeg(
            "-i", input_path,
            "-vf", "select='%s'" % ("+".join(["eq(n\\,%d)" % i for i in frame_indices])),
            "-vsync", "0",
            folder / "%06d.png",
        )

    def _merge_frames(self, folder: pathlib.Path, output_path: pathlib.Path):
        import PIL.Image
        image = None
        width, height = None, None
        for i, frame_path in enumerate(sorted(folder.glob("*.png"))):
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
        image.save(output_path)
    
    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        with utils.tempdir() as folder:
            self._extract_frames(input_path, folder)
            ouptut_path = self.inflate(input_path)
            self._merge_frames(folder, ouptut_path)
        return ouptut_path