# Blender scene: mesh from build.compute(), PBR materials, cameras (orthographic sheet views + hero), model.blend / model.glb, renders
import bpy, math, os, sys, json, numpy as np
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__))
import build
ROOT = build.ROOT; TEX = build.TEX; OUT_R = ROOT + '/renders'
os.makedirs(OUT_R, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def img(name, noncolor=False):
    im = bpy.data.images.load(os.path.join(TEX, name + '.png'), check_existing=True)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    return im

def mat_skin(name, vein=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img('skin_albedo')
    r = nt.nodes.new('ShaderNodeTexImage'); r.image = img('skin_rough', True)
    n = nt.nodes.new('ShaderNodeTexImage'); n.image = img('skin_normal', True)
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 2.0
    ca = nt.nodes.new('ShaderNodeVertexColor'); ca.layer_name = 'Tint'        # copper on ridge edges / purple in crevices
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
    dz = nt.nodes.new('ShaderNodeMix'); dz.data_type = 'RGBA'; dz.blend_type = 'MIX'          # soften the copper tint (only crests stay warm)
    dz.inputs['Factor'].default_value = float(os.environ.get('TINT_SOFT', 0.5)); dz.inputs['B'].default_value = (0.80, 0.66, 0.70, 1)
    nt.links.new(ca.outputs['Color'], dz.inputs['A'])
    nt.links.new(t.outputs['Color'], mx.inputs['A']); nt.links.new(dz.outputs['Result'], mx.inputs['B'])
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'Cav'           # deep crevices -> plum diffuse (no emission)
    cm = nt.nodes.new('ShaderNodeMath'); cm.operation = 'MULTIPLY_ADD'; cm.use_clamp = True
    cm.inputs[1].default_value = float(os.environ.get('PLUM', 3.0)); cm.inputs[2].default_value = float(os.environ.get('PLUM_OFF', -0.2))
    nt.links.new(at.outputs['Fac'], cm.inputs[0])
    mp = nt.nodes.new('ShaderNodeMix'); mp.data_type = 'RGBA'; mp.blend_type = 'MIX'
    nt.links.new(cm.outputs['Value'], mp.inputs['Factor']); nt.links.new(mx.outputs['Result'], mp.inputs['A'])
    mp.inputs['B'].default_value = (0.11, 0.025, 0.20, 1)
    nt.links.new(mp.outputs['Result'], b.inputs['Base Color'])
    if 'Thin Film Thickness' in b.inputs:
        b.inputs['Thin Film Thickness'].default_value = float(os.environ.get('FILM', 0)); b.inputs['Thin Film IOR'].default_value = 1.45   # purple/green iridescent sheen
    nt.links.new(r.outputs['Color'], b.inputs['Roughness'])
    nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Metallic'].default_value = float(os.environ.get('METAL', 0.55))     # dark bronze: semi-metallic organic
    b.inputs['Specular IOR Level'].default_value = 0.4
    b.inputs['Specular Tint'].default_value = (*build.srgb2lin((205, 165, 140)), 1)
    if vein:
        e = nt.nodes.new('ShaderNodeTexImage'); e.image = img('skin_vein')
        nt.links.new(e.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = 0.8
    return m

def mat_glow():
    m = bpy.data.materials.new('BH_Glow_Rim'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    a = nt.nodes.new('ShaderNodeTexImage'); a.image = img('glow_albedo')
    e = nt.nodes.new('ShaderNodeTexImage'); e.image = img('glow_emit')
    n = nt.nodes.new('ShaderNodeTexImage'); n.image = img('skin_normal', True)
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.6
    nt.links.new(a.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(e.outputs['Color'], b.inputs['Emission Color'])
    nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Emission Strength'].default_value = float(os.environ.get('GLOW', 2.4))
    b.inputs['Roughness'].default_value = 0.65; b.inputs['Metallic'].default_value = 0.0
    b.inputs['Specular IOR Level'].default_value = 0.03                     # no grey sheen on the funnel wall
    return m

def mat_core():
    m = bpy.data.materials.new('BH_Core_Black'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1); b.inputs['Roughness'].default_value = 1.0
    b.inputs['Specular IOR Level'].default_value = 0.0
    return m

def mat_pore(name, glow=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    n = nt.nodes.new('ShaderNodeTexImage'); n.image = img('skin_normal', True)
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 1.0
    nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if glow:
        b.inputs['Base Color'].default_value = (0.05, 0.004, 0.08, 1)
        b.inputs['Emission Color'].default_value = (*build.srgb2lin((190, 50, 255)), 1)
        b.inputs['Emission Strength'].default_value = 1.3
    else:
        b.inputs['Base Color'].default_value = (0.008, 0.0025, 0.009, 1)    # near-black plum socket
    b.inputs['Roughness'].default_value = 0.95 if not glow else 0.6; b.inputs['Metallic'].default_value = 0.0 if not glow else 0.3
    b.inputs['Specular IOR Level'].default_value = 0.04 if not glow else 0.3                # non-reflective sockets: no grey sheen
    return m

def mat_rim():
    m = mat_skin('BH_Rim_Wear'); b = m.node_tree.nodes['Principled BSDF']
    t = [n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image.name.startswith('skin_albedo')][0]
    mix = m.node_tree.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1.0
    mix.inputs['B'].default_value = (1.7, 1.15, 0.9, 1)              # brighter worn copper/rust on rims
    m.node_tree.links.new(t.outputs['Color'], mix.inputs['A']); m.node_tree.links.new(mix.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Metallic'].default_value = 0.85
    return m

MATS = [mat_skin('BH_Skin_Bronze'), mat_skin('BH_Skin_Vein', True), mat_glow(), mat_core(), mat_pore('BH_Pore_Dark'), mat_pore('BH_Pore_Glow', True), mat_rim()]

import hashlib, pickle
_h = hashlib.md5(open(os.path.join(os.path.dirname(__file__), 'build.py'), 'rb').read()).hexdigest()
_cache = f'/tmp/bh_mesh_{_h}.pkl'
if os.path.exists(_cache):
    V, F, FM, UV, info = pickle.load(open(_cache, 'rb')); print('mesh from cache', _cache)
else:
    V, F, FM, UV, info = build.compute(); pickle.dump((V, F, FM, UV, info), open(_cache, 'wb'))
VCOL = info.pop('_vcol'); VCAV = info.pop('_vcav')
me = bpy.data.meshes.new('BlackHole_Structure')
me.vertices.add(len(V)); me.vertices.foreach_set('co', V.astype(np.float32).ravel())
me.loops.add(F.size); me.loops.foreach_set('vertex_index', F.astype(np.int32).ravel())
me.polygons.add(len(F)); me.polygons.foreach_set('loop_start', (np.arange(len(F)) * 3).astype(np.int32))
me.update(calc_edges=True)
for m in MATS: me.materials.append(m)
me.polygons.foreach_set('material_index', FM.astype(np.int32))
uvl = me.uv_layers.new(name='UVMap'); uvl.data.foreach_set('uv', UV[F.ravel()].astype(np.float32).ravel())
me.polygons.foreach_set('use_smooth', np.ones(len(F), bool))
ca = me.color_attributes.new('Tint', 'FLOAT_COLOR', 'POINT')
ca.data.foreach_set('color', np.c_[VCOL, np.ones(len(VCOL), np.float32)].astype(np.float32).ravel())
me.color_attributes.active_color = ca
cv = me.attributes.new('Cav', 'FLOAT', 'POINT'); cv.data.foreach_set('value', np.clip(VCAV, 0, 1).astype(np.float32) * 0.5)
me.validate(); me.update()
ob = bpy.data.objects.new('BlackHole_Structure', me); scene.collection.objects.link(ob)
# v7: collapse-decimate 2.48M -> ≤200k tris (default 0.08 ≈ 198.6k), protect hole, bake detail normals from a mid-poly source
DEC = float(os.environ.get('DECIMATE', 0.08)); info['tris_full'] = len(me.polygons)
BAKE = os.environ.get('BAKE_NORMALS', '1') == '1'
BAKE_SRC = float(os.environ.get('BAKE_SRC', '0.2'))   # mid-poly bake source (v6 density); 1.0 = full 2.48M
BAKE_RES = int(os.environ.get('BAKE_RES', '1024'))
if DEC < 1.0:
    lo0, hi0 = V.min(0), V.max(0)
    keep = np.unique(F[(FM == build.MAT_GLOW) | (FM == build.MAT_CORE)].ravel())
    def _decimate(target, ratio, tag):
        vg_name = 'BH_KeepHole_' + tag
        vg = target.vertex_groups.new(name=vg_name)
        vg.add(keep.tolist(), 1.0, 'REPLACE')
        md = target.modifiers.new('Decimate_' + tag, 'DECIMATE')
        md.decimate_type = 'COLLAPSE'; md.ratio = ratio; md.use_collapse_triangulate = True
        md.vertex_group = vg_name; md.invert_vertex_group = True; md.vertex_group_factor = 10.0
        bpy.context.view_layer.objects.active = target; bpy.ops.object.modifier_apply(modifier=md.name)
        # modifier_apply invalidates the vg RNA pointer — remove by name if it still exists
        g = target.vertex_groups.get(vg_name)
        if g is not None:
            target.vertex_groups.remove(g)
        return target.data
    # mid-poly bake source (keeps pore/ridge detail that ≤200k can no longer carry as geometry)
    hi_ob = None
    if BAKE and BAKE_SRC < 1.0:
        hi_me = me.copy(); hi_ob = bpy.data.objects.new('BH_BakeSrc', hi_me); scene.collection.objects.link(hi_ob)
        _decimate(hi_ob, BAKE_SRC, 'src'); print('BAKE_SRC tris', len(hi_ob.data.polygons), flush=True)
    elif BAKE:
        hi_ob = bpy.data.objects.new('BH_BakeSrc', me.copy()); scene.collection.objects.link(hi_ob)
    _decimate(ob, DEC, 'low'); me = ob.data
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3).astype(np.float64)
    lo1, hi1 = co.min(0), co.max(0); co = lo0 + (co - lo1) * (hi0 - lo0) / (hi1 - lo1)
    me.vertices.foreach_set('co', co.astype(np.float32).ravel()); me.update()
    if hi_ob is not None:  # same world-space fit so cage rays line up
        hc = np.zeros(len(hi_ob.data.vertices) * 3, np.float32); hi_ob.data.vertices.foreach_get('co', hc); hc = hc.reshape(-1, 3).astype(np.float64)
        hlo, hhi = hc.min(0), hc.max(0); hc = lo0 + (hc - hlo) * (hi0 - lo0) / (hhi - hlo)
        hi_ob.data.vertices.foreach_set('co', hc.astype(np.float32).ravel()); hi_ob.data.update()
    info['decimate'] = dict(ratio=DEC, bake_src=BAKE_SRC if BAKE else None, drift_before_refit=np.r_[lo1 - lo0, hi1 - hi0].round(4).tolist())
    Fd = np.zeros(len(me.polygons) * 3, np.int32); me.polygons.foreach_get('vertices', Fd)
    FMd = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('material_index', FMd)
    pickle.dump((co, Fd.reshape(-1, 3), FMd), open(f'/tmp/bh_dec_{_h}_{DEC}.pkl', 'wb'))
    if BAKE and hi_ob is not None:
        if 'BakeUV' in me.uv_layers: me.uv_layers.remove(me.uv_layers['BakeUV'])
        bake_uv = me.uv_layers.new(name='BakeUV'); me.uv_layers.active = bake_uv
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=0.002, correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        baked = bpy.data.images.new('BH_BakedDetailN', BAKE_RES, BAKE_RES, alpha=False); baked.colorspace_settings.name = 'Non-Color'
        for mat in me.materials:
            if not mat or not mat.use_nodes: continue
            nt = mat.node_tree; node = nt.nodes.new('ShaderNodeTexImage'); node.image = baked; node.name = 'BAKE_TARGET'
            for n in nt.nodes: n.select = False
            node.select = True; nt.nodes.active = node
        scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = int(os.environ.get('BAKE_SAMPLES', '8'))
        scene.cycles.bake_type = 'NORMAL'
        scene.render.bake.normal_space = 'TANGENT'
        scene.render.bake.use_selected_to_active = True
        scene.render.bake.use_cage = False
        scene.render.bake.cage_extrusion = float(os.environ.get('BAKE_CAGE', '0.8'))
        scene.render.bake.max_ray_distance = float(os.environ.get('BAKE_RAY', '2.0'))
        scene.render.bake.margin = 8; scene.render.bake.use_clear = True
        bpy.ops.object.select_all(action='DESELECT'); hi_ob.select_set(True); ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        print('BAKE start', BAKE_RES, 'from', len(hi_ob.data.polygons), 'to', len(me.polygons), flush=True)
        bpy.ops.object.bake(type='NORMAL'); print('BAKE done', flush=True)
        out_n = os.path.join(TEX, 'baked_detail_n.png'); baked.filepath_raw = out_n; baked.file_format = 'PNG'; baked.save()
        print('BAKE saved', out_n, flush=True)
        # wire baked normal (BakeUV) as primary; keep a light mix of tiled procedural micro-normal
        for mat in me.materials:
            if not mat or not mat.use_nodes: continue
            if not (mat.name.startswith('BH_Skin') or mat.name in ('BH_Rim_Wear', 'BH_Pore_Dark', 'BH_Pore_Glow')): continue
            nt = mat.node_tree; nm = next((n for n in nt.nodes if n.type == 'NORMAL_MAP'), None)
            if nm is None: continue
            uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'BakeUV'; uv.location = (-700, -200)
            bn = nt.nodes.new('ShaderNodeTexImage'); bn.image = baked; bn.location = (-500, -200)
            bn.image.colorspace_settings.name = 'Non-Color'
            nt.links.new(uv.outputs['UV'], bn.inputs['Vector'])
            # mix baked (A) with existing procedural normal colour (B) so micro-grain remains
            mxn = nt.nodes.new('ShaderNodeMix'); mxn.data_type = 'RGBA'; mxn.blend_type = 'MIX'
            mxn.inputs['Factor'].default_value = float(os.environ.get('BAKE_MIX', '0.78')); mxn.location = (-280, -100)
            nt.links.new(bn.outputs['Color'], mxn.inputs['A'])
            old_col = nm.inputs['Color'].links[0].from_socket if nm.inputs['Color'].links else None
            if old_col is not None: nt.links.new(old_col, mxn.inputs['B'])
            else: mxn.inputs['B'].default_value = (0.5, 0.5, 1.0, 1)
            for l in list(nm.inputs['Color'].links): nt.links.remove(l)
            nt.links.new(mxn.outputs['Result'], nm.inputs['Color'])
            nm.inputs['Strength'].default_value = float(os.environ.get('NSTR', '2.6'))
            tgt = nt.nodes.get('BAKE_TARGET')
            if tgt: nt.nodes.remove(tgt)
        me.uv_layers.active = me.uv_layers['UVMap']
        bpy.data.objects.remove(hi_ob, do_unlink=True); info['baked_normal'] = out_n
co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
lo, hi = co.min(0), co.max(0)
info.update(bbox_min=lo.tolist(), bbox_max=hi.tolist(), bbox_size=(hi - lo).tolist(), tris=len(me.polygons), verts=len(me.vertices))
print('BBOX', lo, hi, hi - lo, 'TRIS', len(me.polygons))
json.dump(info, open(ROOT + '/measure.json', 'w'), indent=1, default=float)

# ---------------- world / lights ----------------
DARK = os.environ.get('BG', 'sheet') == 'dark'
world = bpy.data.worlds.new('World'); scene.world = world; world.use_nodes = True
nt = world.node_tree; nt.nodes.clear()
lp = nt.nodes.new('ShaderNodeLightPath')
bg_l = nt.nodes.new('ShaderNodeBackground'); bg_l.inputs[0].default_value = (0.55, 0.48, 0.52, 1); bg_l.inputs[1].default_value = 0.35
bg_c = nt.nodes.new('ShaderNodeBackground'); bg_c.name = 'CamBG'
bg_c.inputs[0].default_value = (*build.srgb2lin((236, 230, 219)), 1); bg_c.inputs[1].default_value = 1.0
mix = nt.nodes.new('ShaderNodeMixShader'); out = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0]); nt.links.new(bg_l.outputs[0], mix.inputs[1]); nt.links.new(bg_c.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], out.inputs[0])

def add_light(name, typ, loc, rot, energy, color=(1, 1, 1), size=None):
    ld = bpy.data.lights.new(name, typ); ld.energy = energy; ld.color = color
    if typ == 'SUN': ld.angle = math.radians(4)
    if size and typ in ('AREA',): ld.size = size
    if size and typ == 'POINT': ld.shadow_soft_size = size
    lo_ = bpy.data.objects.new(name, ld); lo_.location = loc; lo_.rotation_euler = rot
    scene.collection.objects.link(lo_); return lo_
add_light('Key_Sun', 'SUN', (0, 0, 150), (math.radians(50), 0, math.radians(-30)), float(os.environ.get('KEY', 6.5)), (1.0, 0.90, 0.78))
add_light('Rim_Sun', 'SUN', (0, 0, 150), (math.radians(60), 0, math.radians(150)), 2.4, (0.80, 0.62, 1.0))
hc = info['hole_centre']
add_light('Hole_Glow', 'POINT', (hc[0], hc[1] - 2, hc[2]), (0, 0, 0), float(os.environ.get('HOLE_W', 2500)), build.srgb2lin((200, 60, 255)), 6)

scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'; scene.cycles.samples = int(os.environ.get('SAMPLES', 48))
scene.cycles.use_denoising = True; scene.cycles.max_bounces = 4
scene.view_settings.view_transform = os.environ.get('VT', 'Standard'); scene.view_settings.look = 'None'

def cam(name, loc, target, ortho=None, lens=50):
    cd = bpy.data.cameras.new(name)
    if ortho: cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else: cd.lens = lens
    cd.clip_end = 2000
    c = bpy.data.objects.new(name, cd); c.location = loc; scene.collection.objects.link(c)
    d = Vector(target) - Vector(loc)
    up = 'Y'
    c.rotation_euler = d.to_track_quat('-Z', up).to_euler()
    return c
mid = (0, 0, 60)
views = {
 'front': (cam('Cam_Front', (0, -300, 60), mid, ortho=132), (900, 900)),
 'rear':  (cam('Cam_Rear', (0, 300, 60), mid, ortho=132), (900, 900)),
 'left':  (cam('Cam_Left', (-300, 0, 60), mid, ortho=132), (900, 900)),
 'right': (cam('Cam_Right', (300, 0, 60), mid, ortho=132), (900, 900)),
 'top':   (cam('Cam_Top', (0, -0.001, 400), (0, 0, 0), ortho=112), (900, 900)),
 'axo':   (cam('Cam_Axo', (-170, -300, 230), (0, 0, 58), ortho=150), (900, 900)),
 'hero':  (cam('Cam_Hero', (-120, -205, 42), (2, 0, 58), lens=40), (1600, 1000)),
 'closeup': (cam('Cam_Closeup', (hc[0] - 48, hc[1] - 70, hc[2] + 30), (hc[0] - 18, hc[1] - 2, hc[2] + 10), lens=45), (1600, 1000)),
}
bpy.ops.wm.save_as_mainfile(filepath=ROOT + '/model.blend')

# GLB (geometry + materials only)
for o in scene.objects: o.select_set(o.type == 'MESH')
GLB_OUT = ROOT + ('/model.glb' if DEC < 1.0 else '/model_full.glb')   # full-res (~112 MB) never overwrites the committed decimated model.glb
bpy.ops.export_scene.gltf(filepath=GLB_OUT, export_format='GLB', use_selection=True, export_apply=True,
                          export_lights=False, export_cameras=False, export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_image_format='AUTO', export_yup=True)
print('EXPORTED', GLB_OUT, os.path.getsize(GLB_OUT))

if os.environ.get('RENDER', '1') == '1':
    only = os.environ.get('ONLY')
    for k, (c, (w, h)) in views.items():
        if only and k not in only.split(','): continue
        dark = (k in ('hero', 'closeup')) or DARK
        bg_c.inputs[0].default_value = (0.004, 0.004, 0.007, 1) if dark else (*build.srgb2lin((236, 230, 219)), 1)
        scene.view_settings.exposure = float(os.environ.get('EXPO_HERO', 1.1)) if k in ('hero', 'closeup') else float(os.environ.get('EXPO', 0.95))
        bg_c.inputs[1].default_value = 1.0 / (2 ** scene.view_settings.exposure)   # keep the sheet-beige background after exposure
        scene.camera = c; scene.render.resolution_x = w; scene.render.resolution_y = h
        scene.render.filepath = os.path.join(OUT_R, f'{k}.png')
        bpy.ops.render.render(write_still=True)
        print('RENDERED', k, flush=True)
