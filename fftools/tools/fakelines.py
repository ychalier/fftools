from pathlib import Path
from numpy import zeros
from ..tool import OneToOneTool
from ..utils import InputFile, VideoInput, VideoOutput

class FakeLines(OneToOneTool):

    NAME = "fakelines"
    DESC = "Fake scanning lines with a hatched pattern."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_{n}{suffix}"

    def __init__(self, template: str, n: int):
        OneToOneTool.__init__(self, template)
        self.n = n
    
    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-n", type=int, default=2, help="number of lines per pattern")

    def process(self, input_file: InputFile) -> Path:
        output_path = self.inflate(input_file.path, {"n": self.n})
        with VideoInput(input_file.path) as vin:
            with VideoOutput(output_path, vin.width, vin.height, vin.framerate, vin.length, hide_progress=self.quiet) as vout:
                frame_out = None
                for i, frame_in in enumerate(vin):
                    if frame_out is None:
                        frame_out = zeros(frame_in.shape, dtype=frame_in.dtype)
                    i0 = i % self.n
                    frame_out[i0::self.n,:,:] = frame_in[i0::self.n,:,:]
                    vout.feed(frame_out)
        return output_path
