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
            size: int = 3):
        OneToOneTool.__init__(self, template)
        self.size = size
        self.opname = operation
        self.operation = utils.getop(operation)

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-p", "--operation", type=str, help="Operation to blend the images together", default="average", choices=["average", "brighter", "darker", "sum", "difference", "weight1", "weight3", "weight5", "weight10", "random"])
        parser.add_argument("-s", "--size", type=int, help="Moving-window size (in frames) for blending", default=3)

    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        import numpy
        output_path = self.inflate(input_path, {
            "operation": self.opname,
            "size": self.size
        })
        with utils.VideoInput(input_path) as vin:
            with utils.VideoOutput(output_path, vin.width, vin.height, vin.framerate, vin.length + self.size - 1) as vout:
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
