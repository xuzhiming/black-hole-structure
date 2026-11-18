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
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 2.2
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
        b.inputs['Emission Strength'].default_value = float(os.environ.get('PORE_GLOW', 0.7))   # v9: softer purple glints
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
VCOL = info.pop('_vcol'); VCAV = info.pop('_vcav'); SMOOTH = info.pop('_smooth', None)
def make_obj(name, V, F, FM, UV, VCOL, VCAV):
    me = bpy.data.meshes.new(name)
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
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o)
    return o
SPLIT = SMOOTH is not None and float(os.environ.get('DECIMATE', 0.08)) < 1.0
if SPLIT:
    # v9: display mesh = smooth (pore-free) build; pore mesh = bake source for detail normals + AO
    ob = make_obj('BlackHole_Structure', *SMOOTH); me = ob.data
    pore_ob = make_obj('BH_BakeSrc', V, F, FM, UV, VCOL, VCAV)
    print('SPLIT smooth', len(me.polygons), 'pore src', len(pore_ob.data.polygons), flush=True)
else:
    ob = make_obj('BlackHole_Structure', V, F, FM, UV, VCOL, VCAV); me = ob.data; pore_ob = None
# v9: new large-scale geometry; ≤200k via 2-pass decimate (gentle funnel/core pass + body pass) + v8 weld/smooth/custom normals/bake
DEC = float(os.environ.get('DECIMATE', 0.08)); info['tris_full'] = len(me.polygons)
BAKE = os.environ.get('BAKE_NORMALS', '1') == '1'
BAKE_SRC = float(os.environ.get('BAKE_SRC', '0.3'))  # denser mid-poly bake source (~620k); 1.0 = full 2.48M
BAKE_RES = int(os.environ.get('BAKE_RES', '1024'))
if DEC < 1.0:
    lo0, hi0 = np.array([-build.BBOX[0] / 2, -build.BBOX[1] / 2, 0.0]), np.array([build.BBOX[0] / 2, build.BBOX[1] / 2, build.BBOX[2]])
    def fit_box(c):
        """v9: stretch to the exact 100x48x120 box, but fade the stretch out around the opening (r<24 m untouched) so the
        hole centre / Ø26 / recess stay on spec; a final tiny affine pass catches any extreme lying inside the fade zone"""
        l1, h1 = c.min(0), c.max(0); d = lo0 + (c - l1) * (hi0 - lo0) / (h1 - l1) - c
        r = np.hypot(c[:, 0] - 0.0, c[:, 2] - build.HC_Z); t = np.clip((r - 24.0) / 16.0, 0, 1); w = t * t * (3 - 2 * t)
        c = c + d * w[:, None]
        l2, h2 = c.min(0), c.max(0); return lo0 + (c - l2) * (hi0 - lo0) / (h2 - l2), l1, h1
    def _hole_verts(target):
        mm = target.data; fmi = np.zeros(len(mm.polygons), np.int32); mm.polygons.foreach_get('material_index', fmi)
        fv = np.zeros(len(mm.polygons) * 3, np.int32); mm.polygons.foreach_get('vertices', fv); fv = fv.reshape(-1, 3)
        hv = np.unique(fv[(fmi == build.MAT_GLOW) | (fmi == build.MAT_CORE)].ravel())
        return hv, int(((fmi == build.MAT_GLOW) | (fmi == build.MAT_CORE)).sum()), len(mm.vertices)
    def _decimate(target, ratio, tag, protect='hole'):
        """collapse-decimate with a protected vertex group: protect='hole' keeps the funnel/core, 'body' keeps everything else"""
        hv, _, nv = _hole_verts(target)
        if protect == 'body':
            m_ = np.ones(nv, bool); m_[hv] = False
            # v9: also keep the Ø26 core mouth edge (glow↔core seam) exact during the gentle hole pass
            mm = target.data; fmi = np.zeros(len(mm.polygons), np.int32); mm.polygons.foreach_get('material_index', fmi)
            fv = np.zeros(len(mm.polygons) * 3, np.int32); mm.polygons.foreach_get('vertices', fv); fv = fv.reshape(-1, 3)
            cvx = np.unique(fv[fmi == build.MAT_CORE].ravel()); gvx = np.unique(fv[fmi == build.MAT_GLOW].ravel())
            m_[np.intersect1d(cvx, gvx)] = True
            co_ = np.zeros(nv * 3, np.float32); mm.vertices.foreach_get('co', co_); co_ = co_.reshape(-1, 3)
            yq = np.percentile(co_[cvx, 1], 10); m_[cvx[co_[cvx, 1] < yq + 1.5]] = True
            hv = np.where(m_)[0]
        vg_name = 'BH_Keep_' + tag
        vg = target.vertex_groups.new(name=vg_name)
        vg.add(hv.tolist(), 1.0, 'REPLACE')
        md = target.modifiers.new('Decimate_' + tag, 'DECIMATE')
        md.decimate_type = 'COLLAPSE'; md.ratio = float(np.clip(ratio, 0.001, 1.0)); md.use_collapse_triangulate = True
        md.vertex_group = vg_name; md.invert_vertex_group = True; md.vertex_group_factor = 10.0
        bpy.context.view_layer.objects.active = target; bpy.ops.object.modifier_apply(modifier=md.name)
        g = target.vertex_groups.get(vg_name)
        if g is not None:
            target.vertex_groups.remove(g)
        return target.data
    TRI_TARGET = int(os.environ.get('TRI_TARGET', '196000')); HOLE_KEEP = float(os.environ.get('HOLE_KEEP', '0.42'))
    def _to_target(target, total, tag):
        """v9: funnel/core get a gentle own pass (they were 127k of the 200k budget in v8), then the rest goes to the target"""
        _, nh, _ = _hole_verts(target); n0 = len(target.data.polygons)
        if HOLE_KEEP < 1.0 and nh > 0:
            _decimate(target, (n0 - nh * (1 - HOLE_KEEP)) / n0, tag + 'h', protect='body')
        n1 = len(target.data.polygons)
        _decimate(target, total / n1, tag, protect='hole')
        print('DECIMATE', tag, n0, '->', n1, '->', len(target.data.polygons), flush=True)
        return target.data
    # mid-poly bake source (keeps pore/ridge detail that ≤200k can no longer carry as geometry)
    hi_ob = None; nrm_src = None
    if SPLIT:
        hi_ob = pore_ob                                           # bake source: full-res pore mesh
        nrm_src = bpy.data.objects.new('BH_NormSrc', me.copy()); scene.collection.objects.link(nrm_src)   # dense smooth copy -> custom normals
        if not BAKE: bpy.data.objects.remove(hi_ob, do_unlink=True); hi_ob = None
    elif BAKE and BAKE_SRC < 1.0:
        hi_me = me.copy(); hi_ob = bpy.data.objects.new('BH_BakeSrc', hi_me); scene.collection.objects.link(hi_ob)
        _decimate(hi_ob, BAKE_SRC, 'src'); print('BAKE_SRC tris', len(hi_ob.data.polygons), flush=True)   # hole kept dense in the bake source
    elif BAKE:
        hi_ob = bpy.data.objects.new('BH_BakeSrc', me.copy()); scene.collection.objects.link(hi_ob)
    _to_target(ob, TRI_TARGET, 'low'); me = ob.data
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3).astype(np.float64)
    co, lo1, hi1 = fit_box(co)
    me.vertices.foreach_set('co', co.astype(np.float32).ravel()); me.update()
    for _o in [x for x in (nrm_src,) if x is not None]:
        _c = np.zeros(len(_o.data.vertices) * 3, np.float32); _o.data.vertices.foreach_get('co', _c); _c = _c.reshape(-1, 3).astype(np.float64)
        _c = fit_box(_c)[0]; _o.data.vertices.foreach_set('co', _c.astype(np.float32).ravel()); _o.data.update()
    if hi_ob is not None:  # same world-space fit so cage rays line up
        hc = np.zeros(len(hi_ob.data.vertices) * 3, np.float32); hi_ob.data.vertices.foreach_get('co', hc); hc = hc.reshape(-1, 3).astype(np.float64)
        hlo, hhi = hc.min(0), hc.max(0); hc = lo0 + (hc - hlo) * (hi0 - lo0) / (hhi - hlo)
        hi_ob.data.vertices.foreach_set('co', hc.astype(np.float32).ravel()); hi_ob.data.update()
    info['decimate'] = dict(ratio=DEC, bake_src=BAKE_SRC if BAKE else None, drift_before_refit=np.r_[lo1 - lo0, hi1 - hi0].round(4).tolist())
    Fd = np.zeros(len(me.polygons) * 3, np.int32); me.polygons.foreach_get('vertices', Fd)
    FMd = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('material_index', FMd)
    pickle.dump((co, Fd.reshape(-1, 3), FMd), open(f'/tmp/bh_dec_{_h}_{DEC}.pkl', 'wb'))
    # --- v8: kill origami --- the protected funnel/core (and some body strips) were built with
    # nearly-unshared verts, so each triangle carried a face normal (= flat / 折纸 shading).
    # Merge-by-distance welds them; shade_smooth + clear custom normals give continuous averaged normals.
    def _weld_smooth(obj, dist=None):
        dist = float(os.environ.get('WELD', '0.002')) if dist is None else dist
        bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=dist)
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.shade_smooth()
        # Blender 4.x: no use_auto_smooth; clear any custom split normals left by modifiers
        try:
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        except Exception:
            pass
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.data.update()
        return obj.data
    me = _weld_smooth(ob); print('AFTER_WELD tris', len(me.polygons), 'verts', len(me.vertices), flush=True)
    if nrm_src is not None: _weld_smooth(nrm_src)
    if hi_ob is not None:
        _weld_smooth(hi_ob); print('BAKE_SRC after weld tris', len(hi_ob.data.polygons), flush=True)
        # Transfer high-poly shading onto low-poly as CUSTOM normals. This is the main anti-origami
        # fix: large facets keep smooth continuous lighting as if the mid-poly surface were still there.
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        xfer = ob.modifiers.new('NormXfer', 'DATA_TRANSFER')
        xfer.object = nrm_src if nrm_src is not None else hi_ob
        xfer.use_loop_data = True
        xfer.data_types_loops = {'CUSTOM_NORMAL'}
        xfer.loop_mapping = 'NEAREST_POLYNOR'
        xfer.use_max_distance = True
        xfer.max_distance = float(os.environ.get('XFER_DIST', '1.5'))
        xfer.loop_mapping = 'POLYINTERP_NEAREST'
        bpy.ops.object.modifier_apply(modifier='NormXfer')
        if nrm_src is not None: bpy.data.objects.remove(nrm_src, do_unlink=True)
        print('CUSTOM_NORMALS', ob.data.has_custom_normals, flush=True)
    # refresh verify cache after weld (tri count may drop slightly)
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3).astype(np.float64)
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
        # v9: AO from the pore mesh -> dark pore sockets / crevice depth on the smooth display mesh
        baked_ao = None
        if os.environ.get('BAKE_AO', '1') == '1':
            baked_ao = bpy.data.images.new('BH_BakedAO', BAKE_RES, BAKE_RES, alpha=False); baked_ao.colorspace_settings.name = 'Non-Color'
            for mat in me.materials:
                if mat and mat.use_nodes and mat.node_tree.nodes.get('BAKE_TARGET'):
                    t_ = mat.node_tree.nodes['BAKE_TARGET']; t_.image = baked_ao; mat.node_tree.nodes.active = t_
            if scene.world: scene.world.light_settings.distance = float(os.environ.get('AO_DIST', '3.0'))
            scene.cycles.samples = int(os.environ.get('AO_SAMPLES', '24'))
            bpy.ops.object.bake(type='AO')
            out_ao = os.path.join(TEX, 'baked_ao.png'); baked_ao.filepath_raw = out_ao; baked_ao.file_format = 'PNG'; baked_ao.save()
            print('AO saved', out_ao, flush=True); info['baked_ao'] = out_ao
        # wire baked normal with a SINGLE clear path TexImage(BakeUV)→NormalMap→BSDF so glTF
        # exports the right normalTexture (v7 Mix nodes made Vein/etc. pick the wrong image).
        # Procedural micro-normal feeds a Bump node afterwards for fine grain without breaking export.
        for mat in me.materials:
            if not mat or not mat.use_nodes: continue
            if mat.name == 'BH_Core_Black':
                tgt = mat.node_tree.nodes.get('BAKE_TARGET')
                if tgt: mat.node_tree.nodes.remove(tgt)
                continue
            nt = mat.node_tree
            bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf is None: continue
            # remove prior Normal Map links / bake target
            tgt = nt.nodes.get('BAKE_TARGET')
            if tgt: nt.nodes.remove(tgt)
            old_nms = [n for n in nt.nodes if n.type == 'NORMAL_MAP']
            proc_tex = None
            for n in nt.nodes:
                if n.type == 'TEX_IMAGE' and n.image and n.image.name.startswith('skin_normal'):
                    proc_tex = n; break
            for n in old_nms:
                nt.nodes.remove(n)
            uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'BakeUV'; uv.location = (-780, -40)
            bn = nt.nodes.new('ShaderNodeTexImage'); bn.image = baked; bn.label = 'BakedDetailN'; bn.location = (-580, -40)
            bn.image.colorspace_settings.name = 'Non-Color'
            nt.links.new(uv.outputs['UV'], bn.inputs['Vector'])
            nm = nt.nodes.new('ShaderNodeNormalMap'); nm.location = (-320, -40)
            nm.inputs['Strength'].default_value = float(os.environ.get('NSTR', '2.4'))
            nt.links.new(bn.outputs['Color'], nm.inputs['Color'])
            # optional micro bump from tiled procedural normal (does not affect glTF normalTexture detection)
            if proc_tex is not None and mat.name != 'BH_Glow_Rim' and float(os.environ.get('MICRO_BUMP', '0')) > 0:   # v9: off by default (Bump made glTF export the tiled skin_normal instead of the bake)
                bump = nt.nodes.new('ShaderNodeBump'); bump.location = (-140, -40)
                bump.inputs['Strength'].default_value = float(os.environ.get('MICRO_BUMP', '0.15'))
                # use procedural normal's color as height proxy (grayscale of existing map)
                nt.links.new(proc_tex.outputs['Color'], bump.inputs['Height'])
                nt.links.new(nm.outputs['Normal'], bump.inputs['Normal'])
                for l in list(bsdf.inputs['Normal'].links): nt.links.remove(l)
                nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
            else:
                for l in list(bsdf.inputs['Normal'].links): nt.links.remove(l)
                nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
            if mat.name == 'BH_Glow_Rim':
                nm.inputs['Strength'].default_value = float(os.environ.get('GLOW_NSTR', '1.2'))
            if baked_ao is not None and mat.name.startswith('BH_Skin') or (baked_ao is not None and mat.name == 'BH_Rim_Wear'):
                an = nt.nodes.new('ShaderNodeTexImage'); an.image = baked_ao; an.label = 'BakedAO'; an.location = (-580, -320)
                nt.links.new(uv.outputs['UV'], an.inputs['Vector'])
                # glTF occlusion socket (exported as occlusionTexture on TEXCOORD_1)
                grp = bpy.data.node_groups.get('glTF Material Output')
                if grp is None:
                    grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
                    grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
                gn = nt.nodes.new('ShaderNodeGroup'); gn.node_tree = grp; gn.location = (300, -400)
                sep = nt.nodes.new('ShaderNodeSeparateColor'); sep.location = (-360, -320)
                nt.links.new(an.outputs['Color'], sep.inputs['Color']); nt.links.new(sep.outputs['Red'], gn.inputs['Occlusion'])
                # Blender render: darken albedo by AO (pore sockets / crevices); the web applies the same via aoMap
                if bsdf.inputs['Base Color'].links:
                    src = bsdf.inputs['Base Color'].links[0].from_socket
                    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.location = (60, 200)
                    mul.inputs['Factor'].default_value = float(os.environ.get('AO_STR', '0.85'))
                    nt.links.new(src, mul.inputs['A']); nt.links.new(an.outputs['Color'], mul.inputs['B'])
                    nt.links.new(mul.outputs['Result'], bsdf.inputs['Base Color'])
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
