import os
import pathlib
import shutil
import tempfile
import unittest

import cv2
import PIL.Image
import numpy

import fftools
from fftools.tool import OneToOneTool, ManyToOneTool
from fftools.utils import InputFile


class TestTools(unittest.TestCase):
    
    HEIGHT = 18
    WIDTH = 32
    DURATION = 4
    FRAMERATE = 1

    def setUp(self):
        self.folder = pathlib.Path(tempfile.gettempdir()) / "fftools-tests"
        if self.folder.exists():
            shutil.rmtree(self.folder)
        self.folder.mkdir()
        self.input_image: InputFile = self._create_dummy_image(self.folder / "dummy.png")
        self.input_video: InputFile = self._create_dummy_video(self.folder / "dummy.mp4")        
        self.addCleanup(self._remove_folder)
    
    def _create_dummy_image(self, path: pathlib.Path) -> InputFile:
        PIL.Image.fromarray(numpy.zeros((self.HEIGHT, self.WIDTH, 3), dtype=numpy.uint8)).save(path)
        return InputFile(path)
    
    def _create_dummy_video(self, path: pathlib.Path) -> InputFile:
        fourcc = cv2.VideoWriter.fourcc(*"mp4v")
        writer = cv2.VideoWriter(path.as_posix(), fourcc, self.FRAMERATE, (self.WIDTH, self.HEIGHT))
        for _ in range(self.DURATION):
            frame = numpy.zeros((self.HEIGHT, self.WIDTH, 3), dtype=numpy.uint8)
            frame[:,:,frame % 3] = 255
            writer.write(frame)
        writer.release()
        return InputFile(path)

    def _remove_folder(self):
        if self.folder.exists():
            shutil.rmtree(self.folder)

    def _test_one_to_one_tool(self, cls: type[OneToOneTool], video: bool, *args, **kwargs) -> pathlib.Path:
        tool = cls(cls.OUTPUT_PATH_TEMPLATE, *args, **kwargs)
        output_path = tool.process(self.input_video if video else self.input_image)
        self.assertIsNotNone(output_path)
        assert output_path is not None
        self.assertTrue(output_path.exists())
        return output_path

    def _test_many_to_one_tool(self, cls: type[ManyToOneTool], *args, **kwargs) -> pathlib.Path:
        tool = cls(*args, **kwargs)
        output_path = self.folder / "out.mp4"
        if output_path.exists():
            os.remove(output_path)
        tool.process([self.input_video, self.input_video, self.input_video], output_path)
        self.assertTrue(output_path.exists())
        return output_path

    def test_blend_frames(self):
        self._test_one_to_one_tool(fftools.tools.BlendFrames, True)
        
    def test_blend_to_image(self):
        self._test_one_to_one_tool(fftools.tools.BlendToImage, True)
        
    def test_blend_videos(self):
        self._test_many_to_one_tool(fftools.tools.BlendVideos)
    
    def test_carve(self):
        self._test_one_to_one_tool(fftools.tools.Carve, False, width=self.WIDTH-1, height=self.HEIGHT+1)
    
    def test_cut(self):
        for video in [True, False]:
            self._test_one_to_one_tool(fftools.tools.Cut, video, max_width=self.WIDTH//2, max_height=self.HEIGHT//2)

    def test_drop_iframe_multi(self):
        self._test_many_to_one_tool(fftools.tools.DropIFrameMulti)
    
    def test_drop_iframe_single(self):
        self._test_one_to_one_tool(fftools.tools.DropIFrameSingle, True, preserve_timings=True, iframe="True")
    
    def test_modulate(self):
        for video in [True, False]:
            self._test_one_to_one_tool(fftools.tools.Modulate, video, "outer", 0.5)

    def test_preview(self):
        self._test_one_to_one_tool(fftools.tools.Preview, True, nrows=2, ncols=2)
    
    def test_probe(self):
        self._test_one_to_one_tool(fftools.tools.Probe, True)
    
    def test_resize(self):
        self._test_one_to_one_tool(fftools.tools.Resize, True, width=self.WIDTH//2)
    
    def test_respeed(self):
        self._test_one_to_one_tool(fftools.tools.Respeed, True, target="x2")
    
    def test_retime_panorama(self):
        self._test_one_to_one_tool(fftools.tools.RetimePanorama, True, 1)
    
    def test_scenes(self):
        path = self._test_one_to_one_tool(fftools.tools.Scenes, True, bin_width=1)
        self.assertTrue(path.is_dir())
    
    def test_split(self):
        path = self._test_one_to_one_tool(fftools.tools.Split, True, duration="00:00:01")
        self.assertTrue(path.is_dir())
    
    def test_squeeze(self):
        self._test_one_to_one_tool(fftools.tools.Squeeze, True)
    
    def test_stack(self):
        self._test_many_to_one_tool(fftools.tools.Stack)
    
    def test_timestamp(self):
        self._test_one_to_one_tool(fftools.tools.Timestamp, True)


if __name__ == "__main__":
    unittest.main()
