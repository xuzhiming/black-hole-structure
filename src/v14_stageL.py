# v14 stage L (blender): hi.npz -> BH_Dense (high, colour attributes) + BlackHole_Structure (decimated <=200k, funnel protected,
#   smart-UV, smooth + custom normals transferred from the high mesh); materials skin / glow funnel / black core. Saves A.blend.
import bpy, os, json, numpy as np
C = os.environ.get('V14_CACHE', '/tmp/v14'); TRI = int(os.environ.get('TRI_TARGET', 196000))
G = json.load(open(C + '/geom.json')); Y_E, Y_M = G['Y_E'], G['Y_M']
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
Z = np.load(C + '/hi.npz'); v, f = Z['v'], Z['f']
def mk(name, v, f):
    me = bpy.data.meshes.new(name); me.vertices.add(len(v)); me.vertices.foreach_set('co', v.ravel())
    me.loops.add(f.size); me.loops.foreach_set('vertex_index', f.ravel()); me.polygons.add(len(f))
    me.polygons.foreach_set('loop_start', np.arange(0, f.size, 3, dtype=np.int32)); me.polygons.foreach_set('loop_total', np.full(len(f), 3, np.int32))
    me.update(); me.validate(); o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); return o
def classify(cen):
    rh = np.hypot(cen[:, 0], cen[:, 2] - 58.0); y = cen[:, 1]
    rf = np.where(y >= Y_E, 13.0 + 7.0 * np.clip((Y_M - y) / 18.0, 0, 1) ** 0.8, 20.0 + 0.35 * (Y_E - y))
    fm = np.zeros(len(cen), np.int32)
    fm[(rh < 20.6) & (y < Y_M - 0.12) & (y > Y_E - 0.6) & (np.abs(rh - rf) < 1.2)] = 1
    fm[(rh < 13.25) & (np.abs(y - Y_M) < 0.3)] = 2
    return fm
dense = mk('BH_Dense', v, f)
# colour attributes for the EMIT bakes: col1 = (fine convexity, broad convexity, pit), pos = normalised world position
s1, s3 = float(np.percentile(np.abs(Z['conv1']), 98)), float(np.percentile(np.abs(Z['conv3']), 98))
col1 = np.stack([np.clip(0.5 + 0.5 * Z['conv1'] / s1, 0, 1), np.clip(0.5 + 0.5 * Z['conv3'] / s3, 0, 1), Z['pit']], 1)
PL, PS = np.array([-55.0, -32.0, -5.0]), np.array([110.0, 64.0, 130.0])
pos = np.clip((v - PL) / PS, 0, 1)
for nm, val in (('col1', col1), ('pos', pos)):
    a = dense.data.color_attributes.new(nm, 'FLOAT_COLOR', 'POINT'); a.data.foreach_set('color', np.c_[val, np.ones(len(val))].astype(np.float32).ravel())
for nm in ('BH_Skin_Bronze', 'BH_Glow_Rim', 'BH_Core_Black'):
    m = bpy.data.materials.new(nm); m.use_nodes = True; dense.data.materials.append(m)
fmD = classify(v[f].mean(1)); dense.data.polygons.foreach_set('material_index', fmD)
dense.data.polygons.foreach_set('use_smooth', np.ones(len(f), bool)); dense.data.update()
print('DENSE', len(v), len(f), 'glow', int((fmD == 1).sum()), 'core', int((fmD == 2).sum()), flush=True)
# low: decimate a copy, funnel + core protected
low = bpy.data.objects.new('BlackHole_Structure', dense.data.copy()); sc.collection.objects.link(low)
for a in list(low.data.color_attributes): low.data.color_attributes.remove(a)
keep = np.unique(f[fmD > 0].ravel()); vg = low.vertex_groups.new(name='keep'); vg.add(keep.tolist(), 1.0, 'REPLACE')
md = low.modifiers.new('dec', 'DECIMATE'); md.decimate_type = 'COLLAPSE'; md.ratio = TRI / len(f); md.use_collapse_triangulate = True
md.vertex_group = 'keep'; md.invert_vertex_group = True; md.vertex_group_factor = float(os.environ.get('KEEP_F', 3.0))
bpy.context.view_layer.objects.active = low; low.select_set(True); bpy.ops.object.modifier_apply(modifier='dec'); low.vertex_groups.remove(low.vertex_groups['keep'])
print('DECIMATED', len(low.data.polygons), flush=True)
# re-classify low faces (decimation keeps indices, but re-derive at the seam for a clean Ø26 edge)
lv = np.zeros(len(low.data.vertices) * 3, np.float32); low.data.vertices.foreach_get('co', lv); lv = lv.reshape(-1, 3)
lf = np.zeros(len(low.data.polygons) * 3, np.int32); low.data.polygons.foreach_get('vertices', lf); lf = lf.reshape(-1, 3)
fmL = classify(lv[lf].mean(1)); low.data.polygons.foreach_set('material_index', fmL)
# exact Ø26 core mouth: snap the core / funnel seam ring to r = 13, y = Y_M; flatten the core cap onto the mouth plane
cv_ = np.unique(lf[fmL == 2].ravel()); ov_ = np.unique(lf[fmL != 2].ravel()); seam = np.intersect1d(cv_, ov_); inner = np.setdiff1d(cv_, seam)
d = lv[seam] - np.array([0, 0, 58.0]); rr = np.hypot(d[:, 0], d[:, 2]) + 1e-9
lv[seam, 0] = d[:, 0] / rr * 13.0; lv[seam, 2] = 58.0 + d[:, 2] / rr * 13.0; lv[seam, 1] = Y_M
di = lv[inner] - np.array([0, 0, 58.0]); ri = np.hypot(di[:, 0], di[:, 2]) + 1e-9; sc_ = np.minimum(1.0, 12.9 / ri)
lv[inner, 0] = di[:, 0] * sc_; lv[inner, 2] = 58.0 + di[:, 2] * sc_; lv[inner, 1] = Y_M
low.data.vertices.foreach_set('co', lv.ravel()); low.data.update(); print('SEAM', len(seam), 'core inner', len(inner), flush=True)
bpy.ops.object.select_all(action='DESELECT'); low.select_set(True); bpy.context.view_layer.objects.active = low
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=0.002)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.uv.smart_project(angle_limit=np.radians(66), island_margin=0.0015, area_weight=0.0, scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT'); bpy.ops.object.shade_smooth()
# make the dense normals consistent too (marching-cubes winding is already outward; this is a guard)
bpy.ops.object.select_all(action='DESELECT'); dense.select_set(True); bpy.context.view_layer.objects.active = dense
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT'); low.select_set(True); bpy.context.view_layer.objects.active = low
x = low.modifiers.new('nx', 'DATA_TRANSFER'); x.object = dense; x.use_loop_data = True; x.data_types_loops = {'CUSTOM_NORMAL'}
x.loop_mapping = 'POLYINTERP_NEAREST'; x.use_max_distance = True; x.max_distance = 1.5
bpy.ops.object.modifier_apply(modifier='nx'); print('CUSTOM_NORMALS', low.data.has_custom_normals, flush=True)
info = dict(source='procedural v14 (SDF + marching cubes)', geom=G, dense_tris=len(f), low_tris=len(low.data.polygons), conv_scale=[s1, s3],
            pos_lo=PL.tolist(), pos_size=PS.tolist(), glow_faces=int((fmL == 1).sum()), core_faces=int((fmL == 2).sum()))
json.dump(info, open(C + '/infoA.json', 'w'), indent=1); json.dump(dict(note='v14 procedural', **{k: G[k] for k in ('tubes', 'pores', 'vox')}), open(C + '/field.json', 'w'))
bpy.ops.wm.save_as_mainfile(filepath=C + '/A.blend'); print('STAGE_L_DONE', info, flush=True)
