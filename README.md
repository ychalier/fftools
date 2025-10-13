# FFtools

A set of graphical tools built upon FFmpeg and other graphics libraries.

## Getting Started

You'll need a working installation of [Python 3](https://www.python.org/). You'll also need [FFmpeg](https://ffmpeg.org/) binaries, available in `PATH`, the `ffmpeg -version` command should work.

### Basic Installation

The process should be straightforward.

1. Download the [latest release](https://github.com/ychalier/fftools/releases)
2. Install it with `pip`:
   ```console
   pip install ~/Downloads/fftools-X.X.X.tar.gz
   ```

### Alternative Installation

If you want to access the code.

1. Clone or [download](https://github.com/ychalier/fftools/archive/refs/heads/main.zip) this repository:
   ```console
   git clone https://github.com/ychalier/fftools.git
   cd fftools
   ```
2. Install requirements:
   ```console
   pip install -r requirements.txt
   ```

### Usage

The alias `fftools` represents either `python -m fftools` or `python cli.py`, depending on the chosen installation method.

```console
fftools <tool> [options]
```

See below for the list of available tools or run `fftools --help` for a summary.

## Tools

Most tools are applied to a single input file (except `blend-videos`, `concat` and `stack`). For each of them, you can specify one or more input file (glob patterns are supported) or folders (in which case all files within the folder are processed). The last argument will be considered as the template for the output filenames. This template can use the following placeholders:

- `{parent}` (path to the parent folder of the input file),
- `{stem}` (stem of the input filename, ie. filename without extension),
- `{suffix}` (suffix of the input filename, ie. extension with the dot).
- Some tools may also support additional placeholders, to allow for keeping track of processing parameters in the output filenames.

Such one-to-one tools also support the following flags:
- `-N, --no-execute`: prevent opening the file after processing,
- `-G, --global-progress`: show global progress when processing multiple files,
- `-O, --overwrite`: overwrite existing files (by default, unique filenames are generated),
- `-K, --keep-trimmed-files`: save trimmed input files next to their parent instead of a temporary folder (see paragraph below).

Many-to-one tools (like `blend-videos`, `concat` and `stack`) take their arguments in the same order (input files/folders first, then output path).

When processing video files, if you only want to process part of an input file, you can append a suffix of the form `#start-end` to the input filename, where `start` and `end` are timestamps in `HH:MM:SS[.FFF]` format or frame indices as integers. You can omit `start` or `end` to indicate the beginning or the end of the file respectively. For example, `input.mp4#30-90` will process the part of the video between frames 30 and 90, `input.mp4#30-` will skip the first 30 frames and `input.mp4#-30` will process the 30 frames of the video. By default, trimmed files are saved in a temporary folder. If you want to keep them, use the `-K, --keep-trimmed-files` flag.

For more details on each tool, run `fftools <tool> --help`.

Tool | Description
---- | -----------
`batch` | Wrapper to execute FFmpeg commands on multiple files. All keywords arguments are passed to FFmpeg as-is
`blend-to-image` | Extract the first frames of a video and merge them into a single image
`blend-frames` | Blend consecutive frames of a video together
`blend-videos` | Blend multiple videos into one. | -
`carve` | Resize an image using [seam carving](https://en.m.wikipedia.org/wiki/Seam_carving) (adapted from [andrewcampbell/seam-carving](https://github.com/andrewdcampbell/seam-carving), GPL3)
`concat` | Concatenate multiple image or video files into one video file | -
`cut` | Cut a media (image or video) in a grid given the size of the cells
`drop-iframe-multi` | Concatenate multiple clips with a datamoshing effect
`drop-iframe-single` | Exactly set a reference frames in a video clip and apply a datamoshing effect on it
`modulate` | Apply frequency modulation to images or videos
`preview` | Extract thumbnails of evenly spaced moments of a video
`probe` | Display information about a media file
`resize` | Resize any media (image or video), with smart features
`respeed` | Change the playback speed of a video, with smart features
`retime-panorama` | Retime a panoramic video to smoothen it
`scenes` | Extract a thumbnail of (roughly) every different scene in a video
`split` | Split a video file into parts of same duration
`stack` | Stack videos in a grid | -
`timestamp` | Add a timestamp over video given its creation datetime

## Contributing

Contributions are welcomed. Do not hesitate to submit a pull request with your changes! Submit bug reports and feature suggestions in the [issue tracker](https://github.com/ychalier/transflow/issues/new/choose).
