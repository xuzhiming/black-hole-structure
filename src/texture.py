# Procedural tileable organic textures (numpy + PIL), same idea as scifi_building/src/texture.py:
#   skin_albedo / skin_normal / skin_rough / skin_vein (emissive crevice mask), glow_emit (funnel streaks)
import numpy as np, os, sys
from PIL import Image
OUT = sys.argv[1] if len(sys.argv) > 1 else '/workspace/outputs/black_hole_structure/tex'
os.makedirs(OUT, exist_ok=True)
N = 2048
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)

def pnoise(octaves=5, base=8, seed=0, W=N, H=N):
    r = np.random.default_rng(seed); acc = np.zeros((H, W), np.float32); amp = 1.0; tot = 0
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
    for o in range(octaves):
        fx_, fy_ = base * 2**o, max(1, int(base * 2**o * H / W))
        g = r.random((fy_, fx_)).astype(np.float32)
        u = X * fx_ / W; v = Y * fy_ / H
        x0 = np.floor(u).astype(int); y0 = np.floor(v).astype(int)
        fx = u - x0; fy = v - y0; fx = fx*fx*(3-2*fx); fy = fy*fy*(3-2*fy)
        x1 = (x0+1) % fx_; y1 = (y0+1) % fy_; x0 %= fx_; y0 %= fy_
        a = g[y0, x0]*(1-fx) + g[y0, x1]*fx; b = g[y1, x0]*(1-fx) + g[y1, x1]*fx
        acc += amp * (a*(1-fy) + b*fy); tot += amp; amp *= 0.5
    return acc / tot

rng = np.random.default_rng(11)
# --- flowing organic grooves (stretched along u = tentacle length direction) ---
w1 = pnoise(4, 4, 1); w2 = pnoise(5, 8, 2)
flow = np.sin((yy / N) * 2*np.pi * 9 + (w1 - 0.5) * 9.0 + (xx / N) * 2*np.pi * 1)
groove = 0.5 + 0.5 * flow                       # 1 ridge, 0 groove
# --- pores: periodic stamped craters (dark hole + raised lip) and knobs ---
h = 0.55 * groove + 0.25 * w2
pore_mask = np.zeros((N, N), np.float32)        # 1 inside pore holes
def stamp(px, py, rad, fn):
    R = int(rad * 2.2) + 2
    xs = np.arange(int(px) - R, int(px) + R + 1); ys = np.arange(int(py) - R, int(py) + R + 1)
    X, Y = np.meshgrid(xs, ys); d = np.sqrt((X - px)**2 + (Y - py)**2) / rad
    fn(Y % N, X % N, d)
lip_mask = np.zeros((N, N), np.float32)
for i in range(2000):                           # pores (big + many micro pores)
    px, py = rng.random(2) * N; rad = (rng.uniform(10, 34) * (1.7 if rng.random() < 0.12 else 1.0)) if i < 420 else rng.uniform(4, 10)
    def f(Yi, Xi, d):
        lip = np.exp(-((d - 1.15) / 0.28)**2) * 0.35
        hole = np.clip(1.0 - d, 0, 1)**0.6
        h[Yi, Xi] += lip - hole * 0.9
        pore_mask[Yi, Xi] = np.maximum(pore_mask[Yi, Xi], np.clip((1.0 - d) * 4, 0, 1))
        lip_mask[Yi, Xi] = np.maximum(lip_mask[Yi, Xi], np.exp(-((d - 1.2) / 0.35)**2))
    stamp(px, py, rad, f)
for i in range(1400):                           # barnacle knobs
    px, py = rng.random(2) * N; rad = rng.uniform(5, 18)
    def f(Yi, Xi, d): h[Yi, Xi] += np.clip(1 - d*d, 0, 1)**1.5 * 0.35
    stamp(px, py, rad, f)
h += 0.06 * pnoise(5, 32, 5)
h = (h - h.min()) / (h.max() - h.min())

# --- colour (linear) ---
bronze_dk = np.array([0.011, 0.008, 0.011]); bronze = np.array([0.056, 0.040, 0.043])
rust = np.array([0.62, 0.24, 0.07]); purple = np.array([0.16, 0.035, 0.22]); pore_c = np.array([0.006, 0.003, 0.004])
n3 = pnoise(5, 6, 7)[..., None]; n4 = pnoise(4, 16, 8)[..., None]
H3 = h[..., None]
c = bronze_dk + (bronze - bronze_dk) * np.clip(H3 * 1.4, 0, 1)
c = c + (rust - c) * np.clip((H3 - 0.66) * 4.0, 0, 1) * (0.45 + 0.8 * n4**2)          # rusty highlights on ridges
c = c + (purple - c) * np.clip((0.48 - H3) * 3.0, 0, 1) * np.clip((n3 - 0.15) * 2, 0, 1)  # purple sheen in crevices
c = c * 0.55
lm = lip_mask[..., None] * (0.25 + 0.75 * n4**2)
c = c + (rust * 0.8 - c) * np.clip(lm, 0, 1) * 0.55                             # rusty rims around pores
pm = pore_mask[..., None]; c = c * (1 - pm) + pore_c * pm
c = np.clip(c, 0, 1)

def lin2srgb(a): return np.where(a <= 0.0031308, a*12.92, 1.055*np.power(np.clip(a, 0, 1), 1/2.4) - 0.055)
def save(name, a, srgb=False, size=None):
    a = np.clip(lin2srgb(a) if srgb else a, 0, 1)
    if a.ndim == 2: a = np.repeat(a[..., None], 3, -1)
    im = Image.fromarray((a * 255 + 0.5).astype(np.uint8))
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(os.path.join(OUT, name + '.png'))

st = 9.0
sx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * N / 64
sy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * N / 64
nx, ny, nz = -sx * st / 16 * 4, sy * st / 16 * 4, np.ones_like(h)
l = np.sqrt(nx*nx + ny*ny + nz*nz)
save('skin_albedo', c, True)
save('skin_normal', np.stack([nx/l, ny/l, nz/l], -1) * 0.5 + 0.5)
rough = np.clip(0.28 + 0.38 * (1 - h) - 0.25 * np.clip((h - 0.65) * 3, 0, 1) + 0.1 * (pnoise(4, 12, 9) - 0.5), 0.25, 1)
save('skin_rough', rough)
vein = np.clip((0.30 - h) * 4, 0, 1) * np.clip((n3[..., 0] - 0.45) * 2.5, 0, 1) + pore_mask * 0.3 * (n3[..., 0] > 0.62)
save('skin_vein', vein[..., None] * np.array([0.75, 0.12, 1.0]), True, (1024, 1024))

# --- funnel glow: u = around the hole (tileable), v = 0 core edge .. 1 outer ring ---
W, H = 1024, 256
Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
v = Y / (H - 1); u = X / W
sw = pnoise(5, 8, 21, W, H)
sw2 = pnoise(4, 3, 23, W, H); sw3 = pnoise(5, 24, 24, W, H)
ph = 2*np.pi * (u * 15 + v * 2.2) + (sw - 0.5) * 22 + (sw2 - 0.5) * 14           # strongly warped, uneven spacing
streak = (1 - np.abs(np.sin(ph * 0.5)))**2.0 * np.clip(0.2 + 1.5 * (sw2 - 0.3), 0.05, 1.3)   # ridges fade in / out
streak2 = 0.5 + 0.5 * np.sin(2*np.pi * (u * 37 - v * 1.5) + (pnoise(4, 16, 22, W, H) - 0.5) * 18)
streak = np.clip(streak + 0.5 * np.clip(sw3 - 0.55, 0, 1) * 3, 0, 1.5)                      # glowing blotches / lumps
band = np.where(v < 0.22, 0.7 * (np.clip(v, 0, 1) / 0.22)**3.0, 0.05 + 0.22 * ((v - 0.22) / 0.78)**2.2) + 1.1 * np.exp(-((v - 0.23) / 0.03)**2) + 1.0 * np.exp(-((v - 0.86) / 0.13)**2)
inten = band * (0.08 + 0.92 * np.clip(streak, 0, 1.5)**3.2) * (0.5 + 0.5 * streak2**2) * (0.6 + 0.8 * sw)
col = np.stack([0.70 * inten + 0.15 * inten**2, 0.02 * inten + 0.06 * inten**3, 1.0 * inten], -1)
col = col / max(1e-6, col.max()) * 1.0
save('glow_emit', col, True)
alb = np.stack([0.005 + 0.015*inten, 0.0015 + 0.002*inten, 0.008 + 0.02*inten], -1)   # dark funnel body; light from emission
save('glow_albedo', np.clip(alb, 0, 1), True)
print('TEX DONE', OUT)
