# v13 stage F (= v12 + v11 funnel ripple relief) (system python): thinner, crisper strap/lace plates (flat plate + sharp raised free edge + clear gaps + slot pits)
#   and a funnel of fine inward-spiralling concentric streaks (integer spiral turns -> no seam), mostly dark
#  seeds ~ every S metres on the skin; each seed = one scale (ellipse, long axis along the local flow:
#  tube axis by PCA on tentacles/curls, inward spiral toward the hole elsewhere); per vertex the highest
#  covering scale wins -> overlapping shingles with a raised free edge; 30 % of scales are open cells (pits).
#  Outputs per-vertex displacement + masks (rim=copper edge, cavity=plum, height) for the bake.
import numpy as np, os, json, time
from scipy.spatial import cKDTree
import scipy.sparse as sp
C = os.environ.get('V11_CACHE', '/tmp/v11'); t0 = time.time()
E = lambda k, d: float(os.environ.get(k, d))
S1 = E('S1', 2.4); S2 = E('S2', 1.1); AMP = E('AMP', 0.55); LOWAMP = E('LOWAMP', 0.22); HC = np.array([0.0, 58.0])
rng = np.random.default_rng(11)
def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def adj(f, n):
    i = np.r_[f[:, 0], f[:, 1], f[:, 2], f[:, 1], f[:, 2], f[:, 0]]; j = np.r_[f[:, 1], f[:, 2], f[:, 0], f[:, 0], f[:, 1], f[:, 2]]
    A = sp.csr_matrix((np.ones(len(i), np.float32), (i, j)), shape=(n, n)); A.data[:] = 1
    d = np.asarray(A.sum(1)).ravel(); return sp.diags(1 / np.maximum(d, 1)) @ A
def smooth(L, x, it):
    for _ in range(it): x = L @ x
    return x
def spiral(p):
    dx = p[:, 0] - HC[0]; dz = p[:, 2] - HC[1]; r = np.maximum(np.hypot(dx, dz), 1e-3)
    rv = np.stack([dx / r, np.zeros_like(r), dz / r], 1); tv = np.stack([-dz / r, np.zeros_like(r), dx / r], 1)
    b = E('SPIRAL', 0.55); return np.cos(b) * tv - np.sin(b) * rv
def make_seeds(co, nrm, ok, S, sub):
    idx = np.where(ok)[0]; idx = idx[rng.permutation(len(idx))]
    key = np.floor((co[idx] + rng.uniform(0, S, 3)) / S).astype(np.int64)
    _, first = np.unique(key[:, 0] * 73856093 ^ key[:, 1] * 19349663 ^ key[:, 2] * 83492791, return_index=True)
    sd = idx[first]; P = co[sd]
    # flow direction per seed: PCA axis on tube-like parts, spiral elsewhere (sign kept consistent with the spiral)
    CS = co[sub]; T = spiral(P); tree = cKDTree(CS); nb = tree.query_ball_point(P, 1.7 * S, workers=-1); ntube = 0
    for k, ids in enumerate(nb):
        if len(ids) < 12: continue
        Q = CS[ids] - P[k]; w, v = np.linalg.eigh(Q.T @ Q / len(ids))
        if w[2] > E('TUBE', 3.2) * w[1]:
            ax = v[:, 2] * np.sign(v[:, 2] @ T[k] + 1e-9); T[k] = ax; ntube += 1
    T = T - (T * nrm[sd]).sum(1)[:, None] * nrm[sd]; T /= np.maximum(np.linalg.norm(T, axis=1), 1e-6)[:, None]
    m = len(sd); print('seeds', m, 'tube-aligned', ntube, flush=True)
    return dict(p=P, t=T, a=S * E('SA', 0.95) * rng.uniform(0.8, 1.25, m), b=S * E('SB', 0.36) * rng.uniform(0.8, 1.2, m),
                pit=rng.random(m) < E('PITS', 0.3), amp=rng.uniform(0.75, 1.15, m))
def field(co, nrm, SD, S, k=8, chunk=150000):
    tree = cKDTree(SD['p']); N = len(co)
    H = np.zeros(N, np.float32); RIM = np.zeros(N, np.float32); CAV = np.zeros(N, np.float32)
    for s0 in range(0, N, chunk):
        p = co[s0:s0 + chunk]; n = nrm[s0:s0 + chunk]
        _, nb = tree.query(p, k, workers=-1)
        d = p[:, None, :] - SD['p'][nb]; t = SD['t'][nb]
        t = t - (t * n[:, None, :]).sum(2, keepdims=True) * n[:, None, :]; t /= np.maximum(np.linalg.norm(t, axis=2, keepdims=True), 1e-6)
        b = np.cross(n[:, None, :], t)
        u = (d * t).sum(2); v = (d * b).sum(2); w = (d * n[:, None, :]).sum(2)
        a = SD['a'][nb]; bb = SD['b'][nb]
        q = ((u - 0.28 * a) / a) ** 2 + (v / bb) ** 2
        lift = 0.55 + 0.25 * np.clip(u / a + 0.3, 0, 1.0) + 0.45 * sstep(0.72, 0.93, q) * sstep(0.0, 0.5, u / a)   # thin flat plate, sharp raised lip on the free edge
        h = np.where((q < 1) & (np.abs(w) < 0.45 * S), (1 - np.minimum(q, 1)) ** E('EDGE', 0.05) * lift * SD['amp'][nb], -1.0)
        wi = h.argmax(1); r_ = np.arange(len(p)); hw = h[r_, wi]; qw = q[r_, wi]; uw = u[r_, wi] / a[r_, wi]
        cover = hw > 0
        # open cells: a pit inside the scale (dark socket ringed with copper, like the reference)
        pit = SD['pit'][nb[r_, wi]] & cover; qp = (((u[r_, wi] - 0.1 * a[r_, wi]) / (0.55 * a[r_, wi])) ** 2 + (v[r_, wi] / (0.28 * bb[r_, wi])) ** 2)   # slot pit (lace)
        dep = np.where(pit & (qp < 1), np.clip(1 - qp, 0, 1) ** 0.25, 0.0)
        hh = np.where(cover, hw, 0.0) - 1.25 * dep
        # second-highest covering scale: a big step between them = exposed free edge
        h2 = np.sort(h, 1)[:, -2]; step = np.clip(hw - np.maximum(h2, 0), 0, 1)
        rim = np.clip(sstep(0.86, 0.99, qw) * sstep(0.2, 0.7, uw) * np.where(cover, 1, 0) + 0.7 * np.where(pit, sstep(0.7, 1.0, qp) * (1 - sstep(1.0, 1.35, qp)), 0), 0, 1)
        rim = np.clip(rim * (0.35 + 1.2 * step), 0, 1)
        cav = np.clip(np.where(cover, 0, 1) + dep * 1.2 + (1 - sstep(0.0, 0.25, hh)) * 0.5, 0, 1)
        H[s0:s0 + chunk] = hh; RIM[s0:s0 + chunk] = rim; CAV[s0:s0 + chunk] = cav
    return H, RIM, CAV

D = np.load(C + '/dense.npz'); co = D['co'].astype(np.float64); nrm = D['n'].astype(np.float64); f = D['f']; fm = D['fm']; N = len(co)
L = adj(f, N)
vm = np.zeros(N, np.int32); np.maximum.at(vm, f.ravel(), np.repeat(fm, 3))
skin = (vm == 0).astype(np.float32); skin_w = smooth(L, skin, 25); skin_w = np.clip((skin_w - 0.5) * 2.2, 0, 1) * skin   # fade at the funnel lip
funnel = (vm == 1).astype(np.float32)
# base-form convexity (copper on crests of curls / ridges, plum in folds)
lap = (co - L @ co); conv = (lap * nrm).sum(1); conv = smooth(L, conv, 4)
cs = np.percentile(np.abs(conv), 95); convex = np.clip(conv / cs, -1, 1)
sub = np.arange(0, N, 3)
SD1 = make_seeds(co, nrm, skin > 0, S1, sub); SD2 = make_seeds(co, nrm, skin > 0, S2, sub)
print('seeds', len(SD1['p']), len(SD2['p']), 'tubes', '%.0fs' % (time.time() - t0), flush=True)
H1, R1, C1 = field(co, nrm, SD1, S1); H2, R2, C2 = field(co, nrm, SD2, S2)
print('field done %.0fs' % (time.time() - t0), flush=True)
Hs = H1 + E('OCT2', 0.12) * H2
disp = AMP * (Hs - 0.45) * skin_w
rim = np.clip(np.maximum(R1, 0.45 * R2) * 0.9 + E('CONV_CU', 0.1) * sstep(0.35, 1.0, convex), 0, 1) * skin_w
cav = np.clip(0.75 * C1 + 0.25 * C2 + 0.6 * np.clip(-convex, 0, 1), 0, 1) * skin_w
hgt = np.clip((H1 > 0.3) * (1 - R1) * (1 - C1), 0, 1) * skin_w          # v12: plate tops (grey-blue sheen)
# funnel: concentric violet ring streaks with a slight swirl + broken by angular noise (reference: streaky, dark gaps)
dx = co[:, 0] - HC[0]; dz = co[:, 2] - HC[1]; r = np.hypot(dx, dz); th = np.arctan2(dz, dx)
nz = sum(np.sin(k * th + rng.uniform(0, 6.3)) / k ** 0.8 for k in range(3, 23, 2))
# v12: the fine streaks (~0.5 m) are finer than the dense vertex spacing -> bake the funnel's polar coords (16-bit) and draw the streaks per texel in compose_v12
radial = np.clip((r - 13.0) / 7.5, 0, 1)
fw = smooth(L, funnel, 3) * (vm != 2)
# v13: restore the v11 ripple relief in the funnel (dense mesh -> baked normal), integer swirl = spiral, no seam
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from ripple_v13 import ripple
rip = ripple(r, th); disp = disp + E('RIP_AMP', 0.2) * (rip - 0.15) * fw * (1 - skin_w)
# low mesh: gentle real displacement (silhouette), smoothed so it stays continuous on the 196k mesh
Lo = np.load(C + '/low.npz'); lco = Lo['co'].astype(np.float64); ln = Lo['n'].astype(np.float64); lf = Lo['f']; lfm = Lo['fm']
lvm = np.zeros(len(lco), np.int32); np.maximum.at(lvm, lf.ravel(), np.repeat(lfm, 3))
LL = adj(lf, len(lco)); lsk = smooth(LL, (lvm == 0).astype(np.float32), 12); lsk = np.clip((lsk - 0.5) * 2.2, 0, 1) * (lvm == 0)
lH, _, _ = field(lco, ln, SD1, S1); ldisp = smooth(LL, LOWAMP * (lH - 0.45) * lsk, 2)
np.savez(C + '/field.npz', disp=disp.astype(np.float32), col1=np.stack([rim, cav, hgt], 1).astype(np.float32),
         col2=np.stack([np.clip(r / 40.0, 0, 1) * fw, (0.5 + 0.5 * np.cos(th)) * fw, (0.5 + 0.5 * np.sin(th)) * fw], 1).astype(np.float32), ldisp=ldisp.astype(np.float32))
st = dict(seeds1=len(SD1['p']), seeds2=len(SD2['p']), tube_frac=None, S1=S1, S2=S2, AMP=AMP, LOWAMP=LOWAMP, disp_p=np.percentile(disp, [1, 50, 99]).round(3).tolist(),
          rim_mean=float(rim[skin > 0].mean()), cav_mean=float(cav[skin > 0].mean()), coverage=float((H1 > 0)[skin > 0].mean()), secs=round(time.time() - t0))
json.dump(st, open(C + '/field.json', 'w')); print('FIELD_DONE', st, flush=True)
