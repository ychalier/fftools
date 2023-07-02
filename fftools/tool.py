import os
import subprocess


class Tool:

    def __init__(self):
        pass

    @staticmethod
    def add_arguments(parser):
        pass

    @classmethod
    def from_keys(cls, args, args_keys, kwargs_keys):
        return cls(*[getattr(args, key) for key in args_keys], **{key: getattr(args, key) for key in kwargs_keys})

    @staticmethod
    def ffmpeg(*args, ffmpeg_path="ffmpeg", wait=True):
        process = subprocess.Popen([
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            *args
        ])
        if wait:
            process.wait()

    @staticmethod
    def format_timestamp(total_seconds):
        h = int(total_seconds / 3600)
        m = int((total_seconds - 3600 * h) / 60)
        s = int((total_seconds - 3600 * h - 60 * m))
        ms = round((total_seconds - 3600 * h - 60 * m - s) * 1000)
        return f"{str(h).rjust(2, '0')}:{str(m).rjust(2, '0')}:{str(s).rjust(2, '0')}.{str(ms).rjust(3, '0')}"
    
    @staticmethod
    def fts(ts):
        return Tool.format_timestamp(ts)

    def run(self):
        raise NotImplementedError
    
    @staticmethod
    def startfile(path):
        if os.path.isfile(path):
            os.startfile(path)