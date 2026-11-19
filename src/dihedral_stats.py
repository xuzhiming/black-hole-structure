# dihedral-angle + shading-normal stats for a GLB (skin material only and all)
import json, struct, sys, numpy as np
def load(P):
    d = open(P, 'rb').read(); l = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20 + l]); b0 = 20 + l + 8
    def acc(i):
        a = j['accessors'][i]; bv = j['bufferViews'][a['bufferView']]; n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
        dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[a['componentType']]; o = b0 + bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        x = np.frombuffer(d, dt, a['count'] * n, o); return x.reshape(-1, n) if n > 1 else x
    out = []
    for m in j['meshes']:
        for p in m['primitives']:
            mat = j['materials'][p['material']]['name']
            out.append((mat, acc(p['attributes']['POSITION']).astype(np.float64), acc(p['attributes']['NORMAL']).astype(np.float64), acc(p['indices']).reshape(-1, 3).astype(np.int64)))
    return out
def stats(V, N, F, label):
    # weld by position
    key = np.round(V, 4); _, wid, inv = np.unique(key, axis=0, return_index=True, return_inverse=True); inv = inv.ravel()
    Fw = inv[F]; Vw = V[wid]
    fn = np.cross(Vw[Fw[:, 1]] - Vw[Fw[:, 0]], Vw[Fw[:, 2]] - Vw[Fw[:, 0]]); area = np.linalg.norm(fn, axis=1); fn /= area[:, None] + 1e-12
    E = np.sort(np.stack([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]], 1).reshape(-1, 2), 1); fid = np.repeat(np.arange(len(Fw)), 3)
    o = np.lexsort((E[:, 1], E[:, 0])); E, fid = E[o], fid[o]
    same = (E[1:] == E[:-1]).all(1); a, b = fid[:-1][same], fid[1:][same]
    ang = np.degrees(np.arccos(np.clip((fn[a] * fn[b]).sum(1), -1, 1)))
    # shading normal split: same position, different normals
    nn = N / (np.linalg.norm(N, axis=1)[:, None] + 1e-12); ref = np.zeros((len(wid), 3)); np.add.at(ref, inv, nn); ref /= np.linalg.norm(ref, axis=1)[:, None] + 1e-12
    dev = np.degrees(np.arccos(np.clip((nn * ref[inv]).sum(1), -1, 1)))
    # vertex normal vs face normal (how far shading normals depart from facets)
    fvn = nn[F].mean(1); fvn /= np.linalg.norm(fvn, axis=1)[:, None] + 1e-12
    fdev = np.degrees(np.arccos(np.clip((fvn * fn).sum(1), -1, 1)))
    el = np.linalg.norm(Vw[E[1:][same][:, 0]] - Vw[E[1:][same][:, 1]], axis=1)
    r = dict(label=label, faces=len(F), edges=len(ang), sharp30=round(float((ang > 30).mean() * 100), 2), sharp45=round(float((ang > 45).mean() * 100), 2),
             sharp60=round(float((ang > 60).mean() * 100), 2), dihedral_mean=round(float(ang.mean()), 2), dihedral_p99=round(float(np.percentile(ang, 99)), 1),
             edge_len_med=round(float(np.median(el)), 3), split_normal_verts_pct=round(float((dev > 5).mean() * 100), 2), facet_vs_shading_mean=round(float(fdev.mean()), 2))
    return r
if __name__ == '__main__':
    for P in sys.argv[1:]:
        parts = load(P)
        for mat, V, N, F in parts:
            if mat == 'BH_Skin_Bronze': print(P.split('/')[-2] if '/' in P else P, json.dumps(stats(V, N, F, mat)))
