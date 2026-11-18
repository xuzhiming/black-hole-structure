# v12 stage C (from v11): grey-blue plate tops, desaturated plum gaps, less crest copper, dark funnel with fine streaks + magenta Ø26 ring
# v11 stage C (system python): build the final maps in the GLB's UV space from the bakes
#   albedo  : near-black bronze body (GLB albedo only as low-contrast macro variation) + copper on scale free edges / crests
#             + deep plum in gaps / pits; funnel texels dark violet
#   mr      : G roughness (sharper body specular, matte cavities), B metal (copper edges most metallic)
#   emit    : funnel only - streaky violet rings, bright near the Ø26 mouth, dark gaps
#   normal  : tangent bake (scales), ao: bake x cavity
import os, json, numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, maximum_filter
C = os.environ.get('V11_CACHE', '/tmp/v11'); R = '/workspace/outputs/black_hole_structure/'; T = R + 'tex/'
E = lambda k, d: float(os.environ.get(k, d)); W = int(os.environ.get('ALB_RES', 4096))
def load(p, size, mode='RGB'):
    im = Image.open(p).convert(mode)
    if im.size != (size, size): im = im.resize((size, size), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255
def s2l(x): return np.where(x > 0.04045, ((x + 0.055) / 1.055) ** 2.4, x / 12.92)
def l2s(x): x = np.clip(x, 0, 1); return np.where(x > 0.0031308, 1.055 * x ** (1 / 2.4) - 0.055, 12.92 * x)
def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
c1 = load(C + '/bake_col1.png', W); ao = load(C + '/bake_ao.png', W, 'L')
import cv2
c2 = cv2.imread(C + '/bake_col2.png', cv2.IMREAD_UNCHANGED)[..., ::-1].astype(np.float32) / 65535.0
if c2.shape[0] != W: c2 = cv2.resize(c2, (W, W), interpolation=cv2.INTER_LINEAR)
r_m = c2[..., 0] * 40.0; fmask = sstep(0.24, 0.3, c2[..., 0]); th = np.arctan2(c2[..., 2] * 2 - 1, c2[..., 1] * 2 - 1)
radial = np.clip((r_m - 13.0) / 7.5, 0, 1)
# fine inward-spiralling streaks, per texel: integer turns (no seam), each streak its own brightness, broken along its length
ring_w = E('RING', 0.5); ph = r_m / ring_w + 3 * th / (2 * np.pi); rid = np.floor(ph)
hsh = lambda k, s_: (np.sin(k * 12.9898 + s_ * 78.233) * 43758.5453) % 1.0
amp = 0.2 + 0.8 * hsh(rid, 1.0) ** 1.6
brk = sstep(0.3, 0.8, 0.5 + 0.5 * np.sin(th * (2 + np.floor(7 * hsh(rid, 2.0))) + 6.28 * hsh(rid, 3.0)))
streak = (np.exp(-(((ph - rid) - 0.5) / E('STREAK_W', 0.14)) ** 2) * amp * (0.25 + 0.75 * brk) * fmask).astype(np.float32)
glb = load(R + 'v10/tex/v10_albedo.jpg', W)                     # v10 graded GLB albedo (bronze), macro variation only
rim, cav, top = c1[..., 0], c1[..., 1], c1[..., 2]
cov = (c1.sum(2) > 0) | (fmask > 0)
# masks
rimm = sstep(E('RIM_LO', 0.14), E('RIM_HI', 0.6), rim) ** E('RIM_G', 1.0)
cavm = sstep(E('CAV_LO', 0.2), E('CAV_HI', 0.7), cav)
lum = glb @ np.array([0.299, 0.587, 0.114], np.float32); lum_b = gaussian_filter(lum, 6)
var = np.clip(lum_b / max(np.median(lum_b[cov]), 1e-3), 0.55, 1.6) ** E('VAR_G', 0.55)
macro = gaussian_filter(glb, (6, 6, 0)); mg = macro @ np.array([0.299, 0.587, 0.114], np.float32)
macro = mg[..., None] + (macro - mg[..., None]) * E('MACRO_SAT', 0.35)      # desaturated: no stray purple on body creases
# palette (sRGB) sampled from the reference sheet: charcoal-plum body, copper edge, deep plum crevice
body = np.array([E('BODY_R', 0.115), E('BODY_G', 0.092), E('BODY_B', 0.102)], np.float32)
copper = np.array([0.80, 0.40, 0.16], np.float32); copper_dk = np.array([0.46, 0.20, 0.09], np.float32)
plum = np.array([0.065, 0.028, 0.075], np.float32); sheen = np.array([E('SHEEN_R', 0.15), E('SHEEN_G', 0.155), E('SHEEN_B', 0.185)], np.float32)
topm = sstep(0.2, 0.8, top)[..., None] * E('SHEEN_W', 0.55)
b_lin = (s2l(body)[None, None] * (1 - topm) + s2l(sheen)[None, None] * topm) * var[..., None]
b_lin = b_lin * (1 - E('MACRO_W', 0.3)) + s2l(macro) * E('MACRO_K', 0.55) * E('MACRO_W', 0.3)
cu_lin = s2l(copper_dk) + (s2l(copper) - s2l(copper_dk)) * sstep(0.4, 0.95, rim)[..., None]
alb = b_lin * (1 - rimm[..., None]) + cu_lin * rimm[..., None]
alb = alb * (1 - cavm[..., None] * 0.92) + s2l(plum) * cavm[..., None] * 0.92
# funnel texels: dark violet albedo
fv = s2l(np.array([0.028, 0.012, 0.04], np.float32)) * (0.6 + 1.2 * streak[..., None])
fw = sstep(0.3, 0.7, fmask)[..., None]; alb = alb * (1 - fw) + fv * fw
A = l2s(alb); A[~cov] = l2s(s2l(body))
Image.fromarray((A * 255).astype(np.uint8)).save(T + 'v12_albedo.jpg', quality=int(E('JQ', 90)))
# MR
rough = np.clip(E('ROUGH_BODY', 0.42) - E('ROUGH_TOP', 0.16) * sstep(0.2, 0.8, top) + 0.45 * cavm - 0.1 * rimm, 0.15, 1); rough = rough * (1 - fw[..., 0]) + 0.6 * fw[..., 0]
metal = np.clip(E('METAL_BODY', 0.42) * (1 - cavm) * (1 - 0.6 * sstep(0.2, 0.8, top)) + 0.45 * rimm, 0, 1) * (1 - fw[..., 0])
MR = np.stack([np.ones_like(rough), rough, metal], -1)
Image.fromarray((MR * 255).astype(np.uint8)).resize((2048, 2048), Image.LANCZOS).save(T + 'v12_mr.jpg', quality=90)
# funnel emission: streaky violet, brightest near the Ø26 mouth, dim toward the Ø40 lip, dark gaps
st = streak
rd = radial
fm2 = fmask
# v12: mostly dark; fine streaks fading outward; hot magenta-violet ring right at the Ø26 mouth (radial 0 = r 13 m, 1 = r 20.5 m)
fm_ = sstep(0.2, 0.6, fm2)
inten = st * (0.12 + 0.88 * (1 - rd) ** E('FALL', 3.0)) * E('STREAK_GAIN', 0.55)
ring = np.exp(-((rd - E('RING_C', 0.07)) / E('RING_W', 0.07)) ** 2)
viol = np.array([0.42, 0.10, 0.92], np.float32); mag = np.array([0.95, 0.25, 0.85], np.float32)
emit = (viol[None, None] * inten[..., None] + mag[None, None] * (ring * E('RING_GAIN', 0.9))[..., None]) * fm_[..., None] * E('EMIT_GAIN', 1.0)
Image.fromarray((l2s(np.clip(emit, 0, 1)) * 255).astype(np.uint8)).save(T + 'v12_glow_emit.jpg', quality=90)
# AO x cavity, normal
aof = np.clip(gaussian_filter(ao, 1.0), 0, 1) * (1 - E('CAV_AO', 0.35) * cavm); aof = 1 - E('AO_SOFT', 0.85) * (1 - aof); aof[~cov] = 1
Image.fromarray((aof * 255).astype(np.uint8)).resize((2048, 2048), Image.LANCZOS).save(T + 'v12_ao.jpg', quality=90)
Image.open(C + '/bake_normal.png').convert('RGB').save(T + 'v12_normal.jpg', quality=int(E('NQ', 90)))
print('COMPOSE_DONE', {f: os.path.getsize(T + f) for f in ['v12_albedo.jpg', 'v12_mr.jpg', 'v12_glow_emit.jpg', 'v12_ao.jpg', 'v12_normal.jpg']}, flush=True)
