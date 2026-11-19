# v17 close-up crops (blender): open a model.blend and render tentacles / tail / tail-fill / rear-vortex close-ups.
# env: BLEND (model.blend path), OUT (dir), NSTR_OVR (override normal-map strength), CLEAR_CN=1 (drop custom normals -> plain smooth),
#      FLAT=1 (flat shading), SAMPLES, RES (width)
import bpy, os, sys, numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H); import rend_common as rc
B = os.environ['BLEND']; OUT = os.environ['OUT']; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=B); sc = bpy.context.scene
ob = bpy.data.objects['BlackHole_Structure']
for o in list(sc.objects):
    if o.type in ('LIGHT', 'CAMERA'): bpy.data.objects.remove(o, do_unlink=True)
if os.environ.get('NSTR_OVR'):
    for m in ob.data.materials:
        for n in m.node_tree.nodes:
            if n.type == 'NORMAL_MAP': n.inputs['Strength'].default_value = float(os.environ['NSTR_OVR'])
if os.environ.get('CLEAR_CN') == '1':
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    if ob.data.has_custom_normals: bpy.ops.mesh.customdata_custom_splitnormals_clear()
if os.environ.get('FLAT') == '1':
    ob.data.polygons.foreach_set('use_smooth', np.zeros(len(ob.data.polygons), bool))
bc = rc.setup(sc, hole=(0, 2, 58), hole_w=300, key=6.5)
sc.objects['Rim_Sun'].data.energy = 3.6
C = {'tentacles': ((48, -62, 104), (24, -14, 86)), 'tail': ((8, -72, 22), (-6, -16, 9)), 'tailfill': ((-34, -62, 34), (-20, -14, 20)),
     'rear': ((-12, 72, 74), (-6, 14, 62))}
W = int(os.environ.get('RES', 800)); sc.cycles.samples = int(os.environ.get('SAMPLES', 32))
bc.inputs[0].default_value = (0.004, 0.004, 0.007, 1); sc.view_settings.exposure = 1.1; bc.inputs[1].default_value = 1 / (2 ** 1.1)
for k, (loc, tgt) in C.items():
    c = rc.cam(sc, 'C_' + k, loc, tgt, lens=50); sc.camera = c; sc.render.resolution_x = W; sc.render.resolution_y = int(W * 0.75)
    sc.render.filepath = f'{OUT}/{k}.png'; bpy.ops.render.render(write_still=True); print('RENDERED', k, flush=True)
