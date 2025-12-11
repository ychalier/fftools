import argparse
import pathlib
import time

import tqdm

from . import utils


class Tool:

    NAME = None
    DESC = None

    def __init__(self, quiet: bool = False):
        self.quiet = quiet

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        raise NotImplementedError()

    @classmethod
    def run_from_args(cls, args: argparse.Namespace):
        raise NotImplementedError()


class OneToOneTool(Tool):

    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}{suffix}"

    def __init__(self, template: str | None, quiet: bool = False):
        Tool.__init__(self, quiet)
        self.template = template if template is not None else self.OUTPUT_PATH_TEMPLATE
        self.overwrite = False

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        parser.add_argument("input_path", type=str, help="input path")
        parser.add_argument("output_path", type=str, help="output path", nargs="?")
        group = parser.add_argument_group("processing options")
        group.add_argument("-N", "--no-execute", action="store_true",
            help="do not open the output file")
        group.add_argument("-O", "--overwrite", action="store_true",
            help="overwrite existing files")
        group.add_argument("-G", "--global-progress", action="store_true",
            help="show global progress if multiple inputs are provided")
        group.add_argument("-K", "--keep-trimmed-files", action="store_true",
            help="save trimmed input files next to their parent instead of tempdir")
        group.add_argument("-Q", "--quiet", action="store_true",
            help="do not print anything")
    
    def run(self,
            input_path: pathlib.Path,
            execute: bool = False,
            overwrite: bool = False,
            quiet: bool = True):
        self.quiet = quiet
        self.overwrite = overwrite
        input_file = utils.InputFile(input_path)
        input_file.preprocess()
        output_path = self.process(input_file)
        if execute:
            utils.startfile(output_path)

    @classmethod
    def run_from_args(cls, args: argparse.Namespace):
        kwargs = vars(args)
        input_path = kwargs.pop("input_path")
        template = kwargs.pop("output_path", None)
        no_execute = kwargs.pop("no_execute", False)
        overwrite = kwargs.pop("overwrite", False)
        global_progress = kwargs.pop("global_progress", False)
        keep_trimmed_files = kwargs.pop("keep_trimmed_files", False)
        quiet = kwargs.pop("quiet", False)
        tool = cls(template, **kwargs)
        tool.quiet = quiet
        tool.overwrite = overwrite
        inputs = utils.expand_paths([input_path])
        for input_file in inputs:
            input_file.preprocess(use_temporary_file=not keep_trimmed_files)
        n = len(inputs)
        time_start = time.time()
        show_pbar = quiet and global_progress
        pbar = tqdm.tqdm(unit="file", total=len(inputs), disable=not show_pbar)
        for i, input_file in enumerate(inputs):
            if show_pbar:
                pbar.set_description(input_file.path.name)
            if n > 1 and global_progress and not show_pbar:
                elapsed = time.time() - time_start
                if i >= 1:
                    speed = elapsed / i
                    eta = speed * (n - i)
                    print(f"[{i+1}/{n}] speed={speed:.1f}s/it eta={utils.format_eta(eta)} input={input_file.path.as_posix()}")
                else:
                    print(f"[{i+1}/{n}] {input_file.path.as_posix()}")
            output_path = tool.process(input_file)
            if show_pbar:
                pbar.update(1)
            if len(inputs) == 1 and output_path is not None and not no_execute:
                utils.startfile(output_path)
        pbar.close()

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

    def process(self, input_file: utils.InputFile) -> pathlib.Path | None:
        raise NotImplementedError()


class ManyToOneTool(Tool):

    SORT: bool = False

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        parser.add_argument("input_paths", type=str, help="input path", nargs="+")
        parser.add_argument("output_path", type=str, help="output path")
        group = parser.add_argument_group("processing options")
        group.add_argument("-K", "--keep-trimmed-files", action="store_true",
            help="save trimmed input files next to their parent instead of tempdir")
        group.add_argument("-Q", "--quiet", action="store_true",
            help="do not print anything")
    
    def run(self,
            input_paths: list[pathlib.Path],
            output_path: pathlib.Path,
            execute: bool = False,
            quiet: bool = True):
        self.quiet = quiet
        input_files = [utils.InputFile(input_path) for input_path in input_paths]
        for input_file in input_files:
            input_file.preprocess()
        output_path = self.process(input_files, output_path)
        if execute:
            utils.startfile(output_path)

    @classmethod
    def run_from_args(cls, args: argparse.Namespace):
        kwargs = vars(args)
        input_paths = kwargs.pop("input_paths")
        keep_trimmed_files = kwargs.pop("keep_trimmed_files", False)
        quiet = kwargs.pop("quiet", False)
        output_path = utils.find_unique_path(pathlib.Path(kwargs.pop("output_path")))
        tool = cls(**kwargs)
        tool.quiet = quiet
        inputs = utils.expand_paths(input_paths, sort=tool.SORT)
        for input_file in inputs:
            input_file.preprocess(use_temporary_file=not keep_trimmed_files)
        tool.process(inputs, output_path)
        utils.startfile(output_path)

    def process(self, inputs: list[utils.InputFile], output_path: pathlib.Path):
        raise NotImplementedError()
