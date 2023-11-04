import os

from ..tool import Tool


class Split(Tool):

    NAME = "split"

    def __init__(self, input_path, parts=None, duration=None, output_folder=None):
        Tool.__init__(self)
        self.input_path = input_path
        self.parts = parts
        self.duration = None if duration is None else self.parse_duration(duration)
        if self.parts is None and self.duration is None:
            raise ValueError("Parts or duration should be specified")
        self.output_folder = output_folder

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("input_path", type=str, help="input path")
        parser.add_argument("-p", "--parts", type=int, default=None, help="number of parts to split into")
        parser.add_argument("-d", "--duration", type=str, default=None, help="limit duration")
        parser.add_argument("-o", "--output-folder", type=str, default=None, help="path to output folder")

    @classmethod
    def from_args(cls, args):
        return cls.from_keys(args, ["input_path"], ["parts", "duration", "output_folder"])     
    
    def compute_stops(self, duration):
        stops = []
        limit = self.duration
        if self.parts is not None:
            limit = duration / self.parts
        t = 0
        while t < duration + limit:
            stops.append(min(duration, t))
            t += limit
        return stops

    def process_file(self, input_path):
        probe_result = self.probe(input_path)
        splitext = os.path.splitext(input_path)
        base_path = splitext[0]
        if self.output_folder is not None:
            base_path = os.path.join(
                self.output_folder,
                os.path.basename(base_path))
        stops = self.compute_stops(probe_result.duration)
        for i, (time_start, time_end) in enumerate(zip(stops, stops[1:])):
            output_path = base_path + f"_{i:03d}" + splitext[1]
            self.ffmpeg(
                "-i",
                input_path,
                "-ss",
                self.format_timestamp(time_start),
                "-to",
                self.format_timestamp(time_end),
                output_path
            )

    def run(self):
        input_paths = self.parse_source_paths([self.input_path])
        for input_path in input_paths:
            self.process_file(input_path)
