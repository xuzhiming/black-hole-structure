# v16 stage B = v14 stage B + object-space normal bake (bake_nobj.png, 1024) so stage C can glow side-facing crevices only
# v14 stage B (blender): bake the procedural high mesh (BH_Dense) onto the decimated low UV: tangent NORMAL, AO,
#   EMIT(col1 = fine / broad convexity, pit), EMIT(pos = normalised world position, 16-bit). Each bake cached as PNG.
import bpy, os, numpy as np
C = os.environ.get('V14_CACHE', '/tmp/v14'); RES = int(os.environ.get('BAKE_RES', 4096))
bpy.ops.wm.open_mainfile(filepath=C + '/A.blend'); sc = bpy.context.scene
low = bpy.data.objects['BlackHole_Structure']; dense = bpy.data.objects['BH_Dense']
# source material: emission = colour attribute (switched per EMIT bake)
em = bpy.data.materials.new('BakeSrc'); em.use_nodes = True; nt = em.node_tree; nt.nodes.clear()
at = nt.nodes.new('ShaderNodeAttribute'); es = nt.nodes.new('ShaderNodeEmission'); out = nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(at.outputs['Color'], es.inputs['Color']); nt.links.new(es.outputs[0], out.inputs['Surface'])
dense.data.materials.clear(); dense.data.materials.append(em)
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
rb = sc.render.bake; rb.normal_space = 'TANGENT'; rb.use_selected_to_active = True; rb.use_cage = False
rb.cage_extrusion = float(os.environ.get('BAKE_CAGE', 0.5)); rb.max_ray_distance = float(os.environ.get('BAKE_RAY', 1.4)); rb.margin = 16; rb.use_clear = True
if sc.world is None: sc.world = bpy.data.worlds.new('W')
sc.world.light_settings.distance = float(os.environ.get('AO_DIST', 2.5))
def bake(kind, name, res, samples, attr=None, hi=False):
    path = f'{C}/bake_{name}.png'
    if os.path.exists(path): print('cached', path, flush=True); return path
    if attr: at.attribute_name = attr
    im = bpy.data.images.new('bk_' + name, res, res, alpha=False, float_buffer=hi); im.colorspace_settings.name = 'Non-Color'
    for mm in low.data.materials:
        t = mm.node_tree.nodes.get('BAKE_TARGET') or mm.node_tree.nodes.new('ShaderNodeTexImage'); t.name = 'BAKE_TARGET'; t.image = im
        for q in mm.node_tree.nodes: q.select = False
        t.select = True; mm.node_tree.nodes.active = t
    sc.cycles.samples = samples
    bpy.ops.object.select_all(action='DESELECT'); dense.select_set(True); low.select_set(True); bpy.context.view_layer.objects.active = low
    print('BAKE', name, res, flush=True); bpy.ops.object.bake(type=kind)
    if hi:   # 16-bit PNG (polar coords need > 8 bit)
        st_ = sc.render.image_settings; st_.file_format = 'PNG'; st_.color_depth = '16'; st_.color_mode = 'RGB'
        try: st_.color_management = 'OVERRIDE'; st_.view_settings.view_transform = 'Raw'
        except Exception: sc.view_settings.view_transform = 'Raw'
        im.save_render(path + '.tmp.png', scene=sc)
        st_.color_management = 'FOLLOW_SCENE'; st_.color_depth = '8'
    else:
        im.filepath_raw = path + '.tmp.png'; im.file_format = 'PNG'; im.save()
    os.replace(path + '.tmp.png', path); print('SAVED', path, flush=True); return path
bake('NORMAL', 'normal', RES, 4)
bake('EMIT', 'col1', RES, 1, 'col1')
bake('EMIT', 'pos', RES, 1, 'pos', hi=True)
bake('AO', 'ao', int(os.environ.get('AO_RES', 2048)), int(os.environ.get('AO_SAMPLES', 16)))
rb.normal_space = 'OBJECT'; bake('NORMAL', 'nobj', int(os.environ.get('NOBJ_RES', 1024)), 2); rb.normal_space = 'TANGENT'
for mm in low.data.materials:
    t = mm.node_tree.nodes.get('BAKE_TARGET')
    if t: mm.node_tree.nodes.remove(t)
bpy.data.objects.remove(dense, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=C + '/B.blend'); print('STAGE_B_DONE', flush=True)
