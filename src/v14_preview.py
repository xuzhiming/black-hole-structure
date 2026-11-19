# quick look (blender): hi.npz -> flat-ish material + funnel glow by position, rend_common six views at low samples
import bpy, os, sys, numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H); import rend_common as rc
C = os.environ.get('V14_CACHE', '/tmp/v14'); OUT = os.environ.get('OUT_R', C + '/prev')
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
Z = np.load(C + '/hi.npz'); v, f = Z['v'], Z['f']
me = bpy.data.meshes.new('hi'); me.vertices.add(len(v)); me.vertices.foreach_set('co', v.ravel())
me.loops.add(f.size); me.loops.foreach_set('vertex_index', f.ravel()); me.polygons.add(len(f))
me.polygons.foreach_set('loop_start', np.arange(0, f.size, 3)); me.polygons.foreach_set('loop_total', np.full(len(f), 3)); me.update(); me.validate()
ob = bpy.data.objects.new('BlackHole_Structure', me); sc.collection.objects.link(ob)
me.polygons.foreach_set('use_smooth', np.ones(len(f), bool))
cen = v[f].mean(1); rh = np.hypot(cen[:, 0], cen[:, 2] - 58); YM = float(os.environ.get('Y_M', 9.0))
fm = np.zeros(len(f), np.int32); fm[(rh < 21.5) & (cen[:, 1] < YM - 0.2) & (cen[:, 1] > YM - 26)] = 1; fm[(rh < 13.2) & (np.abs(cen[:, 1] - YM) < 0.4)] = 2
def mat(name, col, em=None, es=0.0, rough=0.45, metal=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if em: b.inputs['Emission Color'].default_value = (*em, 1); b.inputs['Emission Strength'].default_value = es
    me.materials.append(m)
mat('skin', (0.05, 0.025, 0.025)); mat('glow', (0.02, 0.005, 0.03), (0.35, 0.06, 0.8), 1.5, 0.6, 0.0); mat('core', (0, 0, 0), rough=1, metal=0)
me.polygons.foreach_set('material_index', fm); me.update()
bc = rc.setup(sc, hole=(0, -6, 58), hole_w=300, key=6.5)
V = rc.views(sc, hc=(0, -24, 58)); only = os.environ.get('ONLY', 'front,rear,left,right,top,axo').split(',')
rc.render(sc, bc, V, OUT, only=only, samples=int(os.environ.get('SAMPLES', 8)))
