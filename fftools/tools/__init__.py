from ..tool import Tool
from .batch import Batch
from .blend import BlendImage, BlendFrame, BlendVideo
from .carve import Carve
from .concat import Concat
from .cut import Cut
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
    BlendFrame,
    BlendImage,
    BlendVideo,
    Carve,
    Concat,
    Cut,
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