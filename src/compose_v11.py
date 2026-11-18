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
c1 = load(C + '/bake_col1.png', W); c2 = load(C + '/bake_col2.png', W); ao = load(C + '/bake_ao.png', W, 'L')
glb = load(R + 'v10/tex/v10_albedo.jpg', W)                     # v10 graded GLB albedo (bronze), macro variation only
rim, cav, hgt = c1[..., 0], c1[..., 1], c1[..., 2]; streak, radial, fmask = c2[..., 0], c2[..., 1], c2[..., 2]
cov = (c1.sum(2) > 0) | (fmask > 0)
# masks
rimm = sstep(E('RIM_LO', 0.18), E('RIM_HI', 0.75), rim) ** E('RIM_G', 1.0)
cavm = sstep(0.25, 0.85, cav)
lum = glb @ np.array([0.299, 0.587, 0.114], np.float32); lum_b = gaussian_filter(lum, 6)
var = np.clip(lum_b / max(np.median(lum_b[cov]), 1e-3), 0.55, 1.6) ** E('VAR_G', 0.55)
macro = gaussian_filter(glb, (6, 6, 0)); mg = macro @ np.array([0.299, 0.587, 0.114], np.float32)
macro = mg[..., None] + (macro - mg[..., None]) * E('MACRO_SAT', 0.35)      # desaturated: no stray purple on body creases
# palette (sRGB) sampled from the reference sheet: charcoal-plum body, copper edge, deep plum crevice
body = np.array([E('BODY_R', 0.115), E('BODY_G', 0.092), E('BODY_B', 0.102)], np.float32)
copper = np.array([0.80, 0.40, 0.16], np.float32); copper_dk = np.array([0.46, 0.20, 0.09], np.float32)
plum = np.array([0.105, 0.030, 0.13], np.float32)
b_lin = s2l(body)[None, None] * (0.72 + 0.5 * hgt[..., None]) * var[..., None]
b_lin = b_lin * (1 - E('MACRO_W', 0.3)) + s2l(macro) * E('MACRO_K', 0.55) * E('MACRO_W', 0.3)
cu_lin = s2l(copper_dk) + (s2l(copper) - s2l(copper_dk)) * sstep(0.4, 0.95, rim)[..., None]
alb = b_lin * (1 - rimm[..., None]) + cu_lin * rimm[..., None]
alb = alb * (1 - cavm[..., None] * 0.85) + s2l(plum) * cavm[..., None] * 0.85
# funnel texels: dark violet albedo
fv = s2l(np.array([0.07, 0.02, 0.10], np.float32)) * (0.5 + 1.0 * streak[..., None])
fw = sstep(0.3, 0.7, fmask)[..., None]; alb = alb * (1 - fw) + fv * fw
A = l2s(alb); A[~cov] = l2s(s2l(body))
Image.fromarray((A * 255).astype(np.uint8)).save(T + 'v11_albedo.jpg', quality=int(E('JQ', 90)))
# MR
rough = np.clip(E('ROUGH_BODY', 0.36) + 0.5 * cavm - 0.12 * rimm, 0.15, 1); rough = rough * (1 - fw[..., 0]) + 0.6 * fw[..., 0]
metal = np.clip(E('METAL_BODY', 0.5) * (1 - cavm) + 0.38 * rimm, 0, 1) * (1 - fw[..., 0])
MR = np.stack([np.ones_like(rough), rough, metal], -1)
Image.fromarray((MR * 255).astype(np.uint8)).resize((2048, 2048), Image.LANCZOS).save(T + 'v11_mr.jpg', quality=90)
# funnel emission: streaky violet, brightest near the Ø26 mouth, dim toward the Ø40 lip, dark gaps
e2 = 2048; st = np.asarray(Image.fromarray((streak * 255).astype(np.uint8)).resize((e2, e2), Image.LANCZOS)).astype(np.float32) / 255
rd = np.asarray(Image.fromarray((radial * 255).astype(np.uint8)).resize((e2, e2), Image.LANCZOS)).astype(np.float32) / 255
fm2 = np.asarray(Image.fromarray((fmask * 255).astype(np.uint8)).resize((e2, e2), Image.LANCZOS)).astype(np.float32) / 255
inten = (0.03 + 0.97 * st ** 1.5) * (0.07 + 0.93 * (1 - rd) ** E('FALL', 2.6)) * sstep(0.2, 0.6, fm2)
viol = np.array([0.50, 0.13, 0.95], np.float32); mag = np.array([0.85, 0.30, 0.95], np.float32)
mk = (0.25 + 0.5 * (1 - rd) ** 2)[..., None]                    # magenta toward the Ø26 mouth, violet outward
emit = (viol * (1 - mk) + mag * mk) * inten[..., None] * E('EMIT_GAIN', 1.0)
Image.fromarray((l2s(np.clip(emit, 0, 1)) * 255).astype(np.uint8)).save(T + 'v11_glow_emit.jpg', quality=90)
# AO x cavity, normal
aof = np.clip(gaussian_filter(ao, 1.0), 0, 1) * (1 - E('CAV_AO', 0.35) * cavm); aof = 1 - E('AO_SOFT', 0.85) * (1 - aof); aof[~cov] = 1
Image.fromarray((aof * 255).astype(np.uint8)).resize((2048, 2048), Image.LANCZOS).save(T + 'v11_ao.jpg', quality=90)
Image.open(C + '/bake_normal.png').convert('RGB').save(T + 'v11_normal.jpg', quality=int(E('NQ', 90)))
print('COMPOSE_DONE', {f: os.path.getsize(T + f) for f in ['v11_albedo.jpg', 'v11_mr.jpg', 'v11_glow_emit.jpg', 'v11_ao.jpg', 'v11_normal.jpg']}, flush=True)
