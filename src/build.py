# 黑洞构筑体 / Black Hole Structure — v9: 4 big spiral arms + thick tail + layered crown (on top of the v2 procedural build)
# (v2 header follows)
# 黑洞构筑体 / Black Hole Structure — v2 procedural build (bpy 5.3 headless; structure follows scifi_building/src/build.py)
#   v2: dense layered fiddlehead curls with recursive branches, layered back/top tentacle mass, real geometric pores
#   (KD-tree crater displacement with depth + lips + knobs, pore faces get dark / glowing materials), ridged funnel rim.
import math, numpy as np, os, sys, json
from scipy.spatial import cKDTree
from scipy.interpolate import CubicSpline
ROOT = '/workspace/outputs/black_hole_structure'
TEX = ROOT + '/tex'

# ---------------- spec (metres, 1 BU = 1 m) ----------------
BBOX = (100.0, 48.0, 120.0)            # X, Y, Z
HC_Z = 58.0                            # hole centre height
RING_D, CORE_D, RECESS = 40.0, 26.0, 18.0
HALF_Y = 20.5                          # body front half depth (arms/curls add the rest up to 48 m)
BACK_Y = 16.0                          # back pole depth (layered back tentacles sit on top)
A_SCOOP = 13.0                         # crescent scoop: band around the hole height pushed back (side views)
ENV = dict(x=51.0, z0=-1.0, z1=121.0, y0=-27.0, y1=27.0)   # raw envelope used to keep curls inside the box

def srgb2lin(c):
    return tuple(((x/255)/12.92 if x/255 <= 0.04045 else (((x/255)+0.055)/1.055)**2.4) for x in c)

MAT_SKIN, MAT_VEIN, MAT_GLOW, MAT_CORE, MAT_PORE, MAT_PORE_GLOW, MAT_RIM = 0, 1, 2, 3, 4, 5, 6
MAT_NAMES = ['BH_Skin_Bronze', 'BH_Skin_Vein', 'BH_Glow_Rim', 'BH_Core_Black', 'BH_Pore_Dark', 'BH_Pore_Glow', 'BH_Rim_Wear']

class G:
    """mesh accumulator: verts, tris, per-face material, per-vertex uv / normal / local radius / spacing / pit flag"""
    def __init__(self): self.v, self.f, self.fm, self.uv, self.vn, self.vr, self.vs, self.pf, self.vein = [], [], [], [], [], [], [], [], []; self.n = 0
    def add(self, verts, faces, mat, uvs, normals=None, rad=1e3, spacing=1.0, pit=False, vein=False):
        verts = np.asarray(verts, np.float64); faces = np.asarray(faces, np.int64); nv = len(verts)
        self.v.append(verts); self.f.append(faces + self.n)
        self.fm.append(np.broadcast_to(np.asarray(mat, np.int32), (len(faces),)).copy())
        self.uv.append(np.asarray(uvs, np.float64))
        self.vn.append(np.zeros((nv, 3)) if normals is None else np.asarray(normals, np.float64).reshape(nv, 3))
        self.vr.append(np.broadcast_to(np.asarray(rad, np.float64), (nv,)).copy())
        self.vs.append(np.broadcast_to(np.asarray(spacing, np.float64), (nv,)).copy())
        self.pf.append(np.broadcast_to(np.asarray(pit, bool), (nv,)).copy() & (normals is not None))
        self.vein.append(np.full(nv, vein)); self.n += nv
    def arrays(self):
        c = np.concatenate
        return c(self.v), c(self.f), c(self.fm), c(self.uv), c(self.vn), c(self.vr), c(self.vs), c(self.pf), c(self.vein)

rng = np.random.default_rng(20261117)

def vnoise3(p, freq=0.1, seed=0, oct=3):
    out = np.zeros(len(p)); amp = 1.0; tot = 0
    for o in range(oct):
        k = freq * 2**o; ph = np.array([1.7, 9.2, 4.4]) * (seed + o + 1); q = p * k + ph
        out += amp * (np.sin(q[:, 0] + 1.3*np.sin(q[:, 1]*0.7)) * np.sin(q[:, 1] + 1.1*np.sin(q[:, 2]*0.8)) * np.sin(q[:, 2] + 1.2*np.sin(q[:, 0]*0.9)))
        tot += amp; amp *= 0.5
    return out / tot

# ---------------- body shell: revolved profile around the hole axis ----------------
def outline_R(th):
    up = np.clip(np.sin(th), 0, 1); dn = np.clip(-np.sin(th), 0, 1)
    R = 33.0 + 3.5 * up - 2.0 * dn + 1.0 * np.cos(th)
    R += 2.2 * np.sin(5*th + 1.0) + 1.3 * np.sin(9*th + 0.3) + 0.8 * np.sin(14*th + 2.0) + 0.6 * np.sin(23*th + 1.1)
    return R

def profile(R, P):
    rr, rc, rec = P['ring_r'], P['core_r'], P['recess']
    yfront = -HALF_Y + 0.6
    y_m = yfront + max(rec, 1.5)
    y_rim = yfront + 2.0; dd = y_m - y_rim
    pts = [(0.0, y_m + 14.0), (rc * 0.55, y_m + 13.8), (rc - 0.4, y_m + 13.0), (rc, y_m + 10.5), (rc, y_m + 5.0),
           (rc, y_m + 1.5), (rc + 0.2, y_m), (rc + 1.6, y_m - 0.2 * dd), (0.5 * (rc + rr), y_m - 0.55 * dd), (rr - 2.0, y_rim + 0.15 * dd), (rr, y_rim),
           (rr + 2.5, yfront + 0.9), (rr + 6.0, yfront + 0.3), (0.5*(rr + 6.0) + 0.5*R*0.86, yfront),
           (R * 0.90, yfront + 4.0), (R * 0.97, yfront + 11.0), (R, -1.0), (R * 0.985, 5.5), (R * 0.93, 10.5),
           (R * 0.80, BACK_Y - 3.0), (R * 0.60, BACK_Y - 0.8), (R * 0.33, BACK_Y - 0.1), (0.0, BACK_Y)]
    return np.array(pts)

def resample(pts, n):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    s = np.linspace(0, d[-1], n)
    return np.c_[np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])], s / d[-1]

NTH, NT = 560, 380
def build_body(g, P):
    th = np.linspace(0, 2*np.pi, NTH, endpoint=False)
    R = outline_R(th)
    pref = profile(38.0, P); ref, tparam = resample(pref, NT)
    dref = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pref, axis=0), axis=1))]
    rho = np.zeros((NTH, NT)); yv = np.zeros((NTH, NT))
    for i in range(NTH):
        pr = profile(R[i], P)
        d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pr, axis=0), axis=1))]
        s = np.interp(tparam * dref[-1], dref, d)
        rho[i] = np.interp(s, d, pr[:, 0]); yv[i] = np.interp(s, d, pr[:, 1])
    rows = np.arange(NT)[None, :]
    wa = np.clip((P['ring_r'] + 12.0 - rho) / 9.0, 0, 1) * (rows < NT // 3)
    kx = 1.0 + (P.get('ax', 1.0) - 1.0) * wa; kz = 1.0 + (P.get('az', 1.0) - 1.0) * wa
    X = P['hx'] + kx * rho * np.cos(th)[:, None]; Z = P['hz'] + kz * rho * np.sin(th)[:, None]
    zn = (Z - P['hz']) / 40.0
    back = yv > 0
    Y = yv.copy()
    dz = np.maximum(np.abs(Z - P['hz']) - 13.0, 0.0)
    gsc = np.exp(-(dz / 13.0)**2)
    frontness = np.clip(-yv / 12.0, 0, 1)
    hole_rows = (rho < P['ring_r'] + 6.5) & (rows < NT // 3)
    Y = Y + A_SCOOP * gsc * np.where(hole_rows, 1.0, frontness)
    Y[back] *= (1.0 - 0.28 * np.clip(-zn[back], 0, 1)**1.3) * (1.0 + 0.12 * np.clip(zn[back], 0, 1))
    Y += -4.0 * np.clip(-zn, 0, 1)**1.6
    pts = np.stack([X, Y, Z], -1)
    du = np.roll(pts, -1, 0) - np.roll(pts, 1, 0)
    dv = np.zeros_like(pts); dv[:, 1:-1] = pts[:, 2:] - pts[:, :-2]; dv[:, 0] = pts[:, 1] - pts[:, 0]; dv[:, -1] = pts[:, -1] - pts[:, -2]
    nrm = np.cross(dv, du); nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True) + 1e-9
    if nrm[:, -3, 1].mean() < 0: nrm = -nrm
    spacing = np.maximum(np.linalg.norm(du, axis=-1), np.linalg.norm(dv, axis=-1)) * 0.5
    r_safe = np.maximum(rho, 1.0)
    T = np.tile(th[:, None], (1, NT))
    front = yv < 0
    phi_f = T + 6.5 * np.log(r_safe / 21.0)                       # v9: same twist rate as the 4 big arms -> grooves reinforce the vortex
    phi_b = T - 1.10 * np.log(r_safe / 4.0)
    ridge_f = 0.55 * (0.5 + 0.5 * np.cos(8 * phi_f))**1.4 + 0.45 * (0.5 + 0.5 * np.cos(20 * phi_f))**1.6   # v9: broad swirl bands + fine grooves
    ridge_b = (0.5 + 0.5 * np.cos(9 * phi_b))**1.6
    flat = pts.reshape(-1, 3)
    nz = vnoise3(flat, 0.08, 3, 3).reshape(NTH, NT)
    nz2 = vnoise3(flat, 0.35, 7, 2).reshape(NTH, NT)
    lump = vnoise3(flat, 0.045, 11, 3).reshape(NTH, NT)                     # big lumpy masses (back / top)
    hole_zone = rho < P['ring_r'] + 1.5
    amp = np.where(hole_zone & front, 0.35, 1.4)
    amp = amp * np.clip((rho - (P['ring_r'] + 1.0)) / 4.0, 0.15, 1.0)
    ridge = np.where(front, ridge_f, ridge_b)
    disp = amp * (ridge * (0.75 + 0.35 * nz) + 0.45 * nz2) - 1.0
    disp += np.where(back, 3.2, 1.2 * (1 - frontness)) * np.clip(lump, 0, None) * np.clip((rho - P['ring_r'] - 4) / 8, 0, 1)
    # funnel: ridged / organic spiral rim swirling into the core, rough rim lumps at the lip
    phi_h = T + 1.6 * np.log(r_safe / P['core_r'])
    fade = np.clip((rho - P['core_r'] - 0.3) / 3.0, 0, 1)
    rimlump = np.exp(-((rho - P['ring_r']) / 2.4)**2) * (0.6 + 1.2 * nz2) * (0.5 + 0.5 * np.cos(19 * T + 6 * nz + 3 * nz2))**1.5 * 1.3
    fw1 = vnoise3(flat * np.array([1, 1, 1]), 0.11, 31, 3).reshape(NTH, NT)          # low-freq warp / amplitude fields
    fw2 = vnoise3(flat, 0.22, 32, 2).reshape(NTH, NT); fw3 = vnoise3(flat, 0.6, 33, 2).reshape(NTH, NT)
    ph1 = 9 * phi_h + 7.0 * (fw1 - 0.5) + 2.5 * (fw2 - 0.5)                            # warped, non-uniform spacing
    ph2 = 17 * phi_h - 5.0 * (fw2 - 0.5) + 3.0 * (fw3 - 0.5)
    r1 = (1 - np.abs(np.sin(ph1 * 0.5)))**2.2                                         # ridged (sharp crests, soft valleys)
    r2 = (1 - np.abs(np.sin(ph2 * 0.5)))**3
    a1 = np.clip(0.25 + 1.6 * (fw2 - 0.3), 0.1, 1.5); a2 = np.clip(0.2 + 1.4 * (fw1 - 0.35), 0.0, 1.1)
    blob = np.clip(fw3 - 0.55, 0, None) * 2.5                                         # random organic lumps on the funnel wall
    fun = fade * (1.4 * a1 * r1 + 0.6 * a2 * r2 + blob - 0.45) + rimlump
    disp = np.where(hole_zone & front, fun, disp)
    pts = pts + nrm * disp[..., None]
    V = pts.reshape(-1, 3)
    idx = np.arange(NTH * NT).reshape(NTH, NT)
    i0 = idx; i1 = np.roll(idx, -1, 0)
    q = np.stack([i0[:, :-1], i0[:, 1:], i1[:, 1:], i1[:, :-1]], -1).reshape(-1, 4)
    rowmid = np.tile(np.arange(NT - 1), NTH)
    rho_r = rho.mean(0)
    first_glow = int(np.argmin(np.abs(rho_r - (P['core_r'] + 0.2)) + 10.0 * (np.arange(NT) < 4) + 0.2 * np.abs(np.gradient(rho_r))))
    tun0 = int(np.argmax(rho_r >= P['core_r'] - 0.05))              # tunnel wall starts here (glow fading to black inside)
    last_glow = int(np.argmax(rho_r >= P['ring_r'] + 1.2))
    m_row = np.full(NT, MAT_SKIN); m_row[:last_glow] = MAT_GLOW; m_row[:tun0] = MAT_CORE
    fm_q = m_row[rowmid]; fm = np.concatenate([fm_q, fm_q])
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ref, axis=0), axis=1))]
    U = (np.tile(th[:, None], (1, NT)) / (2*np.pi)) * 16.0
    Vv = np.tile(arc[None, :], (NTH, 1)) / 14.0
    # glow UV v: 0..0.22 tunnel wall (black deep -> bright at the mouth), 0.22..1 funnel up to the ring
    jj = np.arange(NT).astype(float)
    gv = np.where(jj < first_glow, 0.22 * (jj - tun0) / max(1, first_glow - tun0), 0.22 + 0.78 * (jj - first_glow) / max(1, last_glow - first_glow))
    grows = (np.arange(NT) >= tun0) & (np.arange(NT) < last_glow)
    Vv[:, grows] = np.clip(np.tile(gv[grows][None, :], (NTH, 1)), 0.005, 0.995)
    U[:, grows] = (np.tile(th[:, None], (1, NT)) / (2*np.pi) * 3.0)[:, grows]
    UV = np.stack([U, Vv], -1).reshape(-1, 2)
    Vx = np.concatenate([V, pts[0]]); seamU = UV.reshape(NTH, NT, 2)[0].copy()
    seamU[:, 0] = np.where(grows, 3.0, 16.0)
    UVx = np.concatenate([UV, seamU])
    seam_idx = np.arange(NTH * NT, NTH * NT + NT)
    last = q[(NTH - 1) * (NT - 1):]
    last[:, 2] = seam_idx[np.arange(NT - 1) + 1]; last[:, 3] = seam_idx[np.arange(NT - 1)]
    q[(NTH - 1) * (NT - 1):] = last
    tris = np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])
    nr = np.concatenate([nrm.reshape(-1, 3), nrm[0]])
    sp = np.concatenate([spacing.ravel(), spacing[0]])
    pitm = np.ones((NTH, NT), bool); pitm[:, :last_glow + 2] = False
    pf = np.concatenate([pitm.ravel(), pitm[0]])
    g.add(Vx, tris, fm, UVx, normals=nr, rad=60.0, spacing=sp, pit=pf)
    j_m = first_glow
    return dict(mouth_y=float(pts[:, j_m, 1].mean()), th=th, pts=pts, nrm=nrm, rho=rho, yv=yv, R=R,
                first_glow=first_glow, last_glow=last_glow, sil=int(np.argmax(rho.mean(0))))

def surf_point(B, th, t_row):
    th = th % (2*np.pi); fi = th / (2*np.pi) * NTH
    i0 = int(np.floor(fi)) % NTH; i1 = (i0 + 1) % NTH; a = fi - np.floor(fi)
    j0 = int(np.clip(np.floor(t_row), 0, NT - 2)); b = np.clip(t_row - j0, 0, 1)
    P = B['pts']; Nn = B['nrm']
    p = (P[i0, j0]*(1-a)*(1-b) + P[i1, j0]*a*(1-b) + P[i0, j0+1]*(1-a)*b + P[i1, j0+1]*a*b)
    n = (Nn[i0, j0]*(1-a)*(1-b) + Nn[i1, j0]*a*(1-b) + Nn[i0, j0+1]*(1-a)*b + Nn[i1, j0+1]*a*b)
    return p, n / (np.linalg.norm(n) + 1e-9)

def row_for(B, side, frac):
    sil = B['sil']
    if side < 0:
        a = B['last_glow']; return a + frac * (sil - a)
    return sil + frac * (NT - 1 - sil)

# ---------------- tubes ----------------
def frames(path):
    T = np.gradient(path, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    a = np.array([0, 0, 1.0]) if abs(T[0, 2]) < 0.9 else np.array([1.0, 0, 0])
    Nn = np.cross(T[0], a); Nn /= np.linalg.norm(Nn)
    NS = np.zeros_like(path); NS[0] = Nn
    for i in range(1, len(path)):
        n = NS[i-1] - T[i] * np.dot(NS[i-1], T[i]); ln = np.linalg.norm(n)
        NS[i] = NS[i-1] if ln < 1e-6 else n / ln
    return T, NS, np.cross(T, NS)

STATS = dict(tubes=0, curls=0, branches=0)
def tube(g, path, radii, mat, rope=0.06, knob=0.10, uv_scale=11.0, seed=0, res=0.32, max_sides=36, pit=True, vein=False):
    path = np.asarray(path, np.float64); radii = np.asarray(radii, np.float64)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    # resample along length to ~res spacing (curvature-safe: also limited by radius)
    n = int(np.clip(seg[-1] / res, 6, 2000))
    su = np.linspace(0, seg[-1], n)
    path = np.stack([np.interp(su, seg, path[:, k]) for k in range(3)], 1); radii = np.interp(su, seg, radii); seg = su
    M = len(path)
    sides = int(np.clip(round(2*np.pi*radii.max() / res * 0.85), 8, max_sides))
    T, Nn, BN = frames(path)
    ang = np.linspace(0, 2*np.pi, sides + 1)
    r = radii[:, None]
    tw = ang[None, :] + seg[:, None] * 0.35 / np.maximum(r, 0.6)
    mod = 1 + rope * np.cos(4 * tw) + knob * np.maximum(0, np.sin(seg[:, None] * 1.3 / np.maximum(r, 0.5) + 2.0*np.cos(3*ang[None, :]) + seed))**6
    ca, sa = np.cos(ang)[None, :, None], np.sin(ang)[None, :, None]
    dirs = ca * Nn[:, None, :] + sa * BN[:, None, :]
    ring = path[:, None, :] + (r * mod)[..., None] * dirs
    V = ring.reshape(-1, 3); NR = dirs.reshape(-1, 3)
    S1 = sides + 1
    idx = np.arange(M * S1).reshape(M, S1)
    q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    F = np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])
    circ = 2*np.pi*np.maximum(radii, 0.3)
    U = np.tile((seg / uv_scale)[:, None], (1, S1)); Vt = np.tile(ang[None, :] / (2*np.pi), (M, 1)) * np.clip(np.round(circ / uv_scale), 1, 8)[:, None]
    UV = np.stack([U, Vt], -1).reshape(-1, 2)
    tipc = len(V); V = np.vstack([V, path[-1] + T[-1] * radii[-1] * 0.8, path[0]])
    NR = np.vstack([NR, T[-1], -T[0]])
    UV = np.vstack([UV, [[seg[-1] / uv_scale, 0], [0, 0]]])
    tipF = np.stack([idx[-1, :-1], np.full(sides, tipc), idx[-1, 1:]], -1)
    rootF = np.stack([idx[0, 1:], np.full(sides, tipc + 1), idx[0, :-1]], -1)
    F = np.vstack([F, tipF, rootF])
    rv = np.r_[np.repeat(radii, S1), radii[-1], radii[0]]
    spc = np.r_[np.repeat(np.maximum(2*np.pi*radii/sides, seg[1] - seg[0]), S1), 1, 1]
    g.add(V, F, mat, UV, normals=NR, rad=rv, spacing=spc, pit=pit, vein=vein or mat == MAT_VEIN)
    STATS['tubes'] += 1
    return path, radii

def curl_path(p0, d0, side_vec, L, turns, step=0.25, lift=0.0, tight=1.0, stem=0.0):
    """fern fiddlehead: radius of curvature shrinking along the length (rho = rmin + (f*L - rmin)(1-s)^p)
    -> gently arched stem rolling into a nested scroll. 'turns' (1.6..3) maps to the openness f."""
    d0 = d0 / np.linalg.norm(d0); s_ = side_vec - d0 * np.dot(side_vec, d0); s_ /= np.linalg.norm(s_)
    nrm = np.cross(d0, s_)
    n = max(12, int(L / step)); s = np.linspace(0, 1, n); ds = L / (n - 1)
    f = np.clip(0.42 - 0.08 * turns, 0.18, 0.3); p = 1.0 * tight
    stem = min(stem, 0.6 * L); Ls = L - stem                         # optional gently arched stem before the scroll
    sl = np.cumsum(np.full(n, ds)) - ds
    ss = np.clip((sl - stem) / max(Ls, 1e-3), 0, 1)
    rho = np.where(sl < stem, max(stem, 1.0) * 2.5, 0.35 + (f * Ls - 0.35) * (1 - ss)**p)
    heading = np.r_[0, np.cumsum(ds / rho[:-1])]
    dirs = np.cos(heading)[:, None] * d0 + np.sin(heading)[:, None] * s_ + (lift * s**2)[:, None] * nrm
    return p0 + np.r_[[np.zeros(3)], np.cumsum(dirs[:-1] * ds, 0)]

def taper(n, r0, r1, power=1.1):
    s = np.linspace(0, 1, n); return r1 + (r0 - r1) * (1 - s)**power

def inside_env(p, margin=0.0):
    return (np.abs(p[:, 0]).max() <= ENV['x'] - margin and p[:, 2].min() >= ENV['z0'] + margin and p[:, 2].max() <= ENV['z1'] - margin
            and p[:, 1].min() >= ENV['y0'] and p[:, 1].max() <= ENV['y1'])

def unit(v): return v / (np.linalg.norm(v) + 1e-9)

def fiddle(g, p0, d0, side, L, r0, mat, depth=1, turns=None, r_tip=None, lift=None, vein=False, stem=0.0):
    """one fiddlehead curl (shrunk until it fits the envelope) + recursive side branches stacked on it"""
    turns = turns if turns is not None else rng.uniform(2.0, 2.9)
    lift = lift if lift is not None else rng.uniform(-0.25, 0.25)
    r_tip = r_tip if r_tip is not None else rng.uniform(0.25, 0.45)
    for att in range(14):
        if att == 7: side = -side                                       # try rolling the other way
        path = curl_path(p0, d0, side, L, turns, 0.25, lift, stem=stem)
        rr = taper(len(path), r0, r_tip, 1.35)
        if inside_env(path, rr.max() * 0.5): break
        L *= 0.9; r0 *= 0.95; stem *= 0.85
    else:
        if L < 3: return
    tube(g, path, rr, mat, seed=rng.uniform(0, 6), vein=vein, rope=0.03, knob=0.05)
    STATS['curls'] += 1
    if depth <= 0 or L < 5: return
    T, Nn, BN = frames(path)
    pn = unit(np.cross(d0, side - d0 * np.dot(side, d0)))          # curl plane normal
    nb = rng.integers(1, 4) if depth >= 2 else rng.integers(1, 3)
    for b in range(nb):
        s = rng.uniform(0.12, 0.55); i = int(s * (len(path) - 1))
        t = T[i]; outw = unit(np.cross(t, pn)) * (1 if rng.random() < 0.7 else -1)
        dch = unit(t * rng.uniform(0.2, 0.6) + outw * 0.8 + pn * rng.uniform(-0.6, 0.6))
        sch = unit(np.cross(dch, pn) * (1 if rng.random() < 0.5 else -1) + rng.normal(0, 0.3, 3))
        rch = rr[i] * rng.uniform(0.38, 0.6)
        fiddle(g, path[i] - dch * rr[i] * 0.4, dch, sch, L * rng.uniform(0.3, 0.5), rch, mat, depth - 1, vein=vein)
        STATS['branches'] += 1

# ---------------- pores: real crater displacement (KD-tree) ----------------
def uv_sphere(nu=8, nv=5):
    V = [(0, 0, -1.0)]
    for j in range(1, nv):
        ph = -np.pi / 2 + np.pi * j / nv
        for i in range(nu): V.append((np.cos(ph) * np.cos(2*np.pi*i/nu), np.cos(ph) * np.sin(2*np.pi*i/nu), np.sin(ph)))
    V.append((0, 0, 1.0)); V = np.array(V); F = []
    for i in range(nu): F.append((0, 1 + (i + 1) % nu, 1 + i))
    for j in range(nv - 2):
        for i in range(nu):
            a = 1 + j*nu + i; b_ = 1 + j*nu + (i + 1) % nu; c = b_ + nu; d = a + nu; F += [(a, b_, c), (a, c, d)]
    top = len(V) - 1; base = 1 + (nv - 2) * nu
    for i in range(nu): F.append((base + i, base + (i + 1) % nu, top))
    return V, np.array(F)

def apply_pores(V, F, FM, VN, VR, VS, PF, VEIN, hole_c, prng):
    idx = np.where(PF & (np.linalg.norm(VN, axis=1) > 0.5))[0]
    P = V[idx]
    C, Rr, Dk, Cv, Cn = [], [], [], [], []
    #            voxel  rmin  rmax  depth/r  kind
    # v9: only large + a sparse medium tier, shallower -> pores survive ≤200k as soft dimples (fine grain comes from the bake), no knob tier
    for vox, rmin, rmax, dk in [(4.6, 1.3, 2.4, 0.5), (3.4, 0.8, 1.3, 0.5)]:
        key = np.floor((P + prng.random(3) * vox) / vox).astype(np.int64)
        h = (key[:, 0] * 73856093) ^ (key[:, 1] * 19349663) ^ (key[:, 2] * 83492791)
        perm = prng.permutation(len(P)); _, first = np.unique(h[perm], return_index=True); sel = idx[perm[first]]
        r = prng.uniform(rmin, rmax, len(sel))
        r = np.minimum(r, VR[sel] * (0.5 if dk > 0 else 0.4))          # never punch through thin tentacles
        r = np.where(VR[sel] < 1.6, 0, r)                                   # thin curl tips stay smooth (clean scroll silhouettes)
        ok = (r > 1.5 * VS[sel]) & (r > rmin * 0.6)
        sel, r = sel[ok], r[ok]
        C.append(V[sel]); Rr.append(r); Dk.append(np.full(len(sel), dk)); Cv.append(VEIN[sel]); Cn.append(VN[sel])
    C = np.concatenate(C); Rr = np.concatenate(Rr); Dk = np.concatenate(Dk); Cv = np.concatenate(Cv); Cn = np.concatenate(Cn)
    dhc = np.linalg.norm(C - hole_c, axis=1)
    pnear = np.clip(1 - (dhc - 21) / 15, 0, 1) * (C[:, 1] < hole_c[1] + 6)
    pit_glow = (Dk > 0) & (Rr > 0.5) & (prng.random(len(C)) < float(os.environ.get('GLOW_PIT', 0.035)) * pnear + 0.008 * Cv)   # v9: far fewer purple polka dots
    tree = cKDTree(C)
    d, j = tree.query(P, k=6, distance_upper_bound=Rr.max() * 1.45)
    valid = np.isfinite(d); j = np.where(valid, j, 0)
    x = np.where(valid, d / Rr[j], 9.0)
    rj = Rr[j]; dkj = Dk[j]
    bowl = np.clip(1 - x * x, 0, None)**1.2
    pitw = np.where(dkj > 0, bowl, 0)
    lip = np.exp(-((x - 1.12) / 0.22)**2) * (dkj > 0) * 0.22 * rj
    knob = np.where(dkj < 0, np.clip(1 - x * x, 0, None)**1.5, 0) * (-dkj) * rj
    disp = (-(dkj * rj) * pitw * (dkj > 0) + lip + knob).sum(1)
    cav = pitw.max(1)
    lipv = np.zeros(len(V)); lipv[idx] = (np.exp(-((x - 1.12) / 0.22)**2) * (dkj > 0)).max(1)
    nearest = j[np.arange(len(j)), np.argmax(pitw, 1)]
    vg = np.zeros(len(V), bool); vg[idx] = pit_glow[nearest] & (cav > 0)
    V = V.copy(); V[idx] += VN[idx] * disp[:, None]
    cavity = np.zeros(len(V)); cavity[idx] = cav
    # pore faces: dark sockets; near the hole (and on vein tentacles) they glow purple
    fc = cavity[F].mean(1)
    cent = V[F].mean(1)
    dh = np.linalg.norm(cent - hole_c, axis=1)
    near = np.clip(1 - (dh - 21) / 16, 0, 1) * (cent[:, 1] < hole_c[1] + 6)
    veinf = VEIN[F[:, 0]]
    skin = (FM == MAT_SKIN) | (FM == MAT_VEIN)
    pore = skin & (fc > 0.34)
    FM = FM.copy()
    FM[pore] = MAT_PORE
    rim = skin & ~pore & (lipv[F].mean(1) > 0.8)                    # worn copper edges on the pore lips
    FM[rim] = MAT_RIM
    # glowing beads sitting at the bottom of selected pits (round purple glints, mostly around the hole)
    gi = np.where(pit_glow)[0]
    bv, bf = uv_sphere(8, 5)
    BV, BF, BU = [], [], []
    for n_, k in enumerate(gi):
        rb = Rr[k] * 0.27
        c0 = C[k] - Cn[k] * (Dk[k] * Rr[k] * 0.72)
        BV.append(c0 + bv * rb); BF.append(bf + n_ * len(bv)); BU.append(np.zeros((len(bv), 2)))
    beads = (np.concatenate(BV), np.concatenate(BF), np.concatenate(BU)) if gi.size else None
    return V, FM, beads, dict(pores=int((Dk > 0).sum()), knobs=int((Dk < 0).sum()), pore_faces=int(pore.sum()), rim_faces=int(rim.sum()), glow_beads=int(gi.size))

# ---------------- assemble ----------------
def build_all(P, pores=True):
    global rng
    rng = np.random.default_rng(20261117)
    for k in STATS: STATS[k] = 0
    g = G(); stats = {}
    B = build_body(g, P)
    hc = np.array([P['hx'], 0, P['hz']])
    # 1) front vortex: pitted main arms flowing out of the funnel lip along a long spiral sweep, curling off the silhouette;
    #    thin purple-veined arms run in the grooves between them (stronger spiral read than v2, pores kept on the main arms)
    # v9: 4 big continuous spiral arms (root Ø~11 m on the lip, sweeping ~200° outward, leaving the silhouette as
    #     tapering fiddlehead tips Ø<1 m) + 4 thin purple-veined arms in the grooves between them
    N_ARM = 4
    for k in range(2 * N_ARM):
        main = k % 2 == 0
        th0 = 2*np.pi * (k // 2 + (0 if main else 0.5)) / N_ARM + 0.35 + rng.uniform(-0.04, 0.04)
        sweep = rng.uniform(3.9, 4.3) if main else rng.uniform(3.4, 3.8)
        npt = 260; s = np.linspace(0, 1, npt)
        r0 = rng.uniform(5.2, 6.0) if main else rng.uniform(1.6, 2.1)
        rows = row_for(B, -1, (0.0 if main else 0.05) + (0.98 if main else 0.9) * s)
        pts = []; nrs = []
        for i in range(npt):
            p, n = surf_point(B, th0 - sweep * s[i]**0.8, rows[i]); pts.append(p); nrs.append(n)
        pts = np.array(pts); nrs = np.array(nrs)
        rad = r0 * (0.42 + 0.58 * np.clip(s / 0.4, 0, 1)**0.7) * (1 - 0.3 * s**1.5)
        band = np.exp(-(np.maximum(np.abs(pts[:, 2] - P['hz']) - 10, 0) / 12)**2)
        path = pts + nrs * (rad * (0.35 + (0.85 if main else 0.3) * np.clip(s / 0.3, 0, 1) * (1 - 0.45 * band)))[:, None]
        mat = MAT_SKIN if main else MAT_VEIN
        tube(g, path, rad, mat, seed=k, pit=main, rope=0.10 if main else 0.06, knob=0.06, max_sides=44)
        d_end = unit(path[-1] - path[-6]); outv = path[-1] - hc; outv[1] *= 0.3; outv = unit(outv)
        upf = max(0, (path[-1][2] - hc[2]) / 40.0); ang_e = math.atan2(path[-1][2] - hc[2], path[-1][0] - hc[0])
        Lc = (rng.uniform(34, 44) if main else rng.uniform(10, 15)) * (1 + 0.3 * upf)
        fiddle(g, path[-1] - d_end * rad[-1] * 0.5, unit(d_end * 0.7 + outv * 0.6), outv * 0.3 + np.cross(d_end, [0, 1, 0]), Lc, rad[-1], mat,
               depth=1, turns=2.5 if main else None, r_tip=0.45 if main else None)
        if main:                                                    # a few scale-like curls riding on each big arm
            Ta, Na, Ba = frames(path)
            for q_ in range(3):
                i = int((0.3 + 0.22 * q_ + rng.uniform(-0.05, 0.05)) * (npt - 1))
                outn = unit(nrs[i] * 0.8 + unit(path[i] - hc) * 0.4)
                fiddle(g, path[i] + outn * rad[i] * 0.55, unit(outn + Ta[i] * 0.5), unit(Ta[i] + rng.normal(0, 0.2, 3)),
                       rng.uniform(7, 11), rad[i] * 0.32, MAT_SKIN, depth=0)
    # 2) back swirl arms (lumpier, thicker)
    n_back = 6                                                  # v9: 6 thick continuous back spiral arms (rear view swirl)
    for k in range(n_back):
        th0 = 2*np.pi * k / n_back + rng.uniform(-0.1, 0.1)
        sweep = rng.uniform(3.3, 3.8); npt = 200; s = np.linspace(0, 1, npt)
        r0 = rng.uniform(4.6, 6.0)
        rows = row_for(B, +1, 0.92 - 0.9 * s)
        pts = []; nrs = []
        for i in range(npt):
            p, n = surf_point(B, th0 + sweep * s[i]**0.8, rows[i]); pts.append(p); nrs.append(n)
        pts = np.array(pts); nrs = np.array(nrs)
        rad = r0 * (0.45 + 0.55 * s**0.6) * (1 + 0.08 * np.sin(s * 13 + k))
        path = pts + nrs * (rad * 0.7)[:, None]
        tube(g, path, rad, MAT_SKIN, seed=50 + k)
        d_end = unit(path[-1] - path[-6]); outv = path[-1] - hc; outv[1] *= 0.3; outv = unit(outv)
        upf = max(0, (path[-1][2] - hc[2]) / 40.0); ang_e = math.atan2(path[-1][2] - hc[2], path[-1][0] - hc[0])
        Lc = rng.uniform(16, 26) * (1 + 0.4 * upf) * (0.72 + 0.38 * abs(math.sin(ang_e)))
        fiddle(g, path[-1] - d_end * rad[-1] * 0.5, unit(d_end * 0.5 + outv * 0.8), outv * 0.3 + np.cross(d_end, [0, -1, 0]), Lc, rad[-1], MAT_SKIN, depth=1)
    # 3) layered tentacle mass on the back / top: tentacles walking over the shell in stacked layers, curling up at the end
    for k in range(56):                                          # v9: fewer, taller stacked layers
        top_front = k >= 44
        th0 = rng.uniform(math.radians(10), math.radians(170)) if not top_front else rng.uniform(math.radians(40), math.radians(140))   # v9: crown only (rear spiral stays readable)
        if top_front:
            f0 = rng.uniform(0.55, 0.95); side = -1
        else:
            f0 = rng.uniform(0.05, 0.95); side = 1
        dth = rng.choice([-1, 1]) * rng.uniform(0.25, 0.8); dfr = rng.uniform(-0.35, 0.25)
        layer = rng.integers(0, 3); npt = 70; s = np.linspace(0, 1, npt)
        r0 = rng.uniform(2.0, 3.8) * (1.0 - 0.15 * layer)
        pts = []; nrs = []
        for i in range(npt):
            fr = np.clip(f0 + dfr * s[i], 0.02, 0.98)
            p, n = surf_point(B, th0 + dth * s[i], row_for(B, side, fr)); pts.append(p); nrs.append(n)
        pts = np.array(pts); nrs = np.array(nrs)
        rad = r0 * (0.55 + 0.45 * np.sin(np.pi * np.clip(s * 1.3, 0, 1))) * (1 - 0.3 * s)
        hgt = rad * 0.5 + layer * 2.6 + 3.5 * s**2
        path = pts + nrs * hgt[:, None]
        if not inside_env(path): continue
        tube(g, path, rad, MAT_SKIN, seed=100 + k)
        d_end = unit(path[-1] - path[-5])
        fiddle(g, path[-1] - d_end * rad[-1] * 0.4, unit(d_end + nrs[-1] * 0.6), unit(nrs[-1] + rng.normal(0, 0.3, 3)), rng.uniform(5, 13), rad[-1] * 1.05, MAT_SKIN,
               depth=1 if rng.random() < 0.5 else 0)
    # 4) the big tail (+ branches) and secondary strand
    ctrl = np.array([(28, -6, 40), (24, -12, 25), (11, -15, 12.5), (-8, -14, 9.5), (-27, -11, 12), (-39, -8, 20)])   # v9: raised for the thicker tail
    ss = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ctrl, axis=0), axis=1))]
    cs = CubicSpline(ss, ctrl, bc_type='natural'); su = np.linspace(0, ss[-1], 160); tail = cs(su)
    d_end = unit(cs(ss[-1], 1))
    st_ = np.linspace(0, 1, len(tail))
    trad = (10.5 - 4.5 * st_**0.9) * (0.82 + 0.18 * np.clip(st_ / 0.15, 0, 1)) * (1 + 0.07 * np.sin(np.linspace(0, 26, len(tail))))   # v9: Ø~21 → Ø12, organic swell
    tube(g, tail, trad, MAT_SKIN, seed=99, knob=0.06, rope=0.07, max_sides=56)
    fiddle(g, tail[-1] - d_end * 2, d_end, np.array([0.6, 0, 0.8]) - d_end * 0.2 + np.array([0.5, 0, 0]), 50, trad[-1], MAT_SKIN, depth=1, turns=2.3, r_tip=0.6)
    Tt, Nt_, Bt = frames(tail)
    for k in range(4):                                            # a few curls riding on the tail
        i = int(rng.uniform(0.15, 0.95) * (len(tail) - 1)); up = unit(np.array([0, -0.4, 1.0]) + rng.normal(0, 0.35, 3))
        fiddle(g, tail[i] + up * trad[i] * 0.5, unit(up + Tt[i] * rng.uniform(-0.5, 0.5)), unit(Tt[i] * rng.choice([-1, 1]) + rng.normal(0, 0.2, 3)),
               rng.uniform(7, 12), trad[i] * rng.uniform(0.25, 0.35), MAT_VEIN if k % 2 else MAT_SKIN, depth=1)
    # 5) dense periphery: dozens of fiddleheads of varied size all round the silhouette, in front / mid / back layers
    NPER = 33                                                   # v9: fewer, thicker silhouette curls
    for k in range(NPER):
        th0 = 2*np.pi * k / NPER + rng.uniform(-0.04, 0.04)
        lay = k % 3                                                 # 0 front, 1 silhouette, 2 back
        side = -1 if lay == 0 else 1
        fr = rng.uniform(0.72, 0.95) if lay == 0 else (rng.uniform(0.0, 0.06) if lay == 1 else rng.uniform(0.08, 0.25))
        if math.radians(205) < th0 < math.radians(290) and k % 2 == 0: continue     # tail band: lighter so the tail reads
        p, n = surf_point(B, th0, row_for(B, side, fr))
        outv = p - hc; outv[1] *= 0.15; outv = unit(outv)
        tang = np.cross([0, 1.0, 0], outv) * (1 if (k // 2) % 2 == 0 else -1)
        big = (k % 3 == 1)
        upf = max(0.0, math.sin(th0))
        L = (rng.uniform(32, 46) if big else rng.uniform(11, 22)) * (1 + 0.25 * upf)
        r0 = np.clip(L * 0.09, 1.6, 4.4)
        ydir = {0: -0.35, 1: 0.0, 2: 0.35}[lay]
        d0 = unit(outv * 0.5 + tang * 0.85 + np.array([0, ydir, 0]))           # stem runs along the rim, scroll rolls outward
        fiddle(g, p - outv * r0 * 0.6, d0, unit(outv + np.array([0, -ydir * 0.3, 0])), L, r0, stem=(rng.uniform(4, 10) if big else 0.0), mat=MAT_VEIN if k % 7 == 0 else MAT_SKIN, depth=1 if big else 0)
    # 6) forward-leaning horn curls at the top and bottom front (they make the crescent: scoop between them)
    for k in range(8):
        top = k < 5
        th0 = rng.uniform(math.radians(55), math.radians(125)) if top else rng.uniform(math.radians(235), math.radians(305))
        p, n = surf_point(B, th0, row_for(B, -1, rng.uniform(0.55, 0.9)))
        outv = unit(np.array([p[0] - hc[0], 0, p[2] - hc[2]]))
        d0 = unit(outv * 0.6 + np.array([0, -0.75, 0]) + rng.normal(0, 0.15, 3))
        sd = unit(np.array([0, 0.4, 0]) + outv * -0.8 + rng.normal(0, 0.2, 3))
        fiddle(g, p, d0, sd, rng.uniform(9, 17), rng.uniform(1.6, 3.0), MAT_SKIN, depth=1)
    # 6b) tall scroll stems rising from the crown (the reference's tips reach the 120 m line)
    for k in range(7):
        th0 = math.radians(60 + 60 * k / 6) + rng.uniform(-0.06, 0.06)
        p, n = surf_point(B, th0, row_for(B, 1 if k % 2 else -1, rng.uniform(0.0, 0.15)))
        d0 = unit(np.array([math.cos(th0) * 0.35, rng.uniform(-0.2, 0.2), 1.0]))
        sd = unit(np.array([-math.cos(th0) - (0.6 if k % 2 else -0.6), 0, -0.2]))
        fiddle(g, p - d0 * 2, d0, sd, rng.uniform(40, 52), rng.uniform(2.0, 2.8), MAT_SKIN, depth=1, turns=rng.uniform(2.2, 2.8), stem=rng.uniform(12, 20))
    # 7) organic ridged rim: small tentacles rooted on the lip, curling into the funnel
    for k in range(12):
        th0 = 2*np.pi * k / 12 + rng.uniform(-0.05, 0.05)
        p, n = surf_point(B, th0, B['last_glow'] + rng.uniform(1.0, 4.0))
        inw = unit(np.array([hc[0] - p[0], 0, hc[2] - p[2]]))
        fiddle(g, p - n * 0.3, unit(n * 0.8 + inw * 0.6), unit(inw - n * 0.3), rng.uniform(4, 8), rng.uniform(0.8, 1.5), MAT_VEIN, depth=0, turns=rng.uniform(1.6, 2.3))
    # 8) small surface fiddleheads sprouting everywhere on the shell
    for k in range(16):                                          # v9: few, back only (no uniform small curls on the front)
        side = 1
        th0 = rng.uniform(0, 2*np.pi); fr = rng.uniform(0.12, 0.9)
        p, n = surf_point(B, th0, row_for(B, side, fr))
        if side < 0 and abs(p[2] - hc[2]) < 18 and np.hypot(p[0] - hc[0], p[2] - hc[2]) < 34: continue   # keep the scoop clean-ish
        tang = unit(np.cross(n, rng.normal(0, 1, 3)))
        fiddle(g, p - n * 0.5, unit(n * 0.8 + tang * 0.6), unit(-n * 0.4 + tang), rng.uniform(3.5, 8), rng.uniform(0.6, 1.4), MAT_SKIN, depth=0)
    # v9: crown ridges — thick rolls following the top silhouette in front / mid / back layers with an undulating lift,
    #     so the TOP view reads as stacked layers instead of a flat slab
    for k in range(7):
        lay = k % 3
        side = -1 if lay == 0 else 1
        fr = {0: 0.78, 1: 0.02, 2: 0.35}[lay] + rng.uniform(-0.05, 0.05)
        tha, thb = math.radians(rng.uniform(15, 50)), math.radians(rng.uniform(130, 165))
        if k % 2: tha, thb = thb, tha
        npt = 180; s = np.linspace(0, 1, npt)
        pts = []; nrs = []
        for i in range(npt):
            p, n = surf_point(B, tha + (thb - tha) * s[i], row_for(B, side, np.clip(fr + 0.12 * math.sin(3 * math.pi * s[i] + k), 0.0, 0.97)))
            pts.append(p); nrs.append(n)
        pts = np.array(pts); nrs = np.array(nrs)
        rad = rng.uniform(3.0, 4.4) * (0.55 + 0.45 * np.sin(np.pi * s)**0.6) * (1 + 0.12 * np.sin(9 * s + k))
        lift = rad * 0.55 + (1.2 + 1.4 * lay) * (0.6 + 0.4 * np.sin(2 * np.pi * s * 1.5 + k))
        path = pts + nrs * lift[:, None]
        if not inside_env(path, 1.0): continue
        tube(g, path, rad, MAT_SKIN, seed=300 + k, rope=0.08, knob=0.05)
        d_end = unit(path[-1] - path[-5])
        fiddle(g, path[-1] - d_end * rad[-1] * 0.4, unit(d_end + nrs[-1] * 0.5), unit(nrs[-1] + rng.normal(0, 0.3, 3)), rng.uniform(10, 16), rad[-1], MAT_SKIN, depth=0)
    V, F, FM, UV, VN, VR, VS, PF, VEIN = g.arrays()
    global LAST_VN
    LAST_VN = VN.copy()
    if pores:
        V, FM, beads, pst = apply_pores(V, F, FM, VN, VR, VS, PF, VEIN, np.array([P['hx'], B['mouth_y'], P['hz']]), np.random.default_rng(7))
        stats.update(pst)
        if beads is not None:
            bv, bf, bu = beads
            F = np.vstack([F, bf + len(V)]); FM = np.r_[FM, np.full(len(bf), MAT_PORE_GLOW)]; UV = np.vstack([UV, bu]); V = np.vstack([V, bv])
            LAST_VN = np.vstack([LAST_VN, np.zeros((len(bv), 3))])
    stats.update(STATS); stats['mouth_y_raw'] = B['mouth_y']
    return (V, F, FM, UV), stats

def hole_warp(V, c, ring_now, mouth_y_now, P_fit):
    """tiny local warp around the opening: put the hole centre / Ø40 / Ø26 / recess exactly on spec after the box fit
    (iterating the whole build oscillates because the curl envelope-shrinking is discrete). Full effect inside the lip,
    fades to zero 20 m outside it, so the bbox extremes (curl tips, tail) are untouched."""
    d = np.hypot(V[:, 0] - c[0], V[:, 2] - c[2])
    t = np.clip((d - (RING_D / 2 + 6)) / 20.0, 0, 1); w = 1 - (3 * t * t - 2 * t ** 3)
    kx, kz = (RING_D / 2) / ring_now[0], (RING_D / 2) / ring_now[1]
    tgt = np.array([0.0, HC_Z])
    out = V.copy()
    out[:, 0] = V[:, 0] + w * ((tgt[0] - c[0]) + (V[:, 0] - c[0]) * (kx - 1))
    out[:, 2] = V[:, 2] + w * ((tgt[1] - c[2]) + (V[:, 2] - c[2]) * (kz - 1))
    ty = np.clip((d - (RING_D / 2 + 2)) / 8.0, 0, 1); wy = 1 - (3 * ty * ty - 2 * ty ** 3)
    front = V[:, 1] < mouth_y_now + 16
    out[:, 1] = V[:, 1] + wy * front * ((-BBOX[1] / 2 + RECESS) - mouth_y_now)
    return out

def vertex_normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V)
    for c in range(3):
        N[:, c] = np.bincount(F[:, 0], fn[:, c], len(V)) + np.bincount(F[:, 1], fn[:, c], len(V)) + np.bincount(F[:, 2], fn[:, c], len(V))
    return N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-12)

def cavity_tint(V, F, FM, seed=5):
    """per-vertex concavity at two scales (KD-tree on subsamples): + = crevice / between arms, - = exposed ridge / rim.
    -> vertex colour multiplier: purple in crevices, warm copper on ridges (Blender: multiplies the albedo; web: COLOR_0)."""
    N = vertex_normals(V, F)
    if 'LAST_VN' in globals() and len(LAST_VN) == len(V):          # orient with the generator's outward normals (tube/body winding differs)
        flip = (N * LAST_VN).sum(1) < 0; N[flip] = -N[flip]
    r = np.random.default_rng(seed); cav = np.zeros(len(V))
    for ns, k, w in ((30000, 24, 0.6), (220000, 16, 0.4)):
        sub = V[r.choice(len(V), min(ns, len(V)), replace=False)]
        d, j = cKDTree(sub).query(V, k=k, workers=-1)
        dv = sub[j] - V[:, None, :]
        c = (dv * N[:, None, :]).sum(-1).mean(1) / (np.linalg.norm(dv, axis=-1).mean(1) + 1e-6)
        cav += w * c
    m, p5, p95 = np.percentile(cav, [50, 5, 95])                   # centre on the median (tubes lying on the shell bias it +)
    pos = np.clip((cav - m) / (p95 - m + 1e-6), 0, 1); neg = np.clip((m - cav) / (m - p5 + 1e-6), 0, 1)
    crev = np.clip((pos - 0.25) / 0.75, 0, 1)**0.8; ridge = np.clip((neg - 0.6) / 0.4, 0, 1)**1.3
    cav = pos - neg
    base = np.array([0.36, 0.30, 0.34]); purple = np.array([0.45, 0.26, 0.85]); copper = np.array([1.9, 1.0, 0.45])
    col = base + (purple - base) * crev[:, None]; col = col + (copper - col) * ridge[:, None]
    return col.astype(np.float32), cav.astype(np.float32)

def compute(iters=3):
    """iterate the hole parameters against the fit (fast, without pores), final build with pores, exact fit to 100 x 48 x 120
    (origin = bbox bottom centre), then a local hole warp for the last few %."""
    P = dict(ring_r=RING_D/2, core_r=CORE_D/2, recess=RECESS - A_SCOOP - 2.0, hx=0.0, hz=HC_Z)
    def measure(V, st):
        lo, hi = V.min(0), V.max(0); s = np.array(BBOX) / (hi - lo)
        off = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
        hole = (np.array([P['hx'], 0, P['hz']]) - off) * s
        mouth = (st['mouth_y_raw'] - off[1]) * s[1]
        return s, off, hole, mouth
    for it in range(iters + 1):
        final = it == iters
        (V, F, FM, UV), st = build_all(P, pores=final)
        s, off, hole, mouth = measure(V, st)
        print('fit iter', it, 'scale', np.round(s, 4), 'hole', np.round(hole, 2), 'recess', round(mouth + BBOX[1] / 2, 2), 'tris', len(F), flush=True)
        if final: break
        sxz = 0.5 * (s[0] + s[2])
        P['ax'], P['az'] = sxz / s[0], sxz / s[2]
        P['ring_r'] = RING_D / 2 / sxz; P['core_r'] = CORE_D / 2 / sxz
        P['hx'] += (0.0 - hole[0]) / s[0]; P['hz'] += (HC_Z - hole[2]) / s[2]
        P['recess'] += (RECESS - (mouth + BBOX[1] / 2)) / s[1]
    ax, az = P.get('ax', 1.0), P.get('az', 1.0)
    Vf = (V - off) * s
    ring_now = (P['ring_r'] * ax * s[0], P['ring_r'] * az * s[2])
    Vw = hole_warp(Vf, hole, ring_now, mouth, P)
    lo, hi = Vw.min(0), Vw.max(0)
    info = dict(scale_fit=s.tolist(), pre_warp=dict(hole_centre=hole.tolist(), ring_d=[2 * r for r in ring_now], recess=float(mouth + BBOX[1] / 2)),
                hole_centre=[0.0, float(mouth), HC_Z], ring_d_x=RING_D, ring_d_z=RING_D, core_d_x=CORE_D, core_d_z=CORE_D, recess_from_front_face=RECESS,
                bbox_after_warp=[lo.tolist(), hi.tolist()], params={k: float(v) for k, v in P.items()},
                stats={k: (float(v) if not isinstance(v, int) else v) for k, v in st.items()})
    # warp can't touch the extremes, but re-assert the exact box just in case
    s2 = np.array(BBOX) / (hi - lo); off2 = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    info['post_warp_refit'] = s2.tolist()
    Vout = (Vw - off2) * s2
    if len(LAST_VN) == len(Vout):                                   # consistent outward winding (tubes were built inward)
        fn = np.cross(Vout[F[:, 1]] - Vout[F[:, 0]], Vout[F[:, 2]] - Vout[F[:, 0]])
        ref = LAST_VN[F].sum(1)
        bad = ((fn * ref).sum(1) < 0) & (np.linalg.norm(ref, axis=1) > 0.5)
        F = F.copy(); F[bad] = F[bad][:, [0, 2, 1]]; info['faces_flipped'] = int(bad.sum())
    col, cav = cavity_tint(Vout, F, FM); info['_vcol'] = col; info['_vcav'] = cav
    if os.environ.get('SMOOTH_LOW', '1') == '1':
        # v9: identical build WITHOUT pores (same rng / params / fit / warp) -> the ≤200k display mesh is decimated from this
        # smooth surface (no crater lips -> no shard facets); the pore mesh above becomes the normal/AO bake source.
        (Vs, Fs, FMs, UVs), _ = build_all(P, pores=False)
        Vs = hole_warp((Vs - off) * s, hole, ring_now, mouth, P)
        Vs = (Vs - off2) * s2
        if len(LAST_VN) == len(Vs):
            fn = np.cross(Vs[Fs[:, 1]] - Vs[Fs[:, 0]], Vs[Fs[:, 2]] - Vs[Fs[:, 0]]); ref = LAST_VN[Fs].sum(1)
            bad = ((fn * ref).sum(1) < 0) & (np.linalg.norm(ref, axis=1) > 0.5); Fs = Fs.copy(); Fs[bad] = Fs[bad][:, [0, 2, 1]]
        cs_, cv_ = cavity_tint(Vs, Fs, FMs)
        info['_smooth'] = (Vs, Fs, FMs, UVs, cs_, cv_)
    return Vout, F, FM, UV, info

if __name__ == '__main__':
    import time; t0 = time.time()
    if '--fast' in sys.argv:
        P = dict(ring_r=20.6, core_r=13.4, recess=2.0, hx=3.5, hz=56.8)
        (V, F, FM, UV), st = build_all(P, pores='--pores' in sys.argv)
        print('VERTS', len(V), 'TRIS', len(F), V.min(0).round(1), V.max(0).round(1), st, 'time %.1f' % (time.time() - t0))
    else:
        V, F, FM, UV, info = compute()
        print('VERTS', len(V), 'TRIS', len(F), V.min(0).round(3), V.max(0).round(3), 'time %.1f' % (time.time() - t0))
        print(json.dumps(info, indent=1, default=float))
