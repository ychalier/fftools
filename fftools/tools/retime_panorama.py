import math
from pathlib import Path
from typing import Tuple

import cv2
import numpy

from ..tool import OneToOneTool
from ..utils import VideoInput, VideoOutput, InputFile


def moving_average(x: numpy.ndarray, radius: int) -> numpy.ndarray:
    if radius <= 0:
        return x.copy()
    k = 2 * radius + 1
    pad_left = x[0] * numpy.ones(radius, dtype=numpy.float32)
    pad_right = x[-1] * numpy.ones(radius, dtype=numpy.float32)
    xp = numpy.concatenate([pad_left, x.astype(numpy.float32), pad_right])
    c = numpy.convolve(xp, numpy.ones(k, dtype=numpy.float32) / k, mode="valid")
    return c.astype(numpy.float32)


def enforce_monotonic(x: numpy.ndarray, increasing: bool) -> numpy.ndarray:
    out = x.copy()
    if increasing:
        for i in range(1, len(out)):
            if out[i] < out[i - 1]:
                out[i] = out[i - 1]
    else:
        for i in range(1, len(out)):
            if out[i] > out[i - 1]:
                out[i] = out[i - 1]
    return out


def estimate_motion(
        vin: VideoInput,
        max_corners=800,
        quality_level=0.01,
        min_distance=8,
        win_size=(21, 21),
        max_level=3,
        ransac_thresh=3.0,
        ) -> Tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray]:
    if vin.length < 2:
        raise ValueError("Video is too short (need at least 2 frames).")
    prev = vin.at(0)
    prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
    dx = numpy.zeros(vin.length - 1, dtype=numpy.float32)
    dy = numpy.zeros(vin.length - 1, dtype=numpy.float32)
    valid = numpy.zeros(vin.length - 1, dtype=numpy.bool_)
    for i in range(1, vin.length):
        try:
            curr = next(vin)
        except StopIteration:
            break
        curr_gray = cv2.cvtColor(curr, cv2.COLOR_RGB2GRAY)
        p0 = cv2.goodFeaturesToTrack(
            prev_gray,
            mask=None,
            maxCorners=max_corners,
            qualityLevel=quality_level,
            minDistance=min_distance,
            blockSize=3)
        if p0 is None or len(p0) < 10:
            prev_gray = curr_gray
            continue
        p1 = p0.copy()
        p1, st, err = cv2.calcOpticalFlowPyrLK(
            prev_gray,
            curr_gray,
            p0,
            p1,
            None,
            None,
            winSize=win_size,
            maxLevel=max_level,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
        )
        if p1 is None:
            prev_gray = curr_gray
            continue
        st = st.reshape(-1) > 0
        p0v = p0.reshape(-1, 2)[st]
        p1v = p1.reshape(-1, 2)[st]
        if len(p0v) < 10:
            prev_gray = curr_gray
            continue
        M, inliers = cv2.estimateAffinePartial2D(p0v, p1v, method=cv2.RANSAC, ransacReprojThreshold=ransac_thresh)
        if M is None:
            d = p1v - p0v
            dx[i - 1] = numpy.median(d[:, 0])
            dy[i - 1] = numpy.median(d[:, 1])
            valid[i - 1] = True
        else:
            dx[i - 1] = M[0, 2]
            dy[i - 1] = M[1, 2]
            valid[i - 1] = True
        prev_gray = curr_gray
    return dx, dy, valid


def build_cumulative_path(dx: numpy.ndarray, dy: numpy.ndarray, valid: numpy.ndarray) -> Tuple[numpy.ndarray, numpy.ndarray]:
    dx2 = dx.copy()
    dy2 = dy.copy()
    dx2[~valid] = 0.0
    dy2[~valid] = 0.0
    x = numpy.concatenate([[0.0], numpy.cumsum(dx2)]).astype(numpy.float32)
    y = numpy.concatenate([[0.0], numpy.cumsum(dy2)]).astype(numpy.float32)
    return x, y


def decide_axis(x: numpy.ndarray, y: numpy.ndarray) -> str:
    range_x = float(numpy.abs(x[-1] - x[0]))
    range_y = float(numpy.abs(y[-1] - y[0]))
    return "x" if range_x >= range_y else "y"


def remap_indices_to_constant_speed(pos: numpy.ndarray) -> numpy.ndarray:
    N = len(pos)
    frames = numpy.arange(N, dtype=numpy.float32)
    target_pos = numpy.linspace(pos[0], pos[-1], N).astype(numpy.float32)
    increasing = pos[-1] >= pos[0]
    if not increasing:
        pos_flip = pos[::-1]
        frames_flip = frames[::-1]
        src_idx = numpy.interp(target_pos, pos_flip, frames_flip)
    else:
        src_idx = numpy.interp(target_pos, pos, frames)
    return src_idx.astype(numpy.float32)


class RetimePanorama(OneToOneTool):

    NAME = "retime-panorama"
    DESC = "Retime a panoramic video to smoothen it."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_retimed_{radius}{suffix}"

    def __init__(self,
            template: str,
            radius: int):
        OneToOneTool.__init__(self, template)
        self.radius = radius

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("-r", "--radius", type=int, default=1, help="Moving-average radius (in frames) for trajectory")

    def process(self, input_file: InputFile) -> Path:
        output_path = self.inflate(input_file.path, {"radius": self.radius})
        with VideoInput(input_file.path) as vin:
            dx, dy, valid = estimate_motion(vin)
            x, y = build_cumulative_path(dx, dy, valid)
            axis = decide_axis(x, y)
            pos = x if axis == "x" else y
            pos_sm = moving_average(pos, radius=max(0, self.radius))
            increasing = pos_sm[-1] >= pos_sm[0]
            pos_mono = enforce_monotonic(pos_sm, increasing=increasing)
            src_idx = remap_indices_to_constant_speed(pos_mono)
            with VideoOutput(output_path, vin.width, vin.height, vin.framerate, vin.length, hide_progress=self.quiet) as vout:
                for i in range(vin.length):
                    t = src_idx[i]
                    j0 = int(numpy.clip(math.floor(t), 0, vin.length - 1))
                    j1 = int(numpy.clip(j0 + 1, 0, vin.length - 1))
                    alpha = float(t - j0)
                    if j0 == j1:
                        frame = vin.at(j0)
                    else:
                        f0 = vin.at(j0)
                        f1 = vin.at(j1)
                        frame = cv2.addWeighted(f0, 1.0 - alpha, f1, alpha, 0.0)
                    vout.feed(frame)
        return output_path
