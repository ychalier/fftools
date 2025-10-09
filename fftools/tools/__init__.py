from ..tool import Tool
from .batch import Batch
from .blend_frames import BlendFrames
from .blend_to_image import BlendToImage
from .blend_videos import BlendVideos
from .carve import Carve
from .concat import Concat
from .cut import Cut
from .frame_map import FrameMap
from .modulate import Modulate
from .preview import Preview
from .probe import Probe
from .resize import Resize
from .respeed import Respeed
from .retime_panorama import RetimePanorama
from .scenes import Scenes
from .split import Split
from .stack import Stack
from .timestamp import Timestamp


TOOL_LIST: list[type[Tool]] = [
    Batch,
    BlendFrames,
    BlendToImage,
    BlendVideos,
    Carve,
    Concat,
    Cut,
    FrameMap,
    Modulate,
    Preview,
    Probe,
    Resize,
    Respeed,
    RetimePanorama,
    Scenes,
    Split,
    Stack,
    Timestamp,
]