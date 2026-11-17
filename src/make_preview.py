# embed the compressed GLB + bundled three.js into one self-contained web/preview.html (works from file://, offline)
import base64, json, os
r = '/workspace/outputs/black_hole_structure/'
t = open(r + 'src/web_template.html').read()
g = base64.b64encode(open(r + 'web/model_web.glb', 'rb').read()).decode()
three = open(r + 'src/vendor/three_bundle.js').read().replace('</script', '<\\/script')
M = json.load(open(r + 'measure.json'))
sz = M['bbox_size']
meta = dict(hole=M['hole_centre'], bbox=sz, tris=M['tris'])
out = (t.replace('__BBOX__', '%.0f × %.0f × %.0f' % tuple(sz)).replace('__TRIS__', '{:,}'.format(M['tris']))
        .replace('__META_JSON__', json.dumps(meta)).replace('__THREE_BUNDLE__', three).replace('__GLB_BASE64__', g))
open(r + 'web/preview.html', 'w').write(out)
print('preview.html', len(out))
