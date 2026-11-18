# shared sheet-style lighting + cameras (copied from scene.py) for rendering an arbitrary object set
import bpy, math, os
from mathutils import Vector
def srgb2lin(c): return tuple(((x/255+0.055)/1.055)**2.4 if x/255>0.04045 else x/255/12.92 for x in c)
def setup(sc, hole=(0,-20,58), hole_w=2500, key=6.5):
    w=bpy.data.worlds.new('World'); sc.world=w; w.use_nodes=True; nt=w.node_tree; nt.nodes.clear()
    lp=nt.nodes.new('ShaderNodeLightPath'); bl=nt.nodes.new('ShaderNodeBackground'); bl.inputs[0].default_value=(0.55,0.48,0.52,1); bl.inputs[1].default_value=0.35
    bc=nt.nodes.new('ShaderNodeBackground'); bc.name='CamBG'; bc.inputs[0].default_value=(*srgb2lin((236,230,219)),1)
    mx=nt.nodes.new('ShaderNodeMixShader'); out=nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(lp.outputs['Is Camera Ray'],mx.inputs[0]); nt.links.new(bl.outputs[0],mx.inputs[1]); nt.links.new(bc.outputs[0],mx.inputs[2]); nt.links.new(mx.outputs[0],out.inputs[0])
    def L(n,t,loc,rot,e,c=(1,1,1),s=None):
        ld=bpy.data.lights.new(n,t); ld.energy=e; ld.color=c
        if t=='SUN': ld.angle=math.radians(4)
        if s and t=='POINT': ld.shadow_soft_size=s
        o=bpy.data.objects.new(n,ld); o.location=loc; o.rotation_euler=rot; sc.collection.objects.link(o)
    L('Key_Sun','SUN',(0,0,150),(math.radians(50),0,math.radians(-30)),key,(1.0,0.90,0.78))
    L('Rim_Sun','SUN',(0,0,150),(math.radians(60),0,math.radians(150)),2.4,(0.80,0.62,1.0))
    if hole_w: L('Hole_Glow','POINT',hole,(0,0,0),hole_w,srgb2lin((200,60,255)),6)
    sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.use_denoising=True; sc.cycles.max_bounces=4
    sc.view_settings.view_transform='Standard'; sc.view_settings.look='None'
    return bc
def cam(sc,name,loc,target,ortho=None,lens=50):
    cd=bpy.data.cameras.new(name)
    if ortho: cd.type='ORTHO'; cd.ortho_scale=ortho
    else: cd.lens=lens
    cd.clip_end=2000; c=bpy.data.objects.new(name,cd); c.location=loc; sc.collection.objects.link(c)
    c.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler(); return c
def views(sc,hc=(0,-24,58)):
    mid=(0,0,60)
    return {'front':(cam(sc,'Cam_Front',(0,-300,60),mid,132),(900,900)),'rear':(cam(sc,'Cam_Rear',(0,300,60),mid,132),(900,900)),
     'left':(cam(sc,'Cam_Left',(-300,0,60),mid,132),(900,900)),'right':(cam(sc,'Cam_Right',(300,0,60),mid,132),(900,900)),
     'top':(cam(sc,'Cam_Top',(0,-0.001,400),(0,0,0),112),(900,900)),'axo':(cam(sc,'Cam_Axo',(-170,-300,230),(0,0,58),150),(900,900)),
     'hero':(cam(sc,'Cam_Hero',(-120,-205,42),(2,0,58),lens=40),(1600,1000)),
     'closeup':(cam(sc,'Cam_Closeup',(hc[0]-48,hc[1]-70,hc[2]+30),(hc[0]-18,hc[1]-2,hc[2]+10),lens=45),(1600,1000))}
def render(sc,bc,V,outdir,only=None,samples=48,expo=0.95,expo_hero=1.1):
    os.makedirs(outdir,exist_ok=True); sc.cycles.samples=samples
    for k,(c,(w,h)) in V.items():
        if only and k not in only: continue
        dark=k in ('hero','closeup')
        bc.inputs[0].default_value=(0.004,0.004,0.007,1) if dark else (*srgb2lin((236,230,219)),1)
        sc.view_settings.exposure=expo_hero if dark else expo; bc.inputs[1].default_value=1/(2**sc.view_settings.exposure)
        sc.camera=c; sc.render.resolution_x=w; sc.render.resolution_y=h; sc.render.filepath=os.path.join(outdir,k+'.png')
        bpy.ops.render.render(write_still=True); print('RENDERED',k,flush=True)
