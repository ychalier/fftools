import pathlib

from ..tool import OneToOneTool
from .. import utils


class BlendFrames(OneToOneTool):

    NAME = "blend-frames"
    DESC = "Blend consecutive frames of a video together."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_{operation}_{size}{suffix}"

    def __init__(self,
            template: str,
            operation: str = "average",
            size: int = 3,
            fixed: bool = False):
        OneToOneTool.__init__(self, template)
        self.size = size
        self.opname = operation
        self.fixed = fixed
        self.operation = utils.getop(operation)

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-p", "--operation", type=str, help="Operation to blend the images together", default="average", choices=["average", "brighter", "darker", "sum", "difference", "weight1", "weight3", "weight5", "weight10", "random"])
        parser.add_argument("-s", "--size", type=int, help="Moving-window size (in frames) for blending", default=3)
        parser.add_argument("-f", "--fixed", action="store_true", help="Use fixed window instead of a rolling window")

    def process(self, input_file: utils.InputFile) -> pathlib.Path:
        import numpy
        output_path = self.inflate(input_file.path, {
            "operation": self.opname,
            "size": self.size
        })
        with utils.VideoInput(input_file.path) as vin:
            length = vin.length
            if not self.fixed:
                length += self.size - 1
            with utils.VideoOutput(output_path, vin.width, vin.height, vin.framerate, length) as vout:
                if self.fixed:
                    running = True
                    while running:
                        frames = []
                        try:
                            for _ in range(self.size):
                                frames.append(next(vin))
                        except StopIteration:
                            running = False
                            if not frames:
                                continue
                        out_frame = self.operation(numpy.array(frames))
                        for _ in frames:
                            vout.feed(out_frame)
                else:
                    frames = []
                    for frame in vin:
                        frames.append(frame)
                        while len(frames) > self.size:
                            frames.pop(0)
                        vout.feed(self.operation(numpy.array(frames)))
                    while len(frames) > 1:
                        frames.pop(0)
                        vout.feed(self.operation(numpy.array(frames)))
        return output_path
