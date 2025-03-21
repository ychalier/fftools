import argparse
import pathlib
import time

from . import utils


class Tool:

    NAME = None
    DESC = None

    def __init__(self):
        pass
    
    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        raise NotImplementedError()

    @classmethod
    def run(cls, args: argparse.Namespace):
        raise NotImplementedError()

    
class OneToOneTool(Tool):
    
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}{suffix}"
    
    def __init__(self, template: str | None):
        Tool.__init__(self)
        self.template = template if template is not None else self.OUTPUT_PATH_TEMPLATE
        self.overwrite = False
    
    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        parser.add_argument("input_path", type=str, help="input path")
        parser.add_argument("output_path", type=str, help="output path", nargs="?")
        parser.add_argument("-nx", "--no-execute", action="store_true", help="do not open the output file")
        parser.add_argument("-ow", "--overwrite", action="store_true", help="overwrite existing files")
        parser.add_argument("-gp", "--global-progress", action="store_true", help="show global progress if multiple inputs are provided")
    
    @classmethod
    def run(cls, args: argparse.Namespace):
        kwargs = vars(args)
        input_path = kwargs.pop("input_path")
        template = kwargs.pop("output_path", None)
        no_execute = kwargs.pop("no_execute", False)
        overwrite = kwargs.pop("overwrite", False)
        global_progress = kwargs.pop("global_progress", False)
        tool = cls(template, **kwargs)
        tool.overwrite = overwrite
        expanded_input_paths = utils.expand_paths([input_path])
        n = len(expanded_input_paths)
        time_start = time.time()
        for i, input_path in enumerate(expanded_input_paths):
            if n > 1 and global_progress:
                elapsed = time.time() - time_start
                if i >= 1:
                    speed = elapsed / i
                    eta = speed * (n - i)
                    print(f"[{i+1}/{n}] speed={speed:.1f}s/it eta={utils.format_eta(eta)} input={input_path.as_posix()}")
                else:
                    print(f"[{i+1}/{n}] {input_path.as_posix()}")
            output_path = tool.process(input_path)
            if len(expanded_input_paths) == 1 and output_path is not None and not no_execute:
                utils.startfile(output_path)
    
    def inflate(self, input_path: pathlib.Path, context: dict = {}) -> pathlib.Path:
        path = utils.format_path(self.template, {
            "parent": input_path.parent.as_posix(),
            "stem": input_path.stem,
            "suffix": input_path.suffix,
            **context
        })
        path.parent.mkdir(exist_ok=True, parents=True)
        if self.overwrite:
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        return utils.find_unique_path(path)
    
    def process(self, input_path: pathlib.Path) -> pathlib.Path | None:
        raise NotImplementedError()


class ManyToOneTool(Tool):
    
    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        parser.add_argument("input_paths", type=str, help="input path", nargs="+")
        parser.add_argument("output_path", type=str, help="output path")
    
    @classmethod
    def run(cls, args: argparse.Namespace):
        kwargs = vars(args)
        input_paths = kwargs.pop("input_paths")
        output_path = utils.find_unique_path(pathlib.Path(kwargs.pop("output_path")))
        tool = cls(**kwargs)
        expanded_input_paths = utils.expand_paths(input_paths)
        tool.process(expanded_input_paths, output_path)
        utils.startfile(output_path)
    
    def process(self, input_paths: list[pathlib.Path], output_path: pathlib.Path):
        raise NotImplementedError()
