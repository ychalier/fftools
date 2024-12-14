import math
from pathlib import Path

from ..tool import Tool


class Stack(Tool):
    """
    @see https://stackoverflow.com/questions/11552565/
    """

    NAME = "stack"
    DESC = "Stack videos in a grid"

    def __init__(self, output_path: str, source_paths: str, draw_text: bool = True):
        Tool.__init__(self)
        self.output_path = Path(output_path)
        self.source_paths = self.parse_source_paths(source_paths)
        self.draw_text = draw_text
        self.font_size = 72
        self.text_offset = 100
        self.font_file = "c\\:\\\\Windows\\\\Fonts\\\\arialbd.ttf"

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("output_path", type=str, help="output path")
        parser.add_argument("source_paths", type=str, nargs="+", help="source paths")
        parser.add_argument("-t", "--draw-text", action="store_true", help="write filenames on videos")

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["output_path", "source_paths"], ["draw_text"])

    def run(self):
        n = len(self.source_paths)
        probe = self.probe(self.source_paths[0])
        self.font_size = int(probe.height * 0.15)
        self.text_offset = int(probe.height * 0.21)
        width = math.ceil(math.sqrt(n))
        height = math.ceil(n / width)
        args = []
        filter_args = []
        draw_arg = ""
        for i, path in enumerate(self.source_paths):
            args += ["-i", path.as_posix()]
            if self.draw_text:
                filter_args.append(
                    f"[{i}]drawtext=fontfile='{self.font_file}'"\
                    f":fontsize={self.font_size}"\
                    f":fontcolor=black"\
                    f":box=1"\
                    f":boxcolor=white"\
                    f":text='{path.stem}'"\
                    f":x=(w-text_w)/2"\
                    f":y=h-{self.text_offset}"\
                    f"[v{i}]")
                draw_arg += f"[v{i}]"
        layout_arg = []
        h = "0"
        for i in range(height):
            w = "0"
            for j in range(width):
                layout_arg.append(f"{w}_{h}")
                if w == "0":
                    w = "w0"
                else:
                    w += f"+w{i}"
            if h == "0":
                h = "h0"
            else:
                h += f"+h{i}"
        draw_arg += f"xstack=inputs={n}:layout={'|'.join(layout_arg)}[v]"
        filter_args.append(draw_arg)
        args += ["-filter_complex", ";".join(filter_args)]
        args += ["-map", "[v]"]
        args.append(self.output_path)
        self.ffmpeg(*args)
        self.startfile(self.output_path)
