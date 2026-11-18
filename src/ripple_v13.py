# v13: the v11 funnel ripple (regular wavy rings), shared by scales_v13 (geometry -> baked normal) and compose_v13 (texture),
# so geometry and texture ripples line up. v11 used 2.2 swirl turns (non-integer -> seam at th = +-pi); v13 uses an integer
# SWIRL so the ripples read as a continuous N-armed inward spiral with no seam.
import os, numpy as np
E = lambda k, d: float(os.environ.get(k, d))
_g = np.random.default_rng(1313)
P1 = _g.uniform(0, 6.3, 32); P2 = _g.uniform(0, 6.3, 32)
def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def ripple(r, th):
    nz = sum(np.sin(k * th + P1[i]) / k ** 0.8 for i, k in enumerate(range(3, 23, 2)))
    nz2 = sum(np.sin(k * th + P2[i] + 0.7 * k * r / 20) / k ** 0.6 for i, k in enumerate(range(2, 30, 3)))
    ph = r / E('RIP_RING', 0.95) + E('SWIRL', 3) * th / (2 * np.pi) + E('RIP_WAVE', 0.8) * nz + 0.25 * np.sin(r * 1.7 + 3 * th)
    seg = sstep(-0.4, 0.9, nz2)
    return ((0.5 + 0.5 * np.sin(2 * np.pi * ph)) ** E('STREAK_P', 5.0) * (0.25 + 0.75 * seg)).astype(np.float32)
