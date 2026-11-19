# v10 independent check on the exported model.glb (glTF Y-up -> Z-up): bbox, tris, hole centre, Ø core (4 dirs), funnel, recess
import json, struct, sys, numpy as np
R = '/workspace/outputs/black_hole_structure/'
P = sys.argv[1] if len(sys.argv) > 1 else R + 'model.glb'
d = open(P, 'rb').read(); l = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20 + l]); b0 = 20 + l + 8
def acc(i):
    a = j['accessors'][i]; bv = j['bufferViews'][a['bufferView']]; n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
    dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[a['componentType']]; o = b0 + bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    x = np.frombuffer(d, dt, a['count'] * n, o); return x.reshape(-1, n) if n > 1 else x
parts = {}; tris = 0; allv = []
for m in j['meshes']:
    for p in m['primitives']:
        v = acc(p['attributes']['POSITION']).astype(np.float64); v = np.c_[v[:, 0], -v[:, 2], v[:, 1]]
        f = acc(p['indices']).reshape(-1, 3); tris += len(f); allv.append(v)
        parts[j['materials'][p['material']]['name']] = v[np.unique(f.ravel())]
V = np.vstack(allv); lo, hi = V.min(0), V.max(0)
C = parts['BH_Core_Black']; G = parts['BH_Glow_Rim']
hc = np.array([0.5 * (C[:, 0].min() + C[:, 0].max()), 0.5 * (C[:, 2].min() + C[:, 2].max())])
def dia(Pt, fn, n=8):
    r = np.hypot(Pt[:, 0] - hc[0], Pt[:, 2] - hc[1]); a = np.arctan2(Pt[:, 2] - hc[1], Pt[:, 0] - hc[0]); out = []
    for k in range(n // 2):
        t = k * np.pi / (n // 2); m1 = np.abs(np.angle(np.exp(1j * (a - t)))) < 0.06; m2 = np.abs(np.angle(np.exp(1j * (a - t - np.pi)))) < 0.06
        out.append(float(fn(r[m1]) + fn(r[m2])))
    return out
rc = np.hypot(C[:, 0] - hc[0], C[:, 2] - hc[1]); seam = C[rc > 12.7]          # Ø26 mouth ring of the core
rg = np.hypot(G[:, 0] - hc[0], G[:, 2] - hc[1])
res = dict(bbox_min=lo.round(3).tolist(), bbox_max=hi.round(3).tolist(), bbox_size=(hi - lo).round(3).tolist(), tris=int(tris), verts=int(len(V)),
           hole_centre_xz_from_core=[round(float(hc[0]), 2), round(float(hc[1]), 2)],
           core_diameter_measured_4dirs=np.round(dia(C, np.max), 2).tolist(), glow_outer_diameter_4dirs=np.round(dia(G[rg < 21.5], np.max), 2).tolist(),
           ring_d_param=[40.0, 40.0], core_mouth_y=round(float(np.median(seam[:, 1])), 2), front_face_y=round(float(lo[1]), 2),
           recess_front_face_to_core_mouth=round(float(np.median(seam[:, 1]) - lo[1]), 2), core_dish_back_y=round(float(C[:, 1].max()), 2),
           materials=list(parts.keys()))
print(json.dumps(res, indent=1)); json.dump(res, open(R + 'verify.json', 'w'), indent=1)
