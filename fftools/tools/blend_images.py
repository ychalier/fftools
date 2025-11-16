import pathlib

from ..tool import ManyToOneTool
from .. import utils


class BlendImages(ManyToOneTool):

    NAME = "blend-images"
    DESC = "Blend multiple images into one."

    def __init__(self,
            operation: str = "average"):
        ManyToOneTool.__init__(self)
        self.opname = operation
        self.operation = utils.getop(operation)

    @staticmethod
    def add_arguments(parser):
        ManyToOneTool.add_arguments(parser)
        parser.add_argument("-p", "--operation", type=str, help="Operation to blend the images together", default="average", choices=["average", "brighter", "darker", "sum", "difference", "random"])

    def process(self, inputs: list[utils.InputFile], output_path: pathlib.Path):
        import numpy, PIL.Image
        out = self.operation(numpy.array([PIL.Image.open(i.path) for i in inputs]))
        PIL.Image.fromarray(out.astype(numpy.uint8)).save(output_path)
