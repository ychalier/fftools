from pathlib import Path

from ..tool import Tool


class Timestamp(Tool):

    NAME = "timestamp"

    def __init__(self, input_path: str | Path,
                 timestamp: int | None = None, font_size: int = 36,
                 font_path: str = "C:\\Windows\\Fonts\\courbd.ttf",
                 padding: int = 16, color: tuple[int] = (255, 255, 255, 255)):
        self.input_path = Path(input_path)
        self.timestamp = timestamp
        self.font_size = font_size
        self.font_filepath = Path(font_path)
        self.color = color
        self.padding = padding
        self.font = None

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("input_path", type=str, help="input path")
        parser.add_argument("timestamp", type=int, help="start timestamp", default=None, nargs="?")
        parser.add_argument("-fs", "--font-size", type=int, help="font size", default=36)
        parser.add_argument("-ff", "--font-path", type=str, help="font size", default="C:\\Windows\\Fonts\\courbd.ttf")
        parser.add_argument("-p", "--padding", type=int, help="padding", default=16)

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["input_path", "timestamp"], ["font_size", "font_path", "padding"])
    
    def process_file(self, input_path: Path, output_path: Path):
        import datetime, math, tqdm, PIL.Image
        with Tool.tempdir() as tempdir:
            listfile_path = tempdir / "list.txt"
            with listfile_path.open("w") as listfile:
                probe = self.probe(input_path)
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
            self.ffmpeg(
                "-r", "1",
                "-f", "concat",
                "-safe", "0",
                "-i", listfile_path,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                banner_path
            )
            self.ffmpeg(
                "-i", input_path,
                "-i", banner_path,
                "-filter_complex", "overlay=shortest=1",
                output_path
            )
    
    def run(self):
        from PIL.ImageFont import truetype
        self.font = truetype(self.font_filepath, size=self.font_size)
        input_paths = self.parse_source_paths([self.input_path])
        output_path = None
        for input_path in input_paths:
            output_path = input_path.with_stem(input_path.stem + "_annotated")
            self.process_file(input_path, output_path)
        if len(input_paths) == 1:
            self.startfile(output_path)