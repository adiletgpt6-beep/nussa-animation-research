"""2D-вид: «чернильный» контур по границам цветовых пятен + лёгкая фактура бумаги.
python postprocess_2d.py IN_DIR OUT_DIR"""
import sys, os, glob
import numpy as np, cv2

src, dst = sys.argv[1:3]
os.makedirs(dst, exist_ok=True)
paper = None
for p in sorted(glob.glob(os.path.join(src, "*.png"))):
    out = os.path.join(dst, os.path.basename(p))
    if os.path.exists(out):
        continue
    img = cv2.imread(p)
    h, w = img.shape[:2]
    if paper is None:
        rng = np.random.default_rng(3)
        n = cv2.GaussianBlur(rng.standard_normal((h // 2, w // 2)).astype(np.float32), (0, 0), 1.2)
        n = cv2.resize(n, (w, h))
        paper = (1.0 - 0.035 * (n - n.min()) / (n.max() - n.min())).astype(np.float32)[..., None]
    sm = cv2.bilateralFilter(img, 7, 40, 7)
    lab = cv2.cvtColor(sm, cv2.COLOR_BGR2LAB)
    e = np.zeros((h, w), np.uint8)
    for c, (lo, hi) in zip(range(3), ((28, 70), (18, 45), (18, 45))):
        e |= cv2.Canny(lab[..., c], lo, hi)
    e = cv2.dilate(e, np.ones((2, 2), np.uint8), iterations=1)
    m = cv2.GaussianBlur(e.astype(np.float32) / 255.0, (0, 0), 0.8)[..., None] * 0.85
    ink = np.array([38, 30, 34], np.float32)
    res = img.astype(np.float32) * (1 - m) + ink * m
    res = res * paper
    cv2.imwrite(out, np.clip(res, 0, 255).astype(np.uint8))
print("ok")
