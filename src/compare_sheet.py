# before/after sheet: v6 (~497k) vs v7 (≤200k + baked normals + Draco) - Cycles renders + web preview screenshots
import json
from PIL import Image, ImageDraw, ImageFont
R = '/workspace/outputs/black_hole_structure/'
F = lambda s: ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', s)
v = json.load(open(R + 'verify.json'))
rows = [('renders/hero.png', 'Cycles 透视 HERO'), ('renders/closeup.png', 'Cycles 细节 CLOSE-UP'), ('renders/front.png', 'Cycles 正立面 FRONT'),
        ('web/preview_screenshot.png', 'Web 预览 preview'), ('web/preview_screenshot_close.png', 'Web 细节 close-up')]
cw, ch, hdr, lab = 1100, 690, 90, 34
out = Image.new('RGB', (2 * cw + 30, hdr + len(rows) * (ch + lab + 10)), (16, 12, 20)); d = ImageDraw.Draw(out)
d.text((14, 8), '黑洞构筑体 v6→v7 减至≤20万面 + 烘焙法线 · before / after', fill=(240, 225, 255), font=F(34))
d.text((14, 50), f"v6: 496,621 tris  →  v7: {v['tris']:,} tris (decimate {v.get('decimate_ratio',0.08)}) · baked normals · Draco", fill=(200, 180, 225), font=F(24))
def fit(im):
    im = im.convert('RGB'); k = min(cw / im.width, ch / im.height); im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    o = Image.new('RGB', (cw, ch), (16, 12, 20)); o.paste(im, ((cw - im.width) // 2, (ch - im.height) // 2)); return o
for i, (p, t) in enumerate(rows):
    y = hdr + i * (ch + lab + 10)
    for j, (base, tag) in enumerate([(R + 'v6/', 'v6 BEFORE'), (R, 'v7 AFTER')]):
        x = 10 + j * (cw + 10)
        d.text((x + 4, y), f'{tag} · {t}', fill=(255, 210, 160) if j else (190, 175, 210), font=F(24))
        out.paste(fit(Image.open(base + p)), (x, y + lab))
out.save(R + 'compare_v6_v7.png'); print(R + 'compare_v6_v7.png', out.size)
