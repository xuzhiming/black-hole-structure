# headless check: open web/preview.html via file://, collect console errors, wait for model, screenshot (hero + front)
import sys, time, os
from playwright.sync_api import sync_playwright
R = '/workspace/outputs/black_hole_structure/'
url = 'file://' + R + 'web/preview.html'
errs, logs = [], []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1600, 'height': 1000})
    pg.on('console', lambda m: (errs if m.type == 'error' else logs).append(f'{m.type}: {m.text}'))
    pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
    pg.on('requestfailed', lambda r: errs.append('requestfailed: ' + r.url))
    t0 = time.time(); pg.goto(url)
    pg.wait_for_function('window.__ready === true', timeout=180000)
    print('ready in %.1fs' % (time.time() - t0))
    pg.evaluate('window.__setRotate(false)')
    time.sleep(3); pg.screenshot(path=R + 'web/preview_screenshot.png')
    pg.evaluate("window.__goTo('front')"); time.sleep(3); pg.screenshot(path=R + 'web/preview_screenshot_front.png')
    pg.evaluate("window.__goTo('left')"); time.sleep(3); pg.screenshot(path=R + 'web/preview_screenshot_left.png')
    pg.evaluate("window.__goTo('close')"); time.sleep(3); pg.screenshot(path=R + 'web/preview_screenshot_close.png')
    b.close()
print('console errors:', len(errs)); [print('  ', e) for e in errs]
print('other console:', logs[:10])
