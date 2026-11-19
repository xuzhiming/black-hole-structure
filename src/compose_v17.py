# v17 stage C = v16 with round soft copper flecks (v16 used NEAREST-upsampled noise -> square, paper-like patches)
# v16 stage C = v15 + pinker hot-magenta funnel (less violet streak area), side-edge magenta crevice glow, brighter back, less copper on top
# v15 stage C (= compose_v14 + hotter magenta funnel, a few glowing crevices away from the funnel, copper flecks on the rear vortex)
# v14 stage C (system python): baked col1 (fine / broad convexity, pit) + 16-bit world position -> PBR maps tex/v14_*
#   albedo : dark maroon-brown body, copper on crests / tentacle ridges, deep plum-black in pores and crevices
#   mr     : G roughness, B metal;  ao: baked AO x cavity;  emit: funnel (streaks + v13 spiral ripples + magenta mouth ring)
#            + faint violet glow deep in crevices / pores near the funnel and along the tail (reference: purple in some crevices)
import numpy as np, os, json, sys, cv2
from PIL import Image
from scipy.ndimage import gaussian_filter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from ripple_v13 import ripple
Image.MAX_IMAGE_PIXELS = None
E = lambda k, d: float(os.environ.get(k, d))
C = os.environ.get('V14_CACHE', '/tmp/v14'); R = '/workspace/outputs/black_hole_structure/'; T = R + 'tex/'; W = 4096
OT = os.environ.get('TAG', 'v17')
I = json.load(open(C + '/infoA.json')); G = I['geom']; Y_E, Y_M = G['Y_E'], G['Y_M']
def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def s2l(c): c = np.asarray(c, np.float32); return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def l2s(c): c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
c1 = np.asarray(Image.open(C + '/bake_col1.png').convert('RGB')).astype(np.float32) / 255
pz = cv2.imread(C + '/bake_pos.png', cv2.IMREAD_UNCHANGED)[..., ::-1].astype(np.float32) / 65535.0
cov = pz.sum(2) > 1e-4
P = np.array(I['pos_lo'], np.float32) + pz * np.array(I['pos_size'], np.float32)
x, y, z = P[..., 0], P[..., 1], P[..., 2]
ao = np.asarray(Image.open(C + '/bake_ao.png').convert('L').resize((W, W), Image.BILINEAR)).astype(np.float32) / 255
cv1, cv3, pit = c1[..., 0], c1[..., 1], c1[..., 2]
rh = np.hypot(x, z - 58.0); th = np.arctan2(z - 58.0, x)
rf = np.where(y >= Y_E, 13.0 + 7.0 * np.clip((Y_M - y) / 18.0, 0, 1) ** 0.8, 20.0 + 0.35 * (Y_E - y))
fm = (sstep(1.6, 0.9, np.abs(rh - rf)) * (rh < 20.8) * (y > Y_E - 0.8) * (y < Y_M - 0.05) * cov).astype(np.float32)
crest = sstep(E('CR_LO', 0.6), E('CR_HI', 0.85), cv1) * sstep(0.42, 0.6, cv3)
crev = sstep(E('CV_HI', 0.42), E('CV_LO', 0.25), cv3)
pitm = sstep(0.35, 0.8, pit)
rngn = np.random.default_rng(3).normal(0, 1, (64, 64)).astype(np.float32)
var = 1 + E('VAR', 0.18) * np.asarray(Image.fromarray(rngn).resize((W, W), Image.BICUBIC))
body = s2l([E('BODY_R', 0.13), E('BODY_G', 0.075), E('BODY_B', 0.078)]); body2 = s2l([0.085, 0.05, 0.065])
copper = s2l([0.78, 0.40, 0.18]); plum = s2l([0.045, 0.018, 0.04])
mixb = sstep(0.3, 0.7, cv3)[..., None]
alb = (body2 * (1 - mixb) + body * mixb) * var[..., None]
fl = gaussian_filter(np.random.default_rng(7).normal(0, 1, (1024, 1024)).astype(np.float32), 1.2); fl = (fl - fl.mean()) / fl.std()
fl = np.asarray(Image.fromarray(fl).resize((W, W), Image.BICUBIC))
fleck = sstep(E('FLECK_T', 1.9), E('FLECK_T', 1.9) + 0.5, fl) * sstep(0.45, 0.6, cv3) * sstep(4.0, 12.0, y)
crest = np.maximum(crest, fleck * 0.8)
cw = (crest * E('CU_W', 0.85) * (1 - E('CU_TOP', 0.5) * sstep(78.0, 100.0, z)))[..., None]; alb = alb * (1 - cw) + copper * cw
NO = np.asarray(Image.open(C + '/bake_nobj.png').convert('RGB').resize((W, W), Image.BILINEAR)).astype(np.float32) / 127.5 - 1.0
alb = alb * (1 + E('REAR_GAIN', 0.25) * sstep(0.05, 0.6, NO[..., 1]))[..., None]          # rear-facing surfaces (object normal +Y) a little lighter (reference rear L ~21)
dk = np.clip(np.maximum(pitm, crev) * 0.9, 0, 1)[..., None]; alb = alb * (1 - dk) + plum * dk
fv = s2l([0.03, 0.012, 0.045]); alb = alb * (1 - fm[..., None]) + fv * fm[..., None]
A = l2s(alb); A[~cov] = l2s(body)
Image.fromarray((A * 255).astype(np.uint8)).save(T + OT + '_albedo.jpg', quality=90)
rough = np.clip(E('ROUGH', 0.5) - 0.18 * crest + 0.3 * np.maximum(pitm, crev), 0.15, 1) * (1 - fm) + 0.55 * fm
metal = np.clip(E('METAL', 0.35) + 0.4 * crest - 0.3 * np.maximum(pitm, crev), 0, 1) * (1 - fm)
MR = np.stack([np.ones_like(rough), rough, metal], -1)
Image.fromarray((MR * 255).astype(np.uint8)).resize((2048, 2048), Image.LANCZOS).save(T + OT + '_mr.jpg', quality=90)
# funnel emission
dep = np.clip((Y_M - y) / 18.0, 0, 1.3)                 # 0 at the Ø26 mouth, 1 at the lip plane
r_eff = 13.0 + (Y_M - y) * E('RIP_Y', 0.75)
ph = r_eff / E('STR_RING', 0.5) + 3 * th / (2 * np.pi); rid = np.floor(ph)
hsh = lambda k, s_: (np.sin(k * 12.9898 + s_ * 78.233) * 43758.5453) % 1.0
amp = 0.2 + 0.8 * hsh(rid, 1.0) ** 1.6
brk = sstep(0.3, 0.8, 0.5 + 0.5 * np.sin(th * (2 + np.floor(7 * hsh(rid, 2.0))) + 6.28 * hsh(rid, 3.0)))
streak = np.exp(-(((ph - rid) - 0.5) / 0.14) ** 2) * amp * (0.25 + 0.75 * brk)
rip = np.zeros_like(x); m = fm > 0; rip[m] = ripple(r_eff[m], th[m])
prof = (0.25 + 0.75 * np.exp(-((dep - E('PEAK', 0.35)) / 0.45) ** 2))
inten = (streak * E('STREAK_GAIN', 0.5) + rip * E('RIP_EMIT', 1.1)) * prof
ring = np.exp(-((dep - 0.04) / E('RING_W', 0.05)) ** 2) * E('RING_GAIN', 0.35)
viol = np.array([E('VIOL_R', 0.75), 0.12, E('VIOL_B', 0.85)], np.float32); mag = np.array([1.0, 0.18, 0.78], np.float32) * E('MAG_GAIN', 1.25)
mk = np.clip(E('MAG_MIX', 0.55) + 0.45 * (1 - dep), 0, 1)[..., None]
emit = ((viol * (1 - mk) + mag * mk) * inten[..., None] + mag * ring[..., None]) * fm[..., None]
# skin crevice glow (only where the reference shows it: around the funnel, inside the tail sweep)
near = sstep(34.0, 22.0, rh) * (y < 2) + 0.6 * sstep(30.0, 15.0, z) * sstep(-40, -20, x) * 0
pg = np.random.default_rng(11).random((24, 24)).astype(np.float32); pg = np.asarray(Image.fromarray(pg).resize((W, W), Image.BICUBIC))
near = np.maximum(near, sstep(0.86, 0.95, pg) * 0.8)
cg = np.clip(np.maximum(crev * 0.8, pitm) * near * (1 - fm), 0, 1) * E('CREV_GLOW', 0.35)
emit = emit + viol * cg[..., None]
# v16: magenta glow deep in crevices / pores on the side edges (reference side views ~5 % purple)
side = sstep(E('SIDE_N0', 0.55), E('SIDE_N1', 0.9), np.abs(NO[..., 0])) * sstep(E('SIDE_X0', 20.0), E('SIDE_X1', 34.0), np.abs(x)) * (1 - fm)   # side-facing (|n.x|) on the outer flanks
sg = np.clip(np.maximum(crev, E('SIDE_PIT', 0.4) * pitm) ** 0.7 * side * np.where(x < 0, E('SIDE_NEG', 1.0), 1.0), 0, 1) * E('SIDE_GLOW', 0.8)
emit = emit + mag * sg[..., None]
emit[~cov] = 0
Image.fromarray((l2s(np.clip(emit * E('EMIT_GAIN', 1.0), 0, 1)) * 255).astype(np.uint8)).save(T + OT + '_glow_emit.jpg', quality=90)
aof = np.clip(gaussian_filter(ao, 1.0), 0, 1) * (1 - 0.3 * np.maximum(pitm, crev)); aof = 1 - E('AO_SOFT', 0.85) * (1 - aof); aof[~cov] = 1
Image.fromarray((aof * 255).astype(np.uint8)).resize((2048, 2048), Image.LANCZOS).save(T + OT + '_ao.jpg', quality=90)
Image.open(C + '/bake_normal.png').convert('RGB').save(T + OT + '_normal.jpg', quality=90)
print('COMPOSE_DONE', {k: os.path.getsize(T + f'{OT}_{k}.jpg') for k in ['albedo', 'mr', 'glow_emit', 'ao', 'normal']}, 'funnel_frac', float(fm[cov].mean()), 'crest', float(crest[cov].mean()), flush=True)
