# v10: rebuild from the user's Tripo GLB (ref_glb/user_tripo.glb) -> our convention + spec hole + <=200k smooth pipeline
#  1 import, weld, fill holes, drop specks          2 fit 100x48x120 (Z up, front -Y, origin bottom centre)
#  3 warp the GLB's own bowl onto spec (centre X0 Z58, core Ø26 at recess 18, lip Ø40), dish the core back
#  4 Catmull-Clark x1 -> materials (skin / glow funnel / black core, exact Ø26 seam) -> decimate to 196k (seam kept)
#  5 weld + shade smooth + custom normals from CC x2 dense;   6 bake tangent normal + AO from CC x2 + albedo-driven micro relief
#  7 export model.glb, renders (same sheet cameras / lights as v9)
import bpy, bmesh, math, os, sys, json, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = '/workspace/outputs/black_hole_structure'; TEX = ROOT + '/tex'; OUT_R = ROOT + '/renders'
SRC = os.environ.get('USER_GLB', ROOT + '/ref_glb/user_tripo.glb')
BOX = np.array([100.0, 48.0, 120.0]); HC = np.array([0.0, 58.0]); CORE_R = 13.0; RING_R = 20.0; RECESS = 18.0
TRI_TARGET = int(os.environ.get('TRI_TARGET', 196000)); BAKE_RES = int(os.environ.get('BAKE_RES', 2048))
os.makedirs(OUT_R, exist_ok=True); os.makedirs(TEX, exist_ok=True)
def env(k, d): return float(os.environ.get(k, d))
def sstep(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def srgb2lin(c): return tuple(((x/255+0.055)/1.055)**2.4 if x/255 > 0.04045 else x/255/12.92 for x in c)
bpy.ops.wm.read_factory_settings(use_empty=True); scene = bpy.context.scene
info = {'source': os.path.basename(SRC)}

# ---------- 1 import + clean ----------
bpy.ops.import_scene.gltf(filepath=SRC)
ob = [o for o in scene.objects if o.type == 'MESH'][0]
mw = ob.matrix_world.copy(); ob.parent = None; ob.matrix_world = mw
for o in [o for o in scene.objects if o.type != 'MESH']: bpy.data.objects.remove(o, do_unlink=True)
ob.data.transform(ob.matrix_world); ob.matrix_world.identity(); ob.name = 'BlackHole_Structure'
src_img = {}
for n in ob.active_material.node_tree.nodes:
    if n.type == 'TEX_IMAGE': src_img[n.image.name] = n.image
info['src_tris'] = len(ob.data.polygons); info['src_verts'] = len(ob.data.vertices)
bm = bmesh.new(); bm.from_mesh(ob.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
bnd = [e for e in bm.edges if e.is_boundary]; info['boundary_edges_after_weld'] = len(bnd)
newf = bmesh.ops.holes_fill(bm, edges=bnd, sides=400)['faces']; nf = set(newf)
uvl = bm.loops.layers.uv.active
for f in newf:   # filled caps get the UV of their boundary vertex from an original face (else they span the atlas)
    for lp in f.loops:
        src = next((l2 for l2 in lp.vert.link_loops if l2.face not in nf), None)
        if src is not None: lp[uvl].uv = src[uvl].uv.copy()
info['filled_faces'] = len(newf)
# drop floating specks (< 40 verts)
bm.verts.ensure_lookup_table(); seen = np.zeros(len(bm.verts), bool); kill = []
for v in bm.verts:
    if seen[v.index]: continue
    st = [v]; seen[v.index] = True; comp = []
    while st:
        x = st.pop(); comp.append(x)
        for e in x.link_edges:
            y = e.other_vert(x)
            if not seen[y.index]: seen[y.index] = True; st.append(y)
    if len(comp) < 40: kill += comp
bmesh.ops.delete(bm, geom=kill, context='VERTS'); info['speck_verts_removed'] = len(kill)
bmesh.ops.triangulate(bm, faces=bm.faces)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
info['non_manifold_after_clean'] = sum(1 for e in bm.edges if not e.is_manifold)
bm.to_mesh(ob.data); bm.free(); ob.data.update()
print('CLEAN', info, flush=True)

def getco(o):
    c = np.zeros(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get('co', c); return c.reshape(-1, 3).astype(np.float64)
def setco(o, c): o.data.vertices.foreach_set('co', c.astype(np.float32).ravel()); o.data.update()

# ---------- 2 fit to the box ----------
c = getco(ob); lo, hi = c.min(0), c.max(0); info['src_bbox_size_zup'] = (hi - lo).round(3).tolist()
s = BOX / (hi - lo); info['fit_scale_xyz'] = s.round(4).tolist()
c = (c - [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]) * s
setco(ob, c)

def depth_grid(o, step=0.5):
    me = o.data; V = getco(o); P = [tuple(p.vertices) for p in me.polygons]
    bvh = BVHTree.FromPolygons([tuple(x) for x in V], P)
    xs = np.arange(-50, 50.01, step); zs = np.arange(0, 120.01, step); D = np.full((len(zs), len(xs)), np.nan); FI = np.full(D.shape, -1)
    for i, z in enumerate(zs):
        for j, x in enumerate(xs):
            h = bvh.ray_cast(Vector((x, -80, z)), Vector((0, 1, 0)), 300)
            if h[0] is not None: D[i, j] = h[0].y; FI[i, j] = h[2]
    return xs, zs, D, FI

# ---------- 3 hole warp (GLB bowl -> spec funnel/core) ----------
xs, zs, D, _ = depth_grid(ob, 1.0); X, Z = np.meshgrid(xs, zs)
fl = (D > np.nanmin(D[(np.abs(X) < 25) & (Z > 35) & (Z < 80)]) + 0) & (Z > 35) & (Z < 80) & (np.abs(X) < 25)
floor_y = np.nanmax(D[(np.abs(X) < 25) & (Z > 35) & (Z < 80)])
m = (D > floor_y - 2.5) & (Z > 35) & (Z < 80) & (np.abs(X) < 25)
c0 = np.array([X[m].mean(), Z[m].mean()]); front_y = np.nanmin(D)
info['src_hole'] = dict(centre_xz=c0.round(2).tolist(), floor_y=round(float(floor_y), 2), floor_diam_eq=round(float(2 * np.sqrt(m.sum() / np.pi)), 2), front_face_y=round(float(front_y), 2),
                        recess_front_to_floor=round(float(floor_y - front_y), 2))
print('SRC HOLE', info['src_hole'], flush=True)
R_FLOOR = env('R_FLOOR', 8.5); R_LIP = env('R_LIP', 18.5); R_OUT = env('R_OUT', 34.0)
_rr = np.hypot(X - c0[0], Z - c0[1]); y_edge = float(np.nanmean(D[np.abs(_rr - R_FLOOR) < 0.75])); info['src_hole']['y_at_r_floor'] = round(y_edge, 2)
def warp(c):
    c = c.copy(); dx = c[:, 0] - c0[0]; dz = c[:, 2] - c0[1]; r0 = np.hypot(dx, dz); u = np.stack([dx, dz], 1) / np.maximum(r0, 1e-6)[:, None]
    wy = sstep(1.0, -4.0, c[:, 1])                                       # front shell only (back of the body untouched)
    rk = [0, R_FLOOR * 0.5, R_FLOOR, (R_FLOOR + R_LIP) / 2, R_LIP, (R_LIP + R_OUT) / 2, R_OUT, 1e4]
    rv = [0, CORE_R * 0.5, CORE_R, (CORE_R + RING_R) / 2, RING_R, ((RING_R + R_OUT) / 2 + (R_LIP + R_OUT) / 2) / 2, R_OUT, 1e4]
    r1 = r0 + (np.interp(r0, rk, rv) - r0) * wy
    wt = (1 - sstep(RING_R, R_OUT + 2, r0)) * wy
    cen = c0[None, :] + (HC - c0)[None, :] * wt[:, None]
    c[:, 0] = cen[:, 0] + u[:, 0] * r1; c[:, 2] = cen[:, 1] + u[:, 1] * r1
    # depth: floor -> core mouth at front+18 (edge), dished 5 m further back in the middle; wall eased to the lip
    mouth = front_y + RECESS + env('RECESS_ADJ', 0.0)
    inb = wy * (1 - sstep(R_FLOOR, R_LIP, r0))
    dish = env('DISH', 5.0) * np.clip(1 - (r0 / R_FLOOR) ** 2, 0, 1)
    c[:, 1] = c[:, 1] + ((mouth - y_edge) + dish) * inb
    return c, r0, wy
c, r0, wy = warp(getco(ob)); setco(ob, c)
bowl_v = (r0 < R_LIP + 1.0) & (wy > 0.5)
info['warp'] = dict(R_FLOOR=R_FLOOR, R_LIP=R_LIP, R_OUT=R_OUT, dish=env('DISH', 5.0))

def fit_box(c):
    """exact 100x48x120 again, stretch faded out within r<24 of the hole (keeps centre/Ø on spec)"""
    lo0 = np.array([-BOX[0] / 2, -BOX[1] / 2, 0.0]); hi0 = np.array([BOX[0] / 2, BOX[1] / 2, BOX[2]])
    l1, h1 = c.min(0), c.max(0); d = lo0 + (c - l1) * (hi0 - lo0) / (h1 - l1) - c
    r = np.hypot(c[:, 0] - HC[0], c[:, 2] - HC[1]); w = sstep(24.0, 40.0, r)
    c = c + d * w[:, None]; l2, h2 = c.min(0), c.max(0); return lo0 + (c - l2) * (hi0 - lo0) / (h2 - l2)
setco(ob, fit_box(getco(ob)))
# mark bowl verts so the flag survives subdivision (float attr interpolates)
a = ob.data.attributes.new('bowl', 'FLOAT', 'POINT'); a.data.foreach_set('value', bowl_v.astype(np.float32))

# ---------- 4 subdivide, materials, decimate ----------
def subdiv(o, lv, name):
    o2 = bpy.data.objects.new(name, o.data.copy()); scene.collection.objects.link(o2)
    md = o2.modifiers.new('cc', 'SUBSURF'); md.levels = lv; md.render_levels = lv; md.uv_smooth = 'PRESERVE_BOUNDARIES'; md.quality = 3
    bpy.context.view_layer.objects.active = o2; bpy.ops.object.modifier_apply(modifier='cc')
    bm = bmesh.new(); bm.from_mesh(o2.data); bmesh.ops.triangulate(bm, faces=bm.faces); bm.to_mesh(o2.data); bm.free()
    setco(o2, fit_box(getco(o2))); return o2
dense = subdiv(ob, int(env('DENSE_LV', 2)), 'BH_Dense')
low = subdiv(ob, 1, 'BH_Low'); bpy.data.objects.remove(ob, do_unlink=True); ob = low; ob.name = 'BlackHole_Structure'
print('SUBDIV low', len(ob.data.polygons), 'dense', len(dense.data.polygons), flush=True)

def cls_and_snap(o, snap=True):
    me = o.data; V = getco(o); bw = np.zeros(len(V), np.float32); me.attributes['bowl'].data.foreach_get('value', bw)
    r = np.hypot(V[:, 0] - HC[0], V[:, 2] - HC[1]); inb = bw > 0.5
    if snap:  # put the Ø26 seam exactly on the circle: nearest ring of bowl verts snaps radially to r=13
        el = np.zeros(len(me.edges) * 2, np.int32); me.edges.foreach_get('vertices', el); el = el.reshape(-1, 2)
        Ln = np.linalg.norm(V[el[:, 0]] - V[el[:, 1]], axis=1); ml = np.median(Ln[inb[el[:, 0]] & inb[el[:, 1]]])
        sn = inb & (np.abs(r - CORE_R) < 0.5 * ml)
        k = (CORE_R / np.maximum(r[sn], 1e-6)); V[sn, 0] = HC[0] + (V[sn, 0] - HC[0]) * k; V[sn, 2] = HC[1] + (V[sn, 2] - HC[1]) * k
        setco(o, V); r = np.hypot(V[:, 0] - HC[0], V[:, 2] - HC[1])
    fv = np.zeros(len(me.polygons) * 3, np.int32); me.polygons.foreach_get('vertices', fv); fv = fv.reshape(-1, 3)
    fin = inb[fv].all(1); fr = r[fv]
    core = fin & (fr.max(1) <= CORE_R + 1e-3)
    glow = fin & ~core & (fr.min(1) < RING_R + 0.5)
    fm = np.where(core, 2, np.where(glow, 1, 0)).astype(np.int32)
    return fm, V, fv

# materials
def tex_node(nt, im, noncolor=False, uv=None):
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = im
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    return t
alb_path = TEX + '/v10_albedo.jpg'; mr_path = TEX + '/v10_mr.jpg'
ALB = bpy.data.images.load(alb_path); MR = bpy.data.images.load(mr_path); MR.colorspace_settings.name = 'Non-Color'
def mat_skin():
    m = bpy.data.materials.new('BH_Skin_Bronze'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = tex_node(nt, ALB); r = tex_node(nt, MR, True); sp = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(t.outputs['Color'], b.inputs['Base Color']); nt.links.new(r.outputs['Color'], sp.inputs['Color'])
    nt.links.new(sp.outputs['Green'], b.inputs['Roughness']); nt.links.new(sp.outputs['Blue'], b.inputs['Metallic'])
    b.inputs['Specular IOR Level'].default_value = 0.45; return m
def mat_glow():
    m = bpy.data.materials.new('BH_Glow_Rim'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = tex_node(nt, ALB); r = tex_node(nt, MR, True); sp = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(t.outputs['Color'], b.inputs['Base Color']); nt.links.new(r.outputs['Color'], sp.inputs['Color'])
    nt.links.new(sp.outputs['Green'], b.inputs['Roughness'])
    e = tex_node(nt, bpy.data.images.load(TEX + '/v10_glow_emit.jpg', check_existing=True))
    nt.links.new(e.outputs['Color'], b.inputs['Emission Color'])       # glTF emissiveTexture: violet streaks from the albedo
    b.inputs['Emission Strength'].default_value = env('GLOW', 1.2); b.inputs['Metallic'].default_value = 0.0
    b.inputs['Specular IOR Level'].default_value = 0.1; return m
def mat_core():
    m = bpy.data.materials.new('BH_Core_Black'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0, 0, 0, 1); b.inputs['Roughness'].default_value = 1.0; b.inputs['Specular IOR Level'].default_value = 0.0; return m
MATS = [mat_skin(), mat_glow(), mat_core()]
def assign(o, fm):
    o.data.materials.clear()
    for mm in MATS: o.data.materials.append(mm)
    o.data.polygons.foreach_set('material_index', fm); o.data.update()
fm, V, fv = cls_and_snap(ob); assign(ob, fm)
fmD, _, _ = cls_and_snap(dense, snap=False); assign(dense, fmD)

def decimate(o, ratio, keep_idx, tag):
    vg = o.vertex_groups.new(name='keep_' + tag); vg.add(keep_idx.tolist(), 1.0, 'REPLACE')
    md = o.modifiers.new('dec', 'DECIMATE'); md.decimate_type = 'COLLAPSE'; md.ratio = float(np.clip(ratio, 0.001, 1)); md.use_collapse_triangulate = True
    md.vertex_group = vg.name; md.invert_vertex_group = True; md.vertex_group_factor = 10.0
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='dec'); o.vertex_groups.remove(o.vertex_groups[vg.name])
def seam_verts(o):
    me = o.data; fmi = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('material_index', fmi)
    fv = np.zeros(len(me.polygons) * 3, np.int32); me.polygons.foreach_get('vertices', fv); fv = fv.reshape(-1, 3)
    a = np.unique(fv[fmi == 2].ravel()); b = np.unique(fv[fmi != 2].ravel()); return np.intersect1d(a, b)
n0 = len(ob.data.polygons)
decimate(ob, TRI_TARGET / n0, seam_verts(ob), 'low')
print('DECIMATE', n0, '->', len(ob.data.polygons), flush=True)

# ---------- 5 weld / smooth / custom normals ----------
def weld_smooth(o, dist=0.002):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT'); bpy.ops.object.shade_smooth()
    try: bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception: pass
weld_smooth(ob); weld_smooth(dense)
def fix_uv(o, thr=8.0):
    """decimate collapses a few edges across UV seams -> faces whose UVs span the atlas (they wreck the bake by overdrawing
    good islands). Give each such face the UV of one vertex taken from a neighbouring good face (zero UV area)."""
    me = o.data; uvd = me.uv_layers[0].data
    uv = np.zeros(len(me.loops) * 2, np.float32); uvd.foreach_get('uv', uv); uv = uv.reshape(-1, 3, 2)
    P = getco(o)[np.array([tuple(p.vertices) for p in me.polygons])]
    a3 = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    a2 = 0.5 * np.abs((uv[:, 1, 0] - uv[:, 0, 0]) * (uv[:, 2, 1] - uv[:, 0, 1]) - (uv[:, 2, 0] - uv[:, 0, 0]) * (uv[:, 1, 1] - uv[:, 0, 1]))
    e = np.max(np.linalg.norm(uv - np.roll(uv, 1, 1), axis=2), 1)                     # longest UV edge
    r = a2 / np.maximum(a3, 1e-9); r = r / np.median(r)
    bad = (r > thr) | (e > 0.08); bad_set = set(np.where(bad)[0].tolist())
    lv = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv); good_uv = {}
    for li in range(len(lv)):
        if li // 3 not in bad_set: good_uv.setdefault(lv[li], uv.reshape(-1, 2)[li])
    flat = uv.reshape(-1, 2)
    for f in bad_set:
        ref = next((good_uv[lv[3 * f + k]] for k in range(3) if lv[3 * f + k] in good_uv), flat[3 * f])
        for k in range(3): flat[3 * f + k] = good_uv.get(lv[3 * f + k], ref) if False else ref
    uvd.foreach_set('uv', flat.ravel()); me.update(); return int(bad.sum())
info['uv_faces_fixed'] = fix_uv(ob); print('UV FIX', info['uv_faces_fixed'], flush=True)
setco(ob, fit_box(getco(ob)))
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
x = ob.modifiers.new('nx', 'DATA_TRANSFER'); x.object = dense; x.use_loop_data = True; x.data_types_loops = {'CUSTOM_NORMAL'}
x.loop_mapping = 'POLYINTERP_NEAREST'; x.use_max_distance = True; x.max_distance = 1.5
bpy.ops.object.modifier_apply(modifier='nx'); print('CUSTOM_NORMALS', ob.data.has_custom_normals, flush=True)

# ---------- 6 bake: detail relief from albedo (high-pass luminance) on the dense copy ----------
relief = bpy.data.objects.new('BH_Relief', dense.data.copy()); scene.collection.objects.link(relief)
HP = bpy.data.images.load(TEX + '/v10_height.png'); HP.colorspace_settings.name = 'Non-Color'
tx = bpy.data.textures.new('hp', 'IMAGE'); tx.image = HP; tx.extension = 'EXTEND'
dm = relief.modifiers.new('disp', 'DISPLACE'); dm.texture = tx; dm.texture_coords = 'UV'; dm.uv_layer = relief.data.uv_layers[0].name
dm.strength = env('RELIEF', 0.3); dm.mid_level = 0.5
bpy.context.view_layer.objects.active = relief; bpy.ops.object.modifier_apply(modifier='disp')
bpy.data.objects.remove(dense, do_unlink=True)
me = ob.data; uvname = me.uv_layers[0].name
def bake(kind, path, samples):
    im = bpy.data.images.new('bake_' + kind, BAKE_RES, BAKE_RES, alpha=False); im.colorspace_settings.name = 'Non-Color'
    for mm in me.materials:
        nt = mm.node_tree; n = nt.nodes.get('BAKE_TARGET') or nt.nodes.new('ShaderNodeTexImage'); n.name = 'BAKE_TARGET'; n.image = im
        for q in nt.nodes: q.select = False
        n.select = True; nt.nodes.active = n
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = samples
    rb = scene.render.bake; rb.normal_space = 'TANGENT'; rb.use_selected_to_active = True; rb.use_cage = False
    rb.cage_extrusion = env('BAKE_CAGE', 0.8); rb.max_ray_distance = env('BAKE_RAY', 2.0); rb.margin = 8; rb.use_clear = True
    bpy.ops.object.select_all(action='DESELECT'); relief.select_set(True); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    print('BAKE', kind, flush=True); bpy.ops.object.bake(type=kind)
    im.filepath_raw = path; im.file_format = 'PNG'; im.save(); return path
if scene.world is None: scene.world = bpy.data.worlds.new('W')
scene.world.light_settings.distance = env('AO_DIST', 3.0)
pN = bake('NORMAL', TEX + '/v10_baked_n.png', 8)
pA = bake('AO', TEX + '/v10_baked_ao.png', int(env('AO_SAMPLES', 24)))
bpy.data.objects.remove(relief, do_unlink=True)
for mm in me.materials:
    t = mm.node_tree.nodes.get('BAKE_TARGET')
    if t: mm.node_tree.nodes.remove(t)
import subprocess   # Blender's python has no PIL: convert the bakes to JPEG with the system python (keeps model.glb < 25 MiB)
subprocess.run(['/usr/bin/python3', '-c', "from PIL import Image; import sys; [Image.open(a).convert(m).save(b, quality=93) for a, b, m in "
                "[(sys.argv[1], sys.argv[2], 'RGB'), (sys.argv[3], sys.argv[4], 'L')]]", pN, TEX + '/v10_baked_n.jpg', pA, TEX + '/v10_baked_ao.jpg'], check=True)
subprocess.run(['/usr/bin/python3', '-c', "from PIL import Image, ImageFilter; import numpy as np, sys; a=np.asarray(Image.open(sys.argv[1]).convert('L').filter(ImageFilter.GaussianBlur(1.5))).astype(float)/255; "
                "Image.fromarray((255*(1-float(sys.argv[2])*(1-a))).astype('uint8')).save(sys.argv[1], quality=93)", TEX + '/v10_baked_ao.jpg', str(env('AO_SOFT', 0.6))], check=True)
NRM = bpy.data.images.load(TEX + '/v10_baked_n.jpg'); NRM.colorspace_settings.name = 'Non-Color'
AO = bpy.data.images.load(TEX + '/v10_baked_ao.jpg'); AO.colorspace_settings.name = 'Non-Color'
grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree'); grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
for mm in MATS[:2]:
    nt = mm.node_tree; b = nt.nodes['Principled BSDF']
    n = tex_node(nt, NRM, True); nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = env('NSTR', 1.0)
    nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    an = tex_node(nt, AO, True); sp = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(an.outputs['Color'], sp.inputs['Color'])
    gn = nt.nodes.new('ShaderNodeGroup'); gn.node_tree = grp; nt.links.new(sp.outputs['Red'], gn.inputs['Occlusion'])
    if mm.name == 'BH_Skin_Bronze':   # Blender renders: AO darkens albedo (web: aoMap)
        src = b.inputs['Base Color'].links[0].from_socket
        mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = env('AO_STR', 0.85)
        nt.links.new(src, mul.inputs['A']); nt.links.new(an.outputs['Color'], mul.inputs['B']); nt.links.new(mul.outputs['Result'], b.inputs['Base Color'])

# ---------- measure ----------
V = getco(ob); lo, hi = V.min(0), V.max(0)
fmi = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('material_index', fmi)
fv = np.zeros(len(me.polygons) * 3, np.int32); me.polygons.foreach_get('vertices', fv); fv = fv.reshape(-1, 3)
cv = np.unique(fv[fmi == 2].ravel()); C = V[cv]
hc = [0.5 * (C[:, 0].min() + C[:, 0].max()), float(np.median(C[:, 1])), 0.5 * (C[:, 2].min() + C[:, 2].max())]
seam = seam_verts(ob); S = V[seam]; core_mouth_y = float(np.median(S[:, 1]))
info.update(tris=len(me.polygons), verts=len(me.vertices), bbox_min=lo.tolist(), bbox_max=hi.tolist(), bbox_size=(hi - lo).tolist(),
            hole_centre=[float(hc[0]), float(hc[1]), float(hc[2])], core_d_x=float(C[:, 0].max() - C[:, 0].min()), core_d_z=float(C[:, 2].max() - C[:, 2].min()),
            core_mouth_y=core_mouth_y, recess_from_front_face=core_mouth_y - float(lo[1]), ring_d_x=2 * RING_R, ring_d_z=2 * RING_R,
            mat_faces={n: int((fmi == i).sum()) for i, n in enumerate(['skin', 'glow', 'core'])})
print('MEASURE', json.dumps({k: info[k] for k in ('tris', 'bbox_size', 'hole_centre', 'core_d_x', 'core_d_z', 'recess_from_front_face')}), flush=True)
json.dump(info, open(ROOT + '/measure.json', 'w'), indent=1, default=float)
# drop the GLB's own material + packed 4096 maps (MR png alone is 24 MB): replaced by tex/v10_*.jpg, keeps model.blend < 25 MiB
for mm in [m_ for m_ in bpy.data.materials if not m_.name.startswith('BH_')]: bpy.data.materials.remove(mm)
for im in [i for i in bpy.data.images if i.packed_file]: bpy.data.images.remove(im)
bpy.ops.wm.save_as_mainfile(filepath=ROOT + '/model.blend', compress=True)
for o in scene.objects: o.select_set(o == ob)
bpy.ops.export_scene.gltf(filepath=ROOT + '/model.glb', export_format='GLB', use_selection=True, export_apply=True, export_lights=False, export_cameras=False,
                          export_image_format='AUTO', export_yup=True, export_vertex_color='NONE')
print('EXPORTED', os.path.getsize(ROOT + '/model.glb'), flush=True)

# ---------- 7 renders ----------
sys.path.insert(0, os.path.dirname(__file__)); import rend_common as rc
bc = rc.setup(scene, hole=(hc[0], hc[1] - 6, hc[2]), hole_w=env('HOLE_W', 1200), key=env('KEY', 6.5))
views = rc.views(scene, hc=(hc[0], lo[1] + 4, hc[2]))
if os.environ.get('RENDER', '1') == '1':
    only = os.environ.get('ONLY'); rc.render(scene, bc, views, OUT_R, only=only.split(',') if only else None, samples=int(env('SAMPLES', 48)),
                                              expo=env('EXPO', 0.95), expo_hero=env('EXPO_HERO', 1.1))
