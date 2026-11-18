# v11 stage B (blender): apply the scale field to the dense copy (+ gentle real displacement on the 196k low), bake onto low UV:
#   tangent NORMAL, AO, EMIT(col1 = rim/cavity/height), EMIT(col2 = funnel streak/radial/funnel mask). Each bake cached as PNG.
import bpy, os, numpy as np
C = os.environ.get('V11_CACHE', '/tmp/v11'); RES = int(os.environ.get('BAKE_RES', 4096))
bpy.ops.wm.open_mainfile(filepath=C + '/A.blend'); sc = bpy.context.scene
low = bpy.data.objects['BlackHole_Structure']; dense = bpy.data.objects['BH_Dense']
Fd = np.load(C + '/field.npz')
def co_n(o):
    me = o.data; c = np.zeros(len(me.vertices) * 3, np.float32); n = np.zeros_like(c)
    me.vertices.foreach_get('co', c); me.vertices.foreach_get('normal', n); return c.reshape(-1, 3), n.reshape(-1, 3)
c, n = co_n(dense); assert len(c) == len(Fd['disp']), (len(c), len(Fd['disp']))
dense.data.vertices.foreach_set('co', (c + n * Fd['disp'][:, None]).ravel()); dense.data.update()
for nm in ('col1', 'col2'):
    a = dense.data.color_attributes.new(nm, 'FLOAT_COLOR', 'POINT'); v = Fd[nm]
    a.data.foreach_set('color', np.c_[v, np.ones(len(v), np.float32)].ravel())
c, n = co_n(low); low.data.vertices.foreach_set('co', (c + n * Fd['ldisp'][:, None]).ravel()); low.data.update()
print('DISPLACED low |d|max %.3f' % np.abs(Fd['ldisp']).max(), flush=True)
# source material: emission = colour attribute (switched per EMIT bake)
em = bpy.data.materials.new('BakeSrc'); em.use_nodes = True; nt = em.node_tree; nt.nodes.clear()
at = nt.nodes.new('ShaderNodeAttribute'); es = nt.nodes.new('ShaderNodeEmission'); out = nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(at.outputs['Color'], es.inputs['Color']); nt.links.new(es.outputs[0], out.inputs['Surface'])
dense.data.materials.clear(); dense.data.materials.append(em)
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
rb = sc.render.bake; rb.normal_space = 'TANGENT'; rb.use_selected_to_active = True; rb.use_cage = False
rb.cage_extrusion = float(os.environ.get('BAKE_CAGE', 0.9)); rb.max_ray_distance = float(os.environ.get('BAKE_RAY', 2.2)); rb.margin = 16; rb.use_clear = True
if sc.world is None: sc.world = bpy.data.worlds.new('W')
sc.world.light_settings.distance = float(os.environ.get('AO_DIST', 2.5))
def bake(kind, name, res, samples, attr=None):
    path = f'{C}/bake_{name}.png'
    if os.path.exists(path): print('cached', path, flush=True); return path
    if attr: at.attribute_name = attr
    im = bpy.data.images.new('bk_' + name, res, res, alpha=False, float_buffer=False); im.colorspace_settings.name = 'Non-Color'
    for mm in low.data.materials:
        t = mm.node_tree.nodes.get('BAKE_TARGET') or mm.node_tree.nodes.new('ShaderNodeTexImage'); t.name = 'BAKE_TARGET'; t.image = im
        for q in mm.node_tree.nodes: q.select = False
        t.select = True; mm.node_tree.nodes.active = t
    sc.cycles.samples = samples
    bpy.ops.object.select_all(action='DESELECT'); dense.select_set(True); low.select_set(True); bpy.context.view_layer.objects.active = low
    print('BAKE', name, res, flush=True); bpy.ops.object.bake(type=kind)
    im.filepath_raw = path + '.tmp.png'; im.file_format = 'PNG'; im.save(); os.replace(path + '.tmp.png', path); print('SAVED', path, flush=True); return path
bake('NORMAL', 'normal', RES, 4)
bake('EMIT', 'col1', RES, 1, 'col1')
bake('EMIT', 'col2', 2048, 1, 'col2')
bake('AO', 'ao', int(os.environ.get('AO_RES', 2048)), int(os.environ.get('AO_SAMPLES', 16)))
for mm in low.data.materials:
    t = mm.node_tree.nodes.get('BAKE_TARGET')
    if t: mm.node_tree.nodes.remove(t)
bpy.data.objects.remove(dense, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=C + '/B.blend'); print('STAGE_B_DONE', flush=True)
