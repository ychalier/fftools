# FFmpeg Toolbelt

See also:

- [FFmpeg website](https://ffmpeg.org/)
- [FFmpeg Documentation](https://ffmpeg.org/ffmpeg-all.html)
- [FFmpeg Bug Tracker and Wiki](https://trac.ffmpeg.org/wiki)

## Tools

Tool | Description
---- | -----------
Average | Extract frames from a video and merge them into a single photo
Concat | Concatenate several videos into one
Merge | Merge images into a single video
Preview | Generate a table of preview snapshots for a video
Resize | Resize a video or an image
Respeed | Change the speed or the duration of a video
Shots | Extract all shots from a movie

## Cheatsheet

**Showing Motion Vectors**

```console
ffplay -flags2 +export_mvs input.mp4 -vf codecview=mv=pf+bf+bb
ffmpeg -flags2 +export_mvs -i input.mp4 -vf codecview=mv=pf+bf+bb output.mp4
```

Source: [Debugging Macroblocks and Motion Vectors](https://trac.ffmpeg.org/wiki/Debug/MacroblocksAndMotionVectors)

**Work with VR Videos**

Stereoscopic to Monoscopic: Over-under

```console
ffmpeg -i input.mp4 -vf crop=h=in_h/2:y=0 output.mp4
```

Stereoscopic to Monoscopic: Side-by-side

```console
ffmpeg -i input.mp4 -vf crop=w=in_w/2:x=0 output.mp4
```

Source: [FFmpeg Codes](https://www.vrtonung.de/en/ffmpeg-codes/)
