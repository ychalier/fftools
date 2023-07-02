import subprocess


class Tool:

    def __init__(self, ffmpeg_path="ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    @staticmethod
    def add_arguments(parser):
        pass

    @classmethod
    def from_keys(cls, args, args_keys, kwargs_keys):
        return cls(*[getattr(args, key) for key in args_keys], **{key: getattr(args, key) for key in kwargs_keys})

    def ffmpeg(self, *args):
        subprocess.Popen([
            self.ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            *args
        ]).wait()

    def run(self):
        raise NotImplementedError