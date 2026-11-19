# deterministic 360° turntable of the live page: camera orbits the page's default (hero) view around the vertical axis
# through the orbit target, one rendered frame per step (no real-time recording). Resumable: skips frames already written.
import sys, os, time, base64
from playwright.sync_api import sync_playwright
W, H = int(os.environ.get('VW', 1920)), int(os.environ.get('VH', 1080)); N = int(os.environ.get('NF', 360))
OUT = os.environ.get('OUTDIR', '/workspace/outputs/black_hole_structure/video/frames'); only = [int(x) for x in sys.argv[1:]] or range(N)
URL = f'https://black-hole-structure.pages.dev/?cb={int(time.time())}'
def patch(route):
    r = route.fetch(); body = r.text()
    assert 'window.__goTo = goTo;' in body
    body = body.replace('window.__goTo = goTo;', 'window.__goTo = goTo; window.__T = { camera, controls, composer, renderer, scene };', 1)
    route.fulfill(response=r, body=body)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
    pg.route('https://black-hole-structure.pages.dev/?cb=*', patch)
    pg.goto(URL); pg.wait_for_function('window.__ready === true && window.__T', timeout=300000)
    pg.evaluate("""() => { for (const id of ['ui','info','loading']) { const e = document.getElementById(id); if (e) e.style.display = 'none'; }
      const T = window.__T; window.__setRotate(false); T.renderer.setAnimationLoop(null); T.controls.enableDamping = false;
      T.controls.update(); T.p0 = T.camera.position.clone(); T.t0 = T.controls.target.clone(); }""")
    time.sleep(1)
    print('start', pg.evaluate('[window.__T.p0.toArray(), window.__T.t0.toArray()]'), flush=True)
    for i in only:
        f = f'{OUT}/f{i:04d}.png'
        if os.path.exists(f): continue
        t = time.time()
        url = pg.evaluate("""(a) => { const T = window.__T; const v = T.p0.clone().sub(T.t0).applyAxisAngle(new THREE_Y(), a);
            return null; }""".replace('new THREE_Y()', 'T.camera.up.clone().set(0,1,0)'), 6.283185307179586 * i / N) if False else None
        url = pg.evaluate("""(a) => { const T = window.__T; const v = T.p0.clone().sub(T.t0); const c = Math.cos(a), s = Math.sin(a);
            T.camera.position.set(T.t0.x + v.x * c + v.z * s, T.t0.y + v.y, T.t0.z - v.x * s + v.z * c); T.camera.lookAt(T.t0);
            T.composer.render(); return T.renderer.domElement.toDataURL('image/png'); }""", 6.283185307179586 * i / N)
        open(f + '.tmp', 'wb').write(base64.b64decode(url.split(',', 1)[1])); os.replace(f + '.tmp', f)
        print('frame', i, round(time.time() - t, 2), flush=True)
    b.close()
