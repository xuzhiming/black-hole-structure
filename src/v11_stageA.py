# v11 stage A (blender): v10 geometry (GLB fit + spec hole + 196k low + custom normals) -> cached blend + mesh arrays for the scale field
import os, sys, numpy as np, bpy
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.environ.get('V11_CACHE', '/tmp/v11')
src = open(H + '/scene_v10.py').read().split('# ---------- 6 bake')[0]
exec(compile(src, H + '/scene_v10.py', 'exec'))
def arrays(o):
    me = o.data; me.calc_loop_triangles() if hasattr(me, 'calc_loop_triangles') else None
    co = getco(o); n = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('normal', n)
    fv = np.zeros(len(me.polygons) * 3, np.int32); me.polygons.foreach_get('vertices', fv)
    fm = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('material_index', fm)
    return dict(co=co.astype(np.float32), n=n.reshape(-1, 3), f=fv.reshape(-1, 3), fm=fm)
np.savez(OUT + '/dense.npz', **arrays(dense)); np.savez(OUT + '/low.npz', **arrays(ob))
import json; json.dump(info, open(OUT + '/infoA.json', 'w'), default=float)
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/A.blend')
print('STAGE_A_DONE', len(dense.data.vertices), len(ob.data.polygons), flush=True)
