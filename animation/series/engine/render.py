"""Рендер серии: кадр Skia -> raw RGBA -> FFmpeg (H.264 1920x1080 30 fps)."""
import subprocess, time, sys
import numpy as np
import skia
from canvas import W, H, paint

FPS = 30


def render(scene, out_mp4, f0=0, f1=None, every=1, preview_scale=1.0, log_every=150):
    f1 = f1 if f1 is not None else scene.n_frames
    w, h = int(W * preview_scale), int(H * preview_scale)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}", "-r", str(FPS // every), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS // every), out_mp4]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    surf = skia.Surface(w, h)
    t0 = time.time()
    for f in range(f0, f1, every):
        c = surf.getCanvas()
        c.save()
        c.scale(preview_scale, preview_scale)
        scene.draw_frame(c, f)
        c.restore()
        arr = surf.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)
        pr.stdin.write(arr.tobytes())
        if (f - f0) % log_every == 0:
            print(f"frame {f}/{f1} {time.time() - t0:.0f}s", flush=True)
    pr.stdin.close()
    pr.wait()
    return time.time() - t0


def still(scene, f, path, scale=1.0):
    surf = skia.Surface(int(W * scale), int(H * scale))
    c = surf.getCanvas()
    c.scale(scale, scale)
    scene.draw_frame(c, f)
    surf.makeImageSnapshot().save(path)
