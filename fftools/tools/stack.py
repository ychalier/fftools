import math
import pathlib

from ..tool import ManyToOneTool
from .. import utils


class Stack(ManyToOneTool):
    """
    @see https://stackoverflow.com/questions/11552565/
    """

    NAME = "stack"
    DESC = "Stack videos in a grid"

    def __init__(self, draw_text: bool = True, shortest: bool = False, rows: int | None = None, columns: int | None = None):
        ManyToOneTool.__init__(self)
        self.draw_text = draw_text
        self.shortest = shortest
        self.font_size = 72
        self.text_offset = 100
        self.font_file = "c\\:\\\\Windows\\\\Fonts\\\\arialbd.ttf"
        self.rows = rows
        self.columns = columns

    @staticmethod
    def add_arguments(parser):
        ManyToOneTool.add_arguments(parser)
        parser.add_argument("-t", "--draw-text", action="store_true", help="write filenames on videos")
        parser.add_argument("-s", "--shortest", action="store_true", help="stop when the shortest input ends")
        parser.add_argument("-r", "--rows", type=int, default=None, help="force number of rows")
        parser.add_argument("-c", "--columns", type=int, default=None, help="force number of columns")

    def process(self, inputs: list[utils.InputFile], output_path: pathlib.Path):
        n = len(inputs)
        self.font_size = int(inputs[0].probe.height * 0.15)
        self.text_offset = int(inputs[0].probe.height * 0.21)
        if self.rows is not None and self.columns is not None:
            width = self.columns
            height = self.rows
        elif self.rows is not None:
            height = self.rows
            width = math.ceil(n / height)
        elif self.columns is not None:
            width = self.columns
            height = math.ceil(n / width)
        else:
            width = math.ceil(math.sqrt(n))
            height = math.ceil(n / width)
        args = []
        filter_args = []
        draw_arg = ""
        for i, input_file in enumerate(inputs):
            args += ["-i", input_file.path.as_posix()]
            if self.draw_text:
                filter_args.append(
                    f"[{i}]drawtext=fontfile='{self.font_file}'"\
                    f":fontsize={self.font_size}"\
                    f":fontcolor=black"\
                    f":box=1"\
                    f":boxcolor=white"\
                    f":text='{input_file.path.stem}'"\
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
        draw_arg += f"xstack=inputs={n}:layout={'|'.join(layout_arg)}"
        if self.shortest:
            draw_arg += ":shortest=1"
        draw_arg += "[v]"
        filter_args.append(draw_arg)
        args += ["-filter_complex", ";".join(filter_args)]
        args += ["-map", "[v]"]
        args.append(output_path)
        utils.ffmpeg(*args)
