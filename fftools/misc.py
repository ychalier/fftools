def format_ffmpeg_timestamp(total_seconds):
    h = int(total_seconds / 3600)
    m = int((total_seconds - 3600 * h) / 60)
    s = int((total_seconds - 3600 * h - 60 * m))
    ms = round((total_seconds - 3600 * h - 60 * m - s) * 1000)
    return f"{str(h).rjust(2, '0')}:{str(m).rjust(2, '0')}:{str(s).rjust(2, '0')}.{str(ms).rjust(3, '0')}"
