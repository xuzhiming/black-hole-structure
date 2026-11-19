# v17 stage G = v16 with ROUNDED detail (anti-origami): sine lamellae instead of sawtooth steps, rounder fibre grooves, no fibres on the
#   tail-fill segments, Gaussian-smoothed SDF for the dense bake mesh (hi.npz) and a much smoother SDF marched at 0.5 m for the low mesh (lo.npz)
# v16 stage G = v15 + deeper fibre grooves / ridged lamellae, svg_a silhouette mask: drop rim curls outside it, fill reference-only gaps
# v15 stage G (system python) = v14 + handedness fix (layout mirrored to match the sheet), heavy tail swoop, fibrous / lamellar tentacles
# v14 stage G (system python): procedural signed-distance model of the new reference sheet -> marching cubes high mesh.
#   dish-shaped shell (concave front, convex back) + front spiral arms twisting into the funnel + thin secondary arms
#   + rear spiral vortex arms + long tail tentacle + many rim curls (volutes, tips Ø0.75 m) + porous pits
#   + funnel carve (lip Ø40 at entrance plane, Ø26 core mouth 18 m deeper along +Y) + low-amplitude bump noise.
# Blender coords: X right, Y depth (front = -Y), Z up; metres. Output: $V14_CACHE/hi.npz (+ geom.json)
import numpy as np, os, json, time
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
E = lambda k, d: float(os.environ.get(k, d))
C = os.environ.get('V14_CACHE', '/tmp/v17'); os.makedirs(C, exist_ok=True)
h = E('VOX', 0.25); T0 = time.time()
rng = np.random.default_rng(int(E('SEED', 14)))
HX, HZ = 0.0, 58.0                     # hole axis
Y_E = E('Y_E', -9.0); Y_M = Y_E + E('REC', 18.0)  # v15: REC 17.2 so the measured lip crest (rounded lip bulges ~0.6 m ahead of Y_E, +0.9% fit_box Y scale) lands at 18.0;  entrance (lip) plane, core mouth plane
DC = np.array([0.0, 61.0])             # dish centre (XZ)
def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
# the dish bends mainly about the X axis (side views: crescent whose top and bottom reach forward, mid-height recessed)
AXF, AXB = E('AXF', 0.35), E('AXB', 0.75)
def rdf(x, z): return np.sqrt((AXF * (x - HX)) ** 2 + (z - HZ) ** 2)
def rdb(x, z): return np.sqrt((AXB * (x - DC[0])) ** 2 + (z - DC[1]) ** 2)
def yf_xz(x, z): return Y_E - E('DISH_F', 15.0) * sstep(19.0, 46.0, rdf(x, z)) ** 0.9     # front surface of the dish
def yb_xz(x, z): return E('BACK_TOP', 21.4) - E('BACK_DROP', 41.4) * np.clip(rdb(x, z) / 45.0, 0, 1.3) ** E('BACK_P', 1.7)               # back surface
# ---------------- curves ----------------
tubes = []   # dict(P (n,3), r (n,), k smooth, kind, out (n,3) preferred pore direction)
def resample(P, r, ds_fn):
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]; out = [0.0]
    while out[-1] < s[-1]:
        rr = np.interp(out[-1], s, r); out.append(out[-1] + ds_fn(rr))
    out = np.clip(np.array(out), 0, s[-1]); Pn = np.stack([np.interp(out, s, P[:, i]) for i in range(3)], 1); return Pn, np.interp(out, s, r)
def volute(p, u, nrm, R0, Rend, r0, rt, turns, sgn, ds=0.08, drift=0.0):
    """planar-ish tightening spiral: heading u rotates about nrm; curvature radius R0 -> Rend, tube radius r0 -> rt"""
    nrm = nrm / np.linalg.norm(nrm); u = u - nrm * (u @ nrm); u /= np.linalg.norm(u); Phi = turns * 2 * np.pi
    P = [p.copy()]; Rr = [r0]; psi = 0.0; q = p.copy()
    while psi < Phi:
        f = psi / Phi; R = R0 * (Rend / R0) ** f; dpsi = ds / R
        a = sgn * dpsi; c, s = np.cos(a), np.sin(a); w = np.cross(nrm, u)
        u = u * c + w * s; q = q + u * ds + nrm * drift * ds; psi += dpsi
        P.append(q.copy()); Rr.append(r0 * (rt / r0) ** f)
    return np.array(P), np.array(Rr)
def add(P, r, k=0.8, kind='arm', out=None):
    P, r = resample(np.asarray(P, float), np.asarray(r, float), lambda rr: float(np.clip(0.45 * rr, 0.12, 1.4)))
    tubes.append(dict(P=P, r=r, k=k, kind=kind, out=out))
def xz_dir(t): return np.array([np.cos(t), 0.0, np.sin(t)])
FRONT = np.array([0.0, -1.0, 0.0])
def spiral_arm(th0, rho0, rho1, dth, r0, r1, n=200, yoff=0.0, ysurf='f', curl=None):
    t = np.linspace(0, 1, n); rho = rho0 * (rho1 / rho0) ** t; th = th0 + dth * t
    x = DC[0] + rho * np.cos(th); z = DC[1] + rho * np.sin(th) * 1.02
    rr = r0 + (r1 - r0) * t ** 0.8
    if ysurf == 'f':
        rh = np.hypot(x - HX, z - HZ); y = yf_xz(x, z) - E('ARM_PROUD', 0.6) * rr + yoff
        inner = rh < 21; y = np.where(inner, y + (21 - rh) * 1.6, y)       # dive into the funnel
    else:
        y = yb_xz(x, z) + 0.3 * rr + yoff
    P = np.stack([x, y, z], 1); R = rr
    if curl is not None:
        u = P[-1] - P[-2]; u /= np.linalg.norm(u)
        Q, Rq = volute(P[-1], u, curl.get('n', FRONT + rng.normal(0, 0.25, 3)), curl['R0'], curl.get('Rend', 0.9), r1, 0.375, curl['turns'], curl['sgn'], drift=curl.get('drift', 0.0))
        P = np.vstack([P, Q[1:]]); R = np.r_[R, Rq[1:]]
    add(P, R, k=1.2, kind='arm_' + ysurf, out=FRONT if ysurf == 'f' else -FRONT)
# front main arms: outward = counter-clockwise (seen from the front); they start inside the funnel and twist out to the rim
NF = int(E('NF', 10))
for i in range(NF):
    th0 = 2 * np.pi * i / NF + rng.uniform(-0.15, 0.15)
    sgn = rng.choice([-1, 1], p=[0.35, 0.65])
    spiral_arm(th0, 15.5, rng.uniform(41, 45), E('DTH', 1.05) * np.pi * rng.uniform(0.9, 1.1), rng.uniform(4.4, 5.2), rng.uniform(2.6, 3.1),
               curl=dict(R0=rng.uniform(5.0, 7.0), turns=rng.uniform(1.2, 1.6), sgn=sgn))
# thinner secondary arms in the grooves, slightly proud of the main ones
for i in range(NF):
    th0 = 2 * np.pi * (i + 0.5) / NF + rng.uniform(-0.1, 0.1)
    spiral_arm(th0, 19.0, rng.uniform(36, 42), 0.85 * np.pi * rng.uniform(0.85, 1.05), rng.uniform(2.2, 2.7), rng.uniform(1.3, 1.6), yoff=-1.8,
               curl=dict(R0=rng.uniform(3.0, 4.2), turns=rng.uniform(1.3, 1.7), sgn=rng.choice([-1, 1])))
# rear vortex: arms spiral from the rim into the back centre
NB = int(E('NB', 16)); BC = np.array([E('BCX', 6.0), DC[1] + 4])   # (pre-mirror) -> rear vortex centre ends at X = -6 (right of centre in the rear view, as on the sheet)
for i in range(NB):
    th0 = 2 * np.pi * i / NB + rng.uniform(-0.15, 0.15)
    t = np.linspace(0, 1, 260); rho = rng.uniform(40, 44) * (rng.uniform(3.0, 6.0) / 43) ** t; th = th0 - 1.45 * np.pi * t
    x = BC[0] + rho * np.cos(th); z = BC[1] + rho * np.sin(th); r0b = rng.uniform(2.6, 3.4); rr = r0b + (1.0 - r0b) * t
    y = yb_xz(x, z) + rng.uniform(-0.2, 0.6) * rr
    P = np.stack([x, y, z], 1)
    # rim end continues as an outward curl on the back edge
    u = P[0] - P[1]; u /= np.linalg.norm(u)
    Q, Rq = volute(P[0], u, -FRONT + rng.normal(0, 0.3, 3), rng.uniform(4.5, 6.5), 0.9, rr[0] * 0.75, 0.375, rng.uniform(1.1, 1.5), rng.choice([-1, 1]))
    P = np.vstack([Q[::-1], P]); R = np.r_[Rq[::-1], rr]
    add(P, R, k=1.2, kind='arm_b', out=-FRONT)
# back centre coil
Q, Rq = volute(np.array([BC[0] + 6.0, yb_xz(BC[0] + 6.0, BC[1]) + 1.0, BC[1]]), np.array([0, 0, 1.0]), -FRONT, 5.5, 0.6, 2.2, 0.45, 2.3, 1)
add(Q, Rq, k=1.0, kind='arm_b', out=-FRONT)
# tail: from the body's lower-left, sweeping down and along the bottom to the right, ending in an upturned curl
def catmull(P, n=40):
    Pp = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]]); out = []
    for i in range(1, len(Pp) - 2):
        p0, p1, p2, p3 = Pp[i - 1], Pp[i], Pp[i + 1], Pp[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1]); return np.array(out)
# heavy tail (written in pre-mirror coordinates; after the X mirror it leaves the body's lower RIGHT under the hole,
# sweeps along the bottom to the LEFT and rises into a wave-crest volute curling clockwise as seen from the front)
# v15b: centreline traced from the svg_a front silhouette (ref_svg/): root under the hole at X~+18 (post-mirror), lowest at X~-15 Z~3,
# end crest at X~-45 Z~17 rising into a clockwise curl
CP = np.array([[-18, -9, 24], [-10, -12, 14], [2, -14, 6], [15, -15, 3.6], [28, -14, 6], [38, -12, 11], [45, -10, 17.5]], float)
CR = np.array([E('TAIL_R0', 6.0), 6.0, 5.9, 5.6, 5.0, 4.2, 3.2])
TP = catmull(CP); TR = np.interp(np.linspace(0, len(CR) - 1, len(TP)), np.arange(len(CR)), CR)
u = TP[-1] - TP[-2]; u /= np.linalg.norm(u)
Q, Rq = volute(TP[-1], u, FRONT, E('TAIL_CURL', 6.2), 1.0, TR[-1], 0.375, 1.75, 1)
add(np.vstack([TP, Q[1:]]), np.r_[TR, Rq[1:]], k=1.5, kind='tail', out=FRONT)
# two rope strands twisting around the tail (bulk, rope-like look) + a lower lamella
tt = np.linspace(0, 1, len(TP)); tg = np.gradient(TP, axis=0); tg /= np.linalg.norm(tg, axis=1)[:, None]
b1 = np.cross(tg, np.array([0, 1.0, 0])); b1 /= np.linalg.norm(b1, axis=1)[:, None] + 1e-9; b2 = np.cross(tg, b1)
for ph0, fr in ((0.0, 0.5), (np.pi, 0.42)):
    ang = ph0 + 2 * np.pi * 2.0 * tt; off = (TR * 0.92)[:, None] * (np.cos(ang)[:, None] * b1 + np.sin(ang)[:, None] * b2)
    add(TP[:-6] + off[:-6], (TR * fr)[:-6], k=1.0, kind='tail', out=FRONT)
# lower-left hook: a second tentacle that leaves the tail root and curls inward
CP2 = np.array([[-27, -10, 27], [-31, -11, 17], [-27, -10, 9]], float); TP2 = catmull(CP2, 30)
u = TP2[-1] - TP2[-2]; u /= np.linalg.norm(u)
Q, Rq = volute(TP2[-1], u, FRONT, 4.5, 0.9, 2.4, 0.375, 1.5, 1)
add(np.vstack([TP2, Q[1:]]), np.r_[np.linspace(3.4, 2.4, len(TP2)), Rq[1:]], k=1.2, kind='tail', out=FRONT)
# rim curls (卷须): sprout from the dish rim, short stem, tight volute
NCURL = int(E('NCURL', 34))
for i in range(NCURL):
    while True:
        ph = rng.uniform(0, 2 * np.pi)
        if not (-2.35 < ph < -0.75): break                 # leave the bottom (tail) free
    rho0 = rng.uniform(35, 40); base = np.array([DC[0] + rho0 * np.cos(ph), 0, DC[1] + rho0 * np.sin(ph)])
    lay = rng.choice(['f', 'm', 'b'], p=[0.45, 0.3, 0.25])
    rh = np.hypot(base[0] - HX, base[2] - HZ)
    yF, yB = yf_xz(base[0], base[2]), yb_xz(base[0], base[2]); base[1] = {'f': yF - 1.0, 'm': 0.5 * (yF + yB), 'b': yB + 0.8}[lay]
    radial = xz_dir(ph); tang = xz_dir(ph + np.pi / 2)
    u = radial + rng.uniform(0.2, 0.8) * tang + np.array([0, rng.uniform(-0.25, 0.25), 0]); u /= np.linalg.norm(u)
    L = rng.uniform(3, 8); r0 = rng.uniform(1.9, 2.9)
    stem = np.array([base + u * s for s in np.linspace(0, L, 12)])
    nrm = FRONT * (1 if lay != 'b' else -1) + rng.normal(0, 0.3, 3)
    Q, Rq = volute(stem[-1], u, nrm, rng.uniform(3.4, 5.6), 0.8, r0 * 0.85, 0.375, rng.uniform(1.25, 1.8), rng.choice([-1, 1]))
    add(np.vstack([stem, Q[1:]]), np.r_[np.linspace(r0, r0 * 0.85, 12), Rq[1:]], k=0.9, kind='curl', out=nrm / np.linalg.norm(nrm))
# crown curls: a few long stems at the top so the silhouette reaches Z ~ 118 by itself (no boxy stretch)
for ph, L, sg in ((1.89, 15.0, 1), (1.40, 7.0, -1), (2.35, 7.0, 1)):   # post-mirror: tall crown curl at top-right (svg_a)
    base = np.array([DC[0] + 37 * np.cos(ph), 0, DC[1] + 37 * np.sin(ph)]); base[1] = yf_xz(base[0], base[2]) + 2.0
    u = xz_dir(ph) + 0.35 * xz_dir(ph + np.pi / 2 * sg); u /= np.linalg.norm(u)
    stem = np.array([base + u * s_ + np.array([0, 0, 0.012 * s_ * s_]) for s_ in np.linspace(0, L, 16)])
    Q, Rq = volute(stem[-1], stem[-1] - stem[-2], FRONT + rng.normal(0, 0.2, 3), 5.0, 0.8, 2.3, 0.375, 1.5, sg)
    add(np.vstack([stem, Q[1:]]), np.r_[np.linspace(3.0, 2.3, 16), Rq[1:]], k=1.0, kind='curl', out=FRONT)
# v15: the v14 layout was mirrored left-right against the sheet (front arms twisted outward counter-clockwise, tail root on the
# lower-left sweeping right, rear vortex turning the wrong way). Mirror X for every tentacle (keeps hole at X = 0).
for t in tubes:
    t['P'][:, 0] *= -1
    if t['out'] is not None: t['out'] = t['out'] * np.array([-1, 1, 1])
# fit the tentacle layout to the spec box (X +-50, Z 0..120, front Y -24) before building the field: warp only away from the
# hole (r > 24 m) so the funnel spec is untouched; radii unchanged (tips stay 0.75 m)
TGT = dict(x=(-49.6, 49.6), z=(0.4, 119.6), yf=-23.6)
for it in range(3):
    allP = np.vstack([t['P'] for t in tubes]); allR = np.concatenate([t['r'] for t in tubes])
    lo_, hi_ = (allP - allR[:, None]).min(0), (allP + allR[:, None]).max(0)
    for t in tubes:
        P = t['P']; r = t['r']; w = sstep(24.0, 40.0, np.hypot(P[:, 0] - HX, P[:, 2] - HZ))
        for ax, key in ((0, 'x'), (2, 'z')):
            a0, a1 = lo_[ax] + 0, hi_[ax]; b0, b1 = TGT[key]
            # map the extents of (P -+ r) onto the target: centre-line map keeps radii
            tgt = (b0 + r) + (P[:, ax] - (a0 + r)) * ((b1 - r) - (b0 + r)) / np.maximum((a1 - r) - (a0 + r), 1e-6)
            tgt = b0 + (P[:, ax] - a0) * (b1 - b0) / (a1 - a0)
            if (b1 - b0) > (a1 - a0) * E('MAX_STRETCH', 1.03): tgt = 0.5 * (b0 + b1) + (P[:, ax] - 0.5 * (a0 + a1)) * E('MAX_STRETCH', 1.03)
            P[:, ax] = P[:, ax] + w * (tgt - P[:, ax])
        yl = lo_[1]; m = P[:, 1] < 0
        P[m, 1] = P[m, 1] + w[m] * (P[m, 1] * (TGT['yf'] / yl) - P[m, 1])

# ---------------- v16: svg_a front silhouette (ref_svg/svg_a.png alpha, 1 m / px, spans X -50..50, Z 0..120) ----------------
from PIL import Image
_a = np.asarray(Image.open(os.path.dirname(os.path.abspath(__file__)) + '/../ref_svg/svg_a.png'))[..., 3] > 128
_ys, _xs = np.nonzero(_a); _a = _a[_ys.min():_ys.max() + 1, _xs.min():_xs.max() + 1]
MASK = ndi.binary_fill_holes(np.asarray(Image.fromarray(_a).resize((200, 240), Image.NEAREST)) > 0)[::-1].T   # [ix, iz], 0.5 m / px
def inmask(x, z, dil=0):
    M = ndi.binary_dilation(MASK, iterations=dil) if dil else MASK
    i = np.clip(((np.asarray(x) + 50) * 2).astype(int), 0, 199); j = np.clip((np.asarray(z) * 2).astype(int), 0, 239); return M[i, j]
def model_sil():
    S = np.zeros((200, 240), bool); gx, gz = np.meshgrid((np.arange(200) + 0.5) / 2 - 50, (np.arange(240) + 0.5) / 2, indexing='ij')
    ph = np.arctan2(gz - DC[1], gx - DC[0]); S |= np.hypot(gx - DC[0], gz - DC[1]) < 38.0 + 1.5 * np.sin(3 * ph + 1.0) + 1.0 * np.sin(5 * ph + 2.0)
    for t in tubes:
        for p, r in zip(t['P'][::2], t['r'][::2]):
            i0, i1 = int(max((p[0] - r + 50) * 2, 0)), int(min((p[0] + r + 50) * 2 + 2, 200)); j0, j1 = int(max((p[2] - r) * 2, 0)), int(min((p[2] + r) * 2 + 2, 240))
            if i1 > i0 and j1 > j0: S[i0:i1, j0:j1] |= np.hypot(gx[i0:i1, j0:j1] - p[0], gz[i0:i1, j0:j1] - p[2]) < r
    return S
def iou(S): return float((S & MASK).sum() / (S | MASK).sum())
S0 = model_sil(); print('sil IoU (raster) before', round(iou(S0), 3), flush=True)
# 1) drop curls / crown curls that stick out of the reference silhouette
MD = ndi.binary_dilation(MASK, iterations=int(E('CURL_DIL', 3)))
keep = []
for t in tubes:
    if t['kind'] == 'curl':
        P = t['P']; i = np.clip(((P[:, 0] + 50) * 2).astype(int), 0, 199); j = np.clip((P[:, 2] * 2).astype(int), 0, 239)
        if (~MD[i, j]).mean() > E('CURL_OUT', 0.12): continue
    keep.append(t)
print('curls dropped', len(tubes) - len(keep), flush=True); tubes[:] = keep
S1 = model_sil(); print('sil IoU after curl filter', round(iou(S1), 3), flush=True)
# 2) fill reference-only gaps with a chain of smooth tentacle segments (spheres from the distance transform joined by an MST)
gap = MASK & ~S1; gap = ndi.binary_opening(gap, iterations=2)
lab_, nl = ndi.label(gap); fill_c = []
for li in range(1, nl + 1):
    g = lab_ == li
    if g.sum() < E('GAP_MIN', 60): continue                         # px (0.25 m2 each)
    dt = ndi.distance_transform_edt(g) / 2.0; cov = np.zeros_like(g)
    while True:
        dd = np.where(g & ~cov, dt, 0)
        if dd.max() < 0.9: break
        i, j = np.unravel_index(np.argmax(dd), dd.shape); r = min(float(dt[i, j]) + 0.6, E('FILL_RMAX', 3.8))
        x, z = (i + 0.5) / 2 - 50, (j + 0.5) / 2; rc = min(r, 49.6 - abs(x), z - 0.4, 119.6 - z)
        if rc > 0.8: fill_c.append((x, z, rc))
        gx, gz = np.ogrid[:200, :240]; cov |= np.hypot(gx - i, gz - j) < max(r * 2 * 0.85, 1.5)
allTP = np.vstack([t['P'] for t in tubes]); kdT = cKDTree(allTP[:, [0, 2]])
if fill_c:
    F = np.array(fill_c); ys_ = []
    for x, z, r in F:
        idn = kdT.query_ball_point([x, z], 8.0); ys_.append(np.median(allTP[idn, 1]) if idn else float(yf_xz(x, z)))
    Pf = np.c_[F[:, 0], np.clip(ys_, -23.6 + F[:, 2], 23.5 - F[:, 2]), F[:, 1]]
    from scipy.sparse.csgraph import minimum_spanning_tree
    from scipy.spatial.distance import cdist
    deg = np.zeros(len(Pf), int); Dm = cdist(Pf, Pf); mst = minimum_spanning_tree(Dm).tocoo()
    for a_, b_, dist in zip(mst.row, mst.col, mst.data):
        if dist > F[a_, 2] + F[b_, 2] + 6: continue
        add(np.array([Pf[a_], Pf[b_]]), np.array([F[a_, 2], F[b_, 2]]), k=E('FILL_K', 3.0), kind='fill', out=FRONT); deg[a_] += 1; deg[b_] += 1
    for q in np.where(deg == 0)[0]: add(np.array([Pf[q], Pf[q] + [0.01, 0, 0]]), np.array([F[q, 2]] * 2), k=E('FILL_K', 3.0), kind='fill', out=FRONT)
print('fill blobs', len(fill_c), 'in hole', sum(np.hypot(x, z - 58) < 24 for x, z, r in fill_c), 'area', int(sum(np.pi * r * r for x, z, r in fill_c)), flush=True)
print('fills', [(round(x), round(z), round(r, 1)) for x, z, r in fill_c][:80], flush=True)
S2 = model_sil(); print('sil IoU after fill', round(iou(S2), 3), flush=True)
allP = np.vstack([t['P'] for t in tubes]); allR = np.concatenate([t['r'] for t in tubes])
print('fitted extent', (allP - allR[:, None]).min(0).round(2), (allP + allR[:, None]).max(0).round(2), flush=True)
print('tubes', len(tubes), 'pts', sum(len(t['P']) for t in tubes), round(time.time() - T0, 1), flush=True)
# ---------------- grid ----------------
allP = np.vstack([t['P'] for t in tubes]); allR = np.concatenate([t['r'] for t in tubes])
lo = np.minimum((allP - allR[:, None]).min(0), [-46, -26, 14]) - 2.0; hi = np.maximum((allP + allR[:, None]).max(0), [46, 26, 108]) + 2.0
shape = np.ceil((hi - lo) / h).astype(int) + 1
print('raw extent', (allP - allR[:, None]).min(0).round(1), (allP + allR[:, None]).max(0).round(1), 'grid', shape, shape.prod() / 1e6, 'M', flush=True)
BIG = 6.0
D = np.full(shape, BIG, np.float32)
xs = lo[0] + h * np.arange(shape[0]); ys = lo[1] + h * np.arange(shape[1]); zs = lo[2] + h * np.arange(shape[2])
def smin(a, b, k):
    hh = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1); return b * (1 - hh) + a * hh - k * hh * (1 - hh)
# dish shell (chunked over z)
for k0 in range(0, shape[2], 64):
    Z = zs[k0:k0 + 64]; X, Y, Zg = np.meshgrid(xs, ys, Z, indexing='ij')
    rh = np.hypot(X - HX, Zg - HZ); rd = np.hypot(X - DC[0], Zg - DC[1])
    ph = np.arctan2(Zg - DC[1], X - DC[0]); Rout = 38.0 + 1.5 * np.sin(3 * ph + 1.0) + 1.0 * np.sin(5 * ph + 2.0)
    g = 1.0 / np.sqrt(1 + (E('DISH_F', 14.0) / 26.0) ** 2)
    d = np.maximum(np.maximum((yf_xz(X, Zg) + E('SHELL_BACK', 2.0) - Y) * g, (Y - yb_xz(X, Zg)) * 0.8), rd - Rout)
    D[:, :, k0:k0 + 64] = np.minimum(D[:, :, k0:k0 + 64], np.clip(d, -BIG, BIG))
print('shell', round(time.time() - T0, 1), flush=True)
def idx_box(a, b):
    i0 = np.maximum(np.floor((a - lo) / h).astype(int), 0); i1 = np.minimum(np.ceil((b - lo) / h).astype(int) + 1, shape); return i0, i1
FS, GD, LD, TW = E('FIB_SP', 1.5), E('FIB_D', 0.18), E('LAM_D', 0.08), E('FIB_TW', 0.05)
def frames(P):
    T_ = np.gradient(P, axis=0); T_ /= np.linalg.norm(T_, axis=1)[:, None] + 1e-9
    e1 = np.zeros_like(P); a0 = np.cross(T_[0], [0.3, 0.5, 0.8]); e1[0] = a0 / np.linalg.norm(a0)
    for i in range(1, len(P)):                         # parallel transport
        v_ = e1[i - 1] - T_[i] * (e1[i - 1] @ T_[i]); e1[i] = v_ / (np.linalg.norm(v_) + 1e-9)
    return e1, np.cross(T_, e1)
for t in tubes:
    P, r, k = t['P'], t['r'], t['k']; pad = k + 1.0
    e1s, e2s = frames(P); sl_ = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    NFb = max(5, int(round(2 * np.pi * r.max() / FS))); lam = float(np.clip(1.1 * np.median(r), 1.6, 4.0))
    t0 = (P - r[:, None]).min(0) - pad; t1 = (P + r[:, None]).max(0) + pad; I0, I1 = idx_box(t0, t1)
    loc = np.full(tuple(I1 - I0), BIG, np.float32)
    for s in range(len(P) - 1):
        a, b, ra, rb = P[s], P[s + 1], r[s], r[s + 1]; m = max(ra, rb) + pad
        j0, j1 = idx_box(np.minimum(a, b) - m, np.maximum(a, b) + m); j0 = np.maximum(j0, I0); j1 = np.minimum(j1, I1)
        X = xs[j0[0]:j1[0], None, None]; Y = ys[None, j0[1]:j1[1], None]; Z = zs[None, None, j0[2]:j1[2]]
        ba = b - a; L2 = max(ba @ ba, 1e-9)
        tt = np.clip(((X - a[0]) * ba[0] + (Y - a[1]) * ba[1] + (Z - a[2]) * ba[2]) / L2, 0, 1)
        qx, qy, qz = X - a[0] - tt * ba[0], Y - a[1] - tt * ba[1], Z - a[2] - tt * ba[2]; rr_ = ra + tt * (rb - ra)
        ql = np.sqrt(qx * qx + qy * qy + qz * qz); e1, e2 = e1s[s], e2s[s]; sa = sl_[s] + tt * np.sqrt(L2)
        if max(ra, rb) > 0.7:
            fi = np.arctan2(qx * e2[0] + qy * e2[1] + qz * e2[2], qx * e1[0] + qy * e1[1] + qz * e1[2]) + TW * sa
            groove = (0.5 + 0.5 * np.cos(NFb * fi)) ** E('FIB_P', 1.5)                                      # narrow parallel fibre grooves
            band = 0.5 - 0.5 * np.cos(2 * np.pi * (sa / lam + 0.18 * np.sin(3 * fi)))   # v17: smooth sine lamellae (v16 sawtooth % 1 = hard steps)                                      # stacked, scalloped lamellae
            fade = np.clip((rr_ - 0.7) / 1.0, 0, 1)
            if t['kind'] == 'fill': fade = fade * sstep(0.0, 0.3, tt) * sstep(1.0, 0.7, tt) * 0.7   # v17: no fibre pinch on the exposed end caps of short fill segments
            rr_ = rr_ * (1 - fade * (GD * groove - LD * band))
        d = ql - rr_
        sl = tuple(slice(j0[q] - I0[q], j1[q] - I0[q]) for q in range(3)); loc[sl] = np.minimum(loc[sl], d)
    gs = tuple(slice(I0[q], I1[q]) for q in range(3)); D[gs] = smin(D[gs], loc, k)
print('tubes done', round(time.time() - T0, 1), flush=True)
# ---------------- pores ----------------
pores = []
for t in tubes:
    P, r = t['P'], t['r']; s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]; pos = 0.0
    while True:
        pos += rng.uniform(1.1, 2.2) * max(0.8, np.interp(pos, s, r) * 0.55)
        if pos >= s[-1]: break
        i = min(np.searchsorted(s, pos), len(P) - 2); rr = r[i]
        if rr < 1.1: continue
        tg = P[i + 1] - P[i]; tg /= np.linalg.norm(tg) + 1e-9
        o = t['out'] if t['out'] is not None else FRONT
        for _ in range(rng.integers(1, 3)):
            dvec = o + rng.normal(0, 0.75, 3); dvec -= tg * (dvec @ tg); dvec /= np.linalg.norm(dvec) + 1e-9
            rp = rr * rng.uniform(0.2, 0.42); c = P[i] + dvec * (rr + rp * 0.1)
            if np.hypot(c[0] - HX, c[2] - HZ) < 23.5 and c[1] > Y_E - 6: continue
            pores.append((c, rp))
print('pores', len(pores), flush=True)
KP = E('PORE_K', 0.35)
for c, rp in pores:
    I0, I1 = idx_box(c - rp - KP - 0.5, c + rp + KP + 0.5)
    X = xs[I0[0]:I1[0], None, None]; Y = ys[None, I0[1]:I1[1], None]; Z = zs[None, None, I0[2]:I1[2]]
    ds = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2) - rp
    gs = tuple(slice(I0[q], I1[q]) for q in range(3)); D[gs] = -smin(-D[gs], ds, KP)
print('pores carved', round(time.time() - T0, 1), flush=True)
# ---------------- bump noise (skin only) ----------------
def noise(sp, amp, seed):
    g = np.random.default_rng(seed).normal(0, 1, tuple(np.ceil(shape * h / sp).astype(int) + 3)).astype(np.float32)
    z = ndi.zoom(g, [shape[q] / (g.shape[q] - 3) for q in range(3)], order=3, prefilter=False)[:shape[0], :shape[1], :shape[2]]
    return amp * z / max(np.std(z), 1e-6)
D += noise(2.2, E('N1', 0.16), 1) + noise(0.9, E('N2', 0.05), 2)     # v16: less noise so the fibre grooves read
print('noise', round(time.time() - T0, 1), flush=True)
# ---------------- funnel carve ----------------
for k0 in range(0, shape[2], 64):
    Z = zs[k0:k0 + 64]; X, Y, Zg = np.meshgrid(xs, ys, Z, indexing='ij'); rh = np.hypot(X - HX, Zg - HZ)
    rf = np.where(Y >= Y_E, 13.0 + 7.0 * np.clip((Y_M - Y) / 18.0, 0, 1) ** E('FUN_P', 0.8), 20.0 + E('FLARE', 0.35) * (Y_E - Y))
    dc = np.maximum((rh - rf) * 0.85, Y - Y_M)            # inside funnel < 0
    sl = D[:, :, k0:k0 + 64]
    lip = sstep(Y_E - 4, Y_E + 1, Y)                        # smooth rounding only near the lip, crisp at the Ø26 core mouth
    kk = E('LIP_K', 0.8) * (1 - lip) + 0.05
    D[:, :, k0:k0 + 64] = -smin(-sl, dc, kk)
print('funnel', round(time.time() - T0, 1), flush=True)
# ---------------- mesh ----------------
D[0], D[-1], D[:, 0], D[:, -1], D[:, :, 0], D[:, :, -1] = BIG, BIG, BIG, BIG, BIG, BIG
# v17: low mesh source = strongly smoothed SDF (sigma LO_SIG away from the funnel, HI_SIG near it) marched at 2 h -> even, smooth triangles
def keep_main(v, f):
    import scipy.sparse as sp
    nV = len(v); A = sp.coo_matrix((np.ones(len(f) * 3), (np.repeat(f[:, 0], 3), f.ravel())), shape=(nV, nV))
    ncomp, lab = sp.csgraph.connected_components(A, directed=False); cnt = np.bincount(lab); kv = lab == np.argmax(cnt); fk = kv[f].all(1)
    remap = -np.ones(nV, np.int64); remap[kv] = np.arange(kv.sum()); return v[kv], remap[f[fk]], kv
Ds = ndi.gaussian_filter(D, E('LO_SIG', 0.5) / h); Dh = ndi.gaussian_filter(D, E('HI_SIG', 0.2) / h)
for k0 in range(0, shape[2], 64):
    Zc = zs[k0:k0 + 64]; X, Zg = np.meshgrid(xs, Zc, indexing='ij'); wfun = sstep(21.0, 25.0, np.hypot(X - HX, Zg - HZ))[:, None, :]
    Ds[:, :, k0:k0 + 64] = wfun * Ds[:, :, k0:k0 + 64] + (1 - wfun) * Dh[:, :, k0:k0 + 64]
st = int(E('LO_STRIDE', 1)); Dl = Ds[::st, ::st, ::st].copy(); del Ds
Dl[0], Dl[-1], Dl[:, 0], Dl[:, -1], Dl[:, :, 0], Dl[:, :, -1] = BIG, BIG, BIG, BIG, BIG, BIG
lv_, lf_, _, _ = marching_cubes(Dl, 0.0, spacing=(h * st,) * 3, allow_degenerate=False); lv_ = lv_ + lo; lf_ = lf_[:, ::-1].copy()
lv_, lf_, _ = keep_main(lv_, lf_); np.savez(C + '/lo.npz', v=lv_.astype(np.float32), f=lf_.astype(np.int32)); print('lo mesh', len(lv_), len(lf_), flush=True); del Dl
D = Dh; D[0], D[-1], D[:, 0], D[:, -1], D[:, :, 0], D[:, :, -1] = BIG, BIG, BIG, BIG, BIG, BIG
v, f, nrm, _ = marching_cubes(D, 0.0, spacing=(h, h, h), allow_degenerate=False)
v = v + lo; f = f[:, ::-1].copy()          # outward winding
# keep the main connected component(s): drop floaters
import scipy.sparse as sp
nV = len(v); A = sp.coo_matrix((np.ones(len(f) * 3), (np.repeat(f[:, 0], 3), f.ravel())), shape=(nV, nV))
ncomp, lab = sp.csgraph.connected_components(A, directed=False); cnt = np.bincount(lab)
keepc = np.where(cnt > 0.05 * cnt.max())[0]; kv = np.isin(lab, keepc); fk = kv[f].all(1)   # main body only: drop arm fragments cut loose by the funnel carve
remap = -np.ones(nV, np.int64); remap[kv] = np.arange(kv.sum()); f = remap[f[fk]]; v = v[kv]; nrm = -nrm[kv]
print('mesh', len(v), len(f), 'components', ncomp, 'kept', len(keepc), round(time.time() - T0, 1), flush=True)
# ---------------- per-vertex attributes ----------------
Dc = np.clip(D, -3, 3)
def samp(G, p): return ndi.map_coordinates(G, ((p - lo) / h).T, order=1, mode='nearest').astype(np.float32)
conv1 = samp(ndi.gaussian_filter(Dc, E('CONV1_S', 0.6) / h), v); conv3 = samp(ndi.gaussian_filter(Dc, 3.0 / h), v)
PC = np.array([c for c, _ in pores]); PR = np.array([rp for _, rp in pores]); kd = cKDTree(PC); dd, ii = kd.query(v, k=1)
pit = np.clip(1.0 - (dd - PR[ii]) / (0.35 * PR[ii]), 0, 1).astype(np.float32)       # 1 inside the pit wall, 0 outside the rim
np.savez(C + '/hi.npz', v=v.astype(np.float32), f=f.astype(np.int32), n=nrm.astype(np.float32), conv1=conv1, conv3=conv3, pit=pit)
json.dump(dict(vox=h, Y_E=Y_E, Y_M=Y_M, tubes=len(tubes), pores=len(pores), verts=len(v), tris=len(f), lo=lo.tolist(), shape=shape.tolist(),
               bbox_min=v.min(0).tolist(), bbox_max=v.max(0).tolist(), secs=round(time.time() - T0, 1)), open(C + '/geom.json', 'w'), indent=1)
print('GEOM_DONE', json.load(open(C + '/geom.json')), flush=True)
