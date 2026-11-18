# v10 textures from the user's GLB: albedo (optional bronze grade), MR -> JPEG, high-pass luminance height (bake relief)
import json, struct, os, sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter
R = '/workspace/outputs/black_hole_structure/'; T = R + 'tex/'; SRC = R + 'ref_glb/user_tripo.glb'
d = open(SRC, 'rb').read(); l = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20 + l]); b0 = 20 + l + 8
def blob(i): bv = j['bufferViews'][j['images'][i]['bufferView']]; o = b0 + bv.get('byteOffset', 0); return d[o:o + bv['byteLength']]
import io
mat = j['materials'][0]; ia = j['textures'][mat['pbrMetallicRoughness']['baseColorTexture']['index']]['source']
im_mr = j['textures'][mat['pbrMetallicRoughness']['metallicRoughnessTexture']['index']]['source']
A = Image.open(io.BytesIO(blob(ia))).convert('RGB'); MR = Image.open(io.BytesIO(blob(im_mr))).convert('RGB')
GRADE = float(os.environ.get('GRADE', '0.0'))
a = np.asarray(A).astype(np.float32) / 255
if GRADE > 0:
    # pull the mauve/pink toward the reference's dark bronze + copper, keep saturated purples (glow / veins)
    lum = a @ np.array([0.299, 0.587, 0.114]); mx = a.max(2); mn = a.min(2); sat = (mx - mn) / np.maximum(mx, 1e-4)
    purple = np.clip(((a[..., 2] - a[..., 1]) * 4 - 0.15), 0, 1) * np.clip(sat * 2 - 0.4, 0, 1)
    stops = np.array([0.0, 0.08, 0.2, 0.38, 0.6, 1.0]); cols = np.array([[0.015, 0.012, 0.018], [0.075, 0.05, 0.065], [0.20, 0.13, 0.12], [0.42, 0.27, 0.18], [0.74, 0.48, 0.30], [0.97, 0.78, 0.58]])
    lum = np.clip(lum, 0, 1) ** float(os.environ.get('ALB_GAMMA', 1.0)) * float(os.environ.get('ALB_CON', 1.0))
    gm = np.stack([np.interp(lum, stops, cols[:, k]) for k in range(3)], -1)
    w = GRADE * (1 - purple * float(os.environ.get('KEEP_PURPLE', 0.8)))
    a = a * (1 - w[..., None]) + gm * w[..., None]
    a = np.clip(a * float(os.environ.get('ALB_GAIN', 1.0)), 0, 1)
Image.fromarray((a * 255).astype(np.uint8)).save(T + 'v10_albedo.jpg', quality=92)
# funnel emission: violet streaks from the albedo luminance (only the BH_Glow_Rim material samples it)
_l = np.clip((a @ np.array([0.299, 0.587, 0.114])) * 2.4, 0, 1) ** 2.2
_e = np.clip(_l[..., None] * np.array([0.62, 0.16, 1.0]) * float(os.environ.get('EMIT_GAIN', 1.0)), 0, 1)
Image.fromarray((_e * 255).astype(np.uint8)).save(T + 'v10_glow_emit.jpg', quality=92)
mr = np.asarray(MR).astype(np.float32) / 255   # glTF MR: G roughness, B metal -> more matte, less chrome (no wet-plastic sheen)
mr[..., 1] = np.clip(float(os.environ.get('ROUGH_OFF', 0.3)) + mr[..., 1] * (1 - float(os.environ.get('ROUGH_OFF', 0.3))), 0, 1)
mr[..., 2] = mr[..., 2] * float(os.environ.get('METAL_K', 0.75)); mr[..., 0] = 1.0
Image.fromarray((mr * 255).astype(np.uint8)).save(T + 'v10_mr.jpg', quality=92)
# UV coverage mask -> normalized-convolution high-pass of luminance
pos = j['meshes'][0]['primitives'][0]
def acc(i):
    a_ = j['accessors'][i]; bv = j['bufferViews'][a_['bufferView']]; n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[a_['type']]
    dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[a_['componentType']]; o = b0 + bv.get('byteOffset', 0) + a_.get('byteOffset', 0)
    x = np.frombuffer(d, dt, a_['count'] * n, o); return x.reshape(-1, n) if n > 1 else x
uv = acc(pos['attributes']['TEXCOORD_0']); idx = acc(pos['indices']).reshape(-1, 3); W = A.width
M = Image.new('L', (W, W), 0); dr = ImageDraw.Draw(M)
for t in uv[idx] * W: dr.polygon([tuple(p) for p in t], fill=255)
M = M.filter(ImageFilter.MaxFilter(5)); m = np.asarray(M).astype(np.float32) / 255
lum = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).convert('L')).astype(np.float32) / 255
from scipy.ndimage import gaussian_filter
def blur(x, r): return gaussian_filter(x.astype(np.float32), r)
bl = blur(lum * m, 18) / np.maximum(blur(m, 18), 1e-3)
fine = blur(lum * m, 1.2) / np.maximum(blur(m, 1.2), 1e-3)
hp = np.clip((fine - bl) * float(os.environ.get('HP_GAIN', 2.2)), -0.5, 0.5) * m
Image.fromarray(((hp + 0.5) * 255).astype(np.uint8)).save(T + 'v10_height.png')
print('tex ok', A.size, 'coverage', m.mean().round(3))
