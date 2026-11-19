# v11 stage D (blender): B.blend (displaced 196k low, custom normals) + v11 maps -> materials, exact box refit, measure,
# model.blend / model.glb, sheet renders (same cameras / lights as v9-v10)
import bpy, os, sys, json, numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H); import rend_common as rc
C = os.environ.get('V11_CACHE', '/tmp/v11'); ROOT = '/workspace/outputs/black_hole_structure'; TEX = ROOT + '/tex'
OUT_R = os.environ.get('OUT_R', ROOT + '/renders'); env = lambda k, d: float(os.environ.get(k, d))
bpy.ops.wm.open_mainfile(filepath=C + '/B.blend'); scene = bpy.context.scene
_is = scene.render.image_settings; _is.color_management = 'FOLLOW_SCENE'; _is.color_depth = '8'  # stage B may leave a 16-bit Raw override from the col2 bake
ob = bpy.data.objects['BlackHole_Structure']; me = ob.data
BOX = np.array([100.0, 48.0, 120.0]); HC = np.array([0.0, 58.0])
def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def getco(o): c = np.zeros(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get('co', c); return c.reshape(-1, 3).astype(np.float64)
def fit_box(c):
    lo0 = np.array([-BOX[0] / 2, -BOX[1] / 2, 0.0]); hi0 = np.array([BOX[0] / 2, BOX[1] / 2, BOX[2]])
    l1, h1 = c.min(0), c.max(0); d = lo0 + (c - l1) * (hi0 - lo0) / (h1 - l1) - c
    r = np.hypot(c[:, 0] - HC[0], c[:, 2] - HC[1]); w = sstep(24.0, 40.0, r)
    c = c + d * w[:, None]; l2, h2 = c.min(0), c.max(0); return lo0 + (c - l2) * (hi0 - lo0) / (h2 - l2)
c = fit_box(getco(ob)); me.vertices.foreach_set('co', c.astype(np.float32).ravel()); me.update()
# ---- materials (rebuilt; names kept so the web viewer's per-material tweaks apply)
def img(name, nc=False):
    im = bpy.data.images.load(TEX + '/' + name, check_existing=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    return im
TAG = os.environ.get('TAG', 'v11')
ALB, MR, NRM, AO, EMI = img(TAG + '_albedo.jpg'), img(TAG + '_mr.jpg', True), img(TAG + '_normal.jpg', True), img(TAG + '_ao.jpg', True), img(TAG + '_glow_emit.jpg')
grp = bpy.data.node_groups.get('glTF Material Output') or bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
if not grp.interface.items_tree: grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
def T(nt, im): t = nt.nodes.new('ShaderNodeTexImage'); t.image = im; return t
def pbr(name, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    a = T(nt, ALB); r = T(nt, MR); sp = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(r.outputs['Color'], sp.inputs['Color'])
    nt.links.new(sp.outputs['Green'], b.inputs['Roughness']); nt.links.new(sp.outputs['Blue'], b.inputs['Metallic'])
    n = T(nt, NRM); nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = env('NSTR', 1.0)
    nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    o = T(nt, AO); so = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(o.outputs['Color'], so.inputs['Color'])
    g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = grp; nt.links.new(so.outputs['Red'], g.inputs['Occlusion'])
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = env('AO_STR', 0.9)
    nt.links.new(a.outputs['Color'], mul.inputs['A']); nt.links.new(o.outputs['Color'], mul.inputs['B']); nt.links.new(mul.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Specular IOR Level'].default_value = env('SPEC', 0.55)
    if emit is not None:
        b.inputs['Specular IOR Level'].default_value = env('GSPEC', 0.05)      # funnel: no grey/lavender sheen, light comes from the streaks
        e = T(nt, emit); nt.links.new(e.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = estr
    return m
old = [m for m in me.materials]
for m in old: m.name = m.name + '_v10old'   # free the names: the web viewer keys its tweaks on BH_Skin_Bronze / BH_Glow_Rim / BH_Core_Black
mats = [pbr('BH_Skin_Bronze'), pbr('BH_Glow_Rim', EMI, env('GLOW', 2.2))]
core = bpy.data.materials.new('BH_Core_Black'); core.use_nodes = True; cb = core.node_tree.nodes['Principled BSDF']
cb.inputs['Base Color'].default_value = (0, 0, 0, 1); cb.inputs['Roughness'].default_value = 1; cb.inputs['Specular IOR Level'].default_value = 0
for i, m in enumerate(mats + [core]): me.materials[i] = m
for m in old:
    if m.users == 0: bpy.data.materials.remove(m)
for m in [m_ for m_ in bpy.data.materials if m_.users == 0]: bpy.data.materials.remove(m)
for im in [i for i in bpy.data.images if i.users == 0 or i.packed_file]: bpy.data.images.remove(im)
# ---- measure
V = getco(ob); lo, hi = V.min(0), V.max(0)
fmi = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('material_index', fmi)
fv = np.zeros(len(me.polygons) * 3, np.int32); me.polygons.foreach_get('vertices', fv); fv = fv.reshape(-1, 3)
cv = np.unique(fv[fmi == 2].ravel()); Cc = V[cv]; hc = [0.5 * (Cc[:, 0].min() + Cc[:, 0].max()), float(np.median(Cc[:, 1])), 0.5 * (Cc[:, 2].min() + Cc[:, 2].max())]
info = json.load(open(C + '/infoA.json')); info.update(version=TAG, tris=len(me.polygons), verts=len(me.vertices), bbox_size=(hi - lo).tolist(), bbox_min=lo.tolist(), bbox_max=hi.tolist(),
                                                     hole_centre=[float(x) for x in hc], scales=json.load(open(C + '/field.json')))
json.dump(info, open(ROOT + '/measure.json', 'w'), indent=1, default=float); print('MEASURE', info['tris'], info['bbox_size'], hc, flush=True)
if os.environ.get('SAVE', '1') == '1':
    bpy.ops.wm.save_as_mainfile(filepath=ROOT + '/model.blend', compress=True)
    for o in scene.objects: o.select_set(o == ob)
    bpy.ops.export_scene.gltf(filepath=ROOT + '/model.glb', export_format='GLB', use_selection=True, export_apply=True, export_lights=False, export_cameras=False,
                              export_image_format='AUTO', export_yup=True, export_vertex_color='NONE')
    print('EXPORTED', os.path.getsize(ROOT + '/model.glb'), flush=True)
bc = rc.setup(scene, hole=(hc[0], hc[1] - 6, hc[2]), hole_w=env('HOLE_W', 300), key=env('KEY', 6.5))
if 'Rim_Sun' in bpy.data.objects: bpy.data.objects['Rim_Sun'].data.energy = env('RIM', 2.4); bpy.data.objects['Rim_Sun'].data.color = (env('RIM_R', 0.80), env('RIM_G', 0.62), 1.0)
for l in ('Key_Sun', 'Rim_Sun'):
    if l in bpy.data.objects: bpy.data.objects[l].data.angle = np.radians(env('SUN_ANGLE', 2.0))   # crisper speculars on scale edges
views = rc.views(scene, hc=(hc[0], lo[1] + 4, hc[2]))
if os.environ.get('RENDER', '1') == '1':
    only = os.environ.get('ONLY'); rc.render(scene, bc, views, OUT_R, only=only.split(',') if only else None, samples=int(env('SAMPLES', 48)),
                                              expo=env('EXPO', 0.95), expo_hero=env('EXPO_HERO', 1.1))
