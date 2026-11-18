# contact sheet v6: per view rows  REFERENCE crop | v5 (2.48M tris) | v6 (decimated) , then hero + close-up strip, measurements footer
import sys, json
from PIL import Image, ImageDraw, ImageFont
R = '/workspace/outputs/black_hole_structure/'
tag = sys.argv[1] if len(sys.argv) > 1 else ''
font_p = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
def F(s):
    try: return ImageFont.truetype(font_p, s)
    except Exception: return ImageFont.load_default()
names = [('front', '正立面 FRONT'), ('rear', '背立面 REAR'), ('left', '左立面 LEFT'),
         ('right', '右立面 RIGHT'), ('top', '俯视图 TOP'), ('axo', '轴测 AXO')]
c = 420; pad = 8; hdr = 70
W = 2 * (3 * c + 4 * pad)                      # two blocks of 3 columns side by side
rows = 3
grid = Image.new('RGB', (W, hdr + rows * (c + 34)), (236, 230, 219)); d = ImageDraw.Draw(grid)
_T = '{:,}'.format(json.load(open(R + 'verify.json'))['tris'])
d.text((20, 10), '黑洞构筑体 · 参考 vs v5 (2.48M 面) vs v6 减面 (__T__ 面) · Blender Cycles'.replace('__T__', _T), fill=(60, 40, 40), font=F(30))
def fit(im, s):
    im = im.convert('RGB'); k = min(s / im.width, s / im.height)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    out = Image.new('RGB', (s, s), (236, 230, 219)); out.paste(im, ((s - im.width) // 2, (s - im.height) // 2)); return out
for i, (n, lab) in enumerate(names):
    blk, row = i % 2, i // 2
    x0 = blk * (3 * c + 4 * pad) + pad; y = hdr + row * (c + 34)
    for j, (src, tl) in enumerate([(R + f'ref/{n}.png', '参考 REF'), (R + f'v5/renders/{n}.png', 'v5 2.48M'), (R + f'renders/{n}.png', 'v6 减面')]):
        x = x0 + j * (c + pad)
        grid.paste(fit(Image.open(src), c), (x, y + 26)); d.rectangle([x, y + 26, x + c - 1, y + 26 + c - 1], outline=(200, 190, 175))
        d.text((x + 4, y + 2), f'{lab} · {lab_}' if (lab_ := lab) and False else f'{lab}  ·  {tl}', fill=(60, 40, 40) if j < 2 else (110, 30, 130), font=F(20))
hero = Image.open(R + 'renders/hero.png').convert('RGB'); cl = Image.open(R + 'renders/closeup.png').convert('RGB')
hh = 620
hero = hero.resize((int(hero.width * hh / hero.height), hh), Image.LANCZOS); cl = cl.resize((int(cl.width * hh / cl.height), hh), Image.LANCZOS)
strip = Image.new('RGB', (W, hh + 90), (18, 14, 22)); ds = ImageDraw.Draw(strip)
k = W / (hero.width + cl.width + 10)
hero = hero.resize((int(hero.width * k), int(hh * k))); cl = cl.resize((W - hero.width - 10, int(hh * k)))
strip = Image.new('RGB', (W, hero.height + 90), (18, 14, 22)); ds = ImageDraw.Draw(strip)
strip.paste(hero, (0, 0)); strip.paste(cl, (hero.width + 10, 0))
ds.text((14, 10), 'v6 HERO 透视', fill=(230, 210, 255), font=F(28)); ds.text((hero.width + 24, 10), 'v6 CLOSE-UP 细节 (pores / copper rims / funnel ridges)', fill=(230, 210, 255), font=F(28))
try:
    M = json.load(open(R + 'verify.json')); s = M['bbox_size']
    ds.text((14, hero.height + 22), f"v6 bbox {s[0]:.1f} × {s[1]:.1f} × {s[2]:.1f} m · tris {M['tris']:,} · core Ø{sum(M['core_diameter_measured_4dirs'])/4:.1f} m · ring Ø{M['ring_d_param'][0]:.0f} m · hole centre Z {M['hole_centre_xz_from_core'][1]:.1f} m · recess {M['recess_front_face_to_core_mouth']:.1f} m",
            fill=(220, 210, 235), font=F(24))
except Exception as e: print('no verify', e)
out = Image.new('RGB', (W, grid.height + strip.height)); out.paste(grid, (0, 0)); out.paste(strip, (0, grid.height))
p = R + f'contact_sheet{tag}.png'; out.save(p); print(p, out.size)
