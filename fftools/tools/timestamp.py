import datetime
import math
import pathlib

from ..tool import OneToOneTool
from .. import utils


class Timestamp(OneToOneTool):

    NAME = "timestamp"
    DESC = "Add a timestamp over video given its creation datetime."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_timestamp{suffix}"

    def __init__(self,
            template: str,
            timestamp: int | None = None,
            font_size: int = 36,
            font_path: str = "C:\\Windows\\Fonts\\courbd.ttf",
            padding: int = 16,
            color: tuple[int] = (255, 255, 255, 255)):
        OneToOneTool.__init__(self, template)
        self.timestamp = timestamp
        self.font_size = font_size
        self.font_filepath = pathlib.Path(font_path)
        self.color = color
        self.padding = padding
        from PIL.ImageFont import truetype
        self.font = truetype(self.font_filepath, size=self.font_size)

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-t", "--timestamp", type=int, help="start timestamp", default=None)
        parser.add_argument("-fs", "--font-size", type=int, help="font size", default=36)
        parser.add_argument("-ff", "--font-path", type=str, help="font size", default="C:\\Windows\\Fonts\\courbd.ttf")
        parser.add_argument("-p", "--padding", type=int, help="padding", default=16)
    
    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        import PIL.Image, tqdm
        with utils.tempdir() as tempdir:
            listfile_path = tempdir / "list.txt"
            with listfile_path.open("w") as listfile:
                probe = utils.ffprobe(input_path)
                start = probe.creation
                if self.timestamp is not None:
                    start = self.timestamp
                for t in tqdm.tqdm(range(start, start + math.ceil(probe.duration))):
                    d = datetime.datetime.fromtimestamp(t)
                    text = d.strftime("%Y-%m-%d %H:%M:%S")
                    mask_image = self.font.getmask(text, "L")
                    height = mask_image.size[1] + 2 * self.padding
                    image = PIL.Image.new("RGB", (probe.width, height))
                    image.im.paste(
                        self.color,
                        (self.padding, self.padding, mask_image.size[0] + self.padding, mask_image.size[1] + self.padding),
                        mask_image)
                    filepath = tempdir / f"{t}.png"
                    listfile.write(f"file '{filepath}'\n")
                    image.save(filepath)
            banner_path = tempdir / "banner.mp4"
            utils.ffmpeg(
                "-r", "1",
                "-f", "concat",
                "-safe", "0",
                "-i", listfile_path,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                banner_path
            )
            output_path = self.inflate(input_path)
            utils.ffmpeg(
                "-i", input_path,
                "-i", banner_path,
                "-filter_complex", "overlay=shortest=1",
                output_path
            )
        return output_path