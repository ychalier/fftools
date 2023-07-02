# FFmpeg Cheatsheet

## Showing Motion Vectors

Source: [Debugging Macroblocks and Motion Vectors](https://trac.ffmpeg.org/wiki/Debug/MacroblocksAndMotionVectors)

```console
ffplay -flags2 +export_mvs input.mp4 -vf codecview=mv=pf+bf+bb
ffmpeg -flags2 +export_mvs -i input.mp4 -vf codecview=mv=pf+bf+bb output.mp4
```

## Work with VR Videos

Source: [FFmpeg Codes](https://www.vrtonung.de/en/ffmpeg-codes/)

### Stereoscopic to Monoscopic: Over-under

```console
ffmpeg -i input.mp4 -vf crop=h=in_h/2:y=0 output.mp4
```

### Stereoscopic to Monoscopic: Side-by-side

```console
ffmpeg -i input.mp4 -vf crop=w=in_w/2:x=0 output.mp4
```

