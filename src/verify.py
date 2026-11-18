# independent check on the final fitted v2 mesh (read from scene.py's cache): bbox, tris, hole centre, Ø core / Ø ring, recess
import sys, os, json, glob, pickle, hashlib, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); import build
h = hashlib.md5(open(os.path.join(os.path.dirname(__file__), 'build.py'), 'rb').read()).hexdigest()
cache = f'/tmp/bh_mesh_{h}.pkl'
V, F, FM, UV, info = pickle.load(open(cache, 'rb')) if os.path.exists(cache) else build.compute()
DEC = float(os.environ.get('DECIMATE', 0.08)); tris_full = len(F)
if DEC < 1.0: V, F, FM = pickle.load(open(f'/tmp/bh_dec_{h}_{DEC}.pkl', 'rb'))   # v6: measure the decimated mesh written by scene.py
lo, hi = V.min(0), V.max(0)
cv = np.unique(F[FM == build.MAT_CORE].ravel()); gv = np.unique(F[FM == build.MAT_GLOW].ravel())
C = V[cv]; hc = np.array([0.5 * (C[:, 0].min() + C[:, 0].max()), 0, 0.5 * (C[:, 2].min() + C[:, 2].max())])   # v9: bbox centre (vertex mean is biased after uneven decimation)
def dia(P, fn, n=8):
    r = np.hypot(P[:, 0] - hc[0], P[:, 2] - hc[2]); a = np.arctan2(P[:, 2] - hc[2], P[:, 0] - hc[0]); out = []
    for k in range(n // 2):
        t = k * np.pi / (n // 2)
        m1 = np.abs(np.angle(np.exp(1j * (a - t)))) < 0.04; m2 = np.abs(np.angle(np.exp(1j * (a - t - np.pi)))) < 0.04
        out.append(float(fn(r[m1]) + fn(r[m2])))
    return out
core_plane_y = float(np.median(C[:, 1]))
G = V[gv]; rg = np.hypot(G[:, 0] - hc[0], G[:, 2] - hc[2])
rimband = G[(rg > 18) & (rg < 22)]                      # funnel lip around Ø40
mouth_y = float(np.percentile(rimband[:, 1], 5)) if len(rimband) else float('nan')
cm = G[rg < CORE_D_HALF + 0.6] if False else G[rg < 13.6]
core_mouth_y = float(np.median(cm[cm[:, 1] < np.percentile(cm[:, 1], 10)][:, 1]))   # where the Ø26 tunnel opens
res = dict(bbox_min=lo.round(3).tolist(), bbox_max=hi.round(3).tolist(), bbox_size=(hi - lo).round(3).tolist(),
           tris=int(len(F)), verts=int(len(V)), tris_full=int(tris_full), decimate_ratio=DEC,
           hole_centre_xz_from_core=[round(float(hc[0]), 2), round(float(hc[2]), 2)],
           core_diameter_measured_4dirs=np.round(dia(C, np.max), 2).tolist(),
           glow_inner_diameter_4dirs=np.round(dia(G, np.min), 2).tolist(),
           ring_d_param=[info['ring_d_x'], info['ring_d_z']],
           funnel_lip_y_at_r20=round(mouth_y, 2), core_plane_y=round(core_plane_y, 2),
           recess_front_face_to_core_mouth=round(core_mouth_y - lo[1], 2), core_mouth_y=round(core_mouth_y, 2), funnel_depth_lip_to_core_plane=round(core_plane_y - mouth_y, 2), recess_param=info['recess_from_front_face'],
           mat_face_counts={n: int((FM == i).sum()) for i, n in enumerate(['skin', 'vein', 'glow', 'core', 'pore_dark', 'pore_glow', 'rim_wear'])},
           pore_stats=info['stats'].get('pores') if isinstance(info.get('stats'), dict) else None,
           fit_scale=info['scale_fit'], post_warp_refit=info['post_warp_refit'])
print(json.dumps(res, indent=1)); json.dump(res, open(build.ROOT + '/verify.json', 'w'), indent=1)
