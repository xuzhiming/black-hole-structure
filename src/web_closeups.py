# web close-ups (headless Chrome, swiftshader): open a self-contained preview.html, put the camera at the same tentacles / tail / tail-fill /
# rear close-up positions as v17_closeups.py (Blender Z-up -> glTF Y-up: (x, y, z) -> (x, z, -y), after the page's own model transform)
# usage: python3 web_closeups.py preview.html outdir
import sys, os, time, base64
from playwright.sync_api import sync_playwright
src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
body = open(src).read(); assert 'window.__goTo = goTo;' in body
body = body.replace('window.__goTo = goTo;', 'window.__goTo = goTo; window.__T = { camera, controls, composer, renderer, scene };', 1)
tmp = '/tmp/_webclose.html'; open(tmp, 'w').write(body)
C = {'tentacles': ((48, -62, 104), (24, -14, 86)), 'tail': ((8, -72, 22), (-6, -16, 9)), 'tailfill': ((-34, -62, 34), (-20, -14, 20)), 'rear': ((-12, 72, 74), (-6, 14, 62))}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--allow-file-access-from-files'])
    pg = b.new_page(viewport={'width': 800, 'height': 600}, device_scale_factor=1)
    pg.goto('file://' + tmp); pg.wait_for_function('window.__ready === true && window.__T', timeout=300000)
    pg.evaluate("""() => { for (const id of ['ui','info','loading']) { const e = document.getElementById(id); if (e) e.style.display = 'none'; }
      const T = window.__T; window.__setRotate && window.__setRotate(false); T.renderer.setAnimationLoop(null); T.controls.enableDamping = false; }""")
    for k, (loc, tgt) in C.items():
        url = pg.evaluate("""([l, t]) => { const T = window.__T; let m = null; T.scene.traverse(o => { if (o.isMesh && !m) m = o; });
            const W = (v) => { const q = m.parent.localToWorld(new m.position.constructor(v[0], v[2], -v[1])); return q; };
            const P = W(l), G = W(t); T.camera.position.copy(P); T.controls.target.copy(G); T.camera.lookAt(G); T.camera.near = 0.05; T.camera.updateProjectionMatrix();
            T.composer.render(); return T.renderer.domElement.toDataURL('image/png'); }""", [loc, tgt])
        open(f'{out}/{k}.png', 'wb').write(base64.b64decode(url.split(',', 1)[1])); print('web closeup', k, flush=True)
    b.close()
