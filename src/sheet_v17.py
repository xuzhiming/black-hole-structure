# contact sheet v17: per view  原图 REF | v16 (v16/renders) | v17 Cycles render, then hero / reference funnel crop / close-up strip + measurements
import json
from PIL import Image, ImageDraw, ImageFont
R = '/workspace/outputs/black_hole_structure/'
def F(s):
    try: return ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', s)
    except Exception: return ImageFont.load_default()
BG = (236, 230, 219)
def fit(im, s, bg=BG):
    im = im.convert('RGB'); k = min(s / im.width, s / im.height)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    out = Image.new('RGB', (s, s), bg); out.paste(im, ((s - im.width) // 2, (s - im.height) // 2)); return out
names = [('front', '正立面 FRONT'), ('rear', '背立面 REAR'), ('left', '左立面 LEFT'), ('right', '右立面 RIGHT'), ('top', '俯视图 TOP'), ('axo', '轴测 AXO')]
M = json.load(open(R + 'verify.json'))
c = 400; pad = 10; hdr = 64; W = 2 * (3 * c + 4 * pad) + pad
grid = Image.new('RGB', (W, hdr + 3 * (c + 34)), BG); d = ImageDraw.Draw(grid)
d.text((20, 12), f"黑洞构筑体 v17 · 去折纸：圆润纤维 / 平滑低模 / 法线来自平滑源 · 原图 vs v16 vs v17 · {M['tris']:,} 面 · Blender Cycles", fill=(60, 40, 40), font=F(30))
for i, (n, lab) in enumerate(names):
    x0 = (i % 2) * (3 * c + 4 * pad) + pad; y = hdr + (i // 2) * (c + 34)
    for j, (src, tl) in enumerate([(R + f'ref_v14/{n}.png', '原图 REF'), (R + f'v16/renders/{n}.png', 'v16'), (R + f'renders/{n}.png', 'v17')]):
        x = x0 + j * (c + pad); grid.paste(fit(Image.open(src), c), (x, y + 28)); d.rectangle([x, y + 28, x + c - 1, y + 27 + c], outline=(200, 190, 175))
        d.text((x + 4, y + 2), f'{lab} · {tl}', fill=((120, 120, 120), (110, 30, 130))[j - 1] if j else (60, 40, 40), font=F(20))
hero = Image.open(R + 'renders/hero.png').convert('RGB'); cl = Image.open(R + 'renders/closeup.png').convert('RGB')
rz = Image.open(R + 'ref_v14/front.png').convert('RGB'); rz = rz.crop((int(rz.width * 0.33), int(rz.height * 0.3), int(rz.width * 0.8), int(rz.height * 0.72)))
hh = 520
def H(im): return im.resize((int(im.width * hh / im.height), hh), Image.LANCZOS)
hero, rz, cl = H(hero), H(rz), H(cl)
k = (W - 20) / (hero.width + rz.width + cl.width); hero, rz, cl = [im.resize((int(im.width * k), int(hh * k)), Image.LANCZOS) for im in (hero, rz, cl)]
strip = Image.new('RGB', (W, hero.height + 70), (18, 14, 22)); ds = ImageDraw.Draw(strip)
strip.paste(hero, (0, 0)); strip.paste(rz, (hero.width + 10, 0)); strip.paste(cl, (hero.width + rz.width + 20, 0))
ds.text((14, 8), 'v17 HERO 透视', fill=(230, 210, 255), font=F(26)); ds.text((hero.width + 22, 8), '原图细节 REF crop', fill=(255, 235, 255), font=F(24))
ds.text((hero.width + rz.width + 32, 8), 'v17 CLOSE-UP 卷须 / 孔洞 / 漏斗', fill=(230, 210, 255), font=F(26))
s_ = M['bbox_size']
ds.text((14, hero.height + 18), f"bbox {s_[0]:.1f} × {s_[1]:.1f} × {s_[2]:.1f} m · tris {M['tris']:,} · core Ø{sum(M['core_diameter_measured_4dirs'])/4:.2f} m · glow ring Ø{sum(M['glow_outer_diameter_4dirs'])/4:.2f} m · hole centre X {M['hole_centre_xz_from_core'][0]:.2f} Z {M['hole_centre_xz_from_core'][1]:.2f} m · recess (lip crest→core) {M.get('recess_lip_crest_to_core_mouth', 0):.2f} m",
        fill=(220, 210, 235), font=F(22))
out = Image.new('RGB', (W, grid.height + strip.height)); out.paste(grid, (0, 0)); out.paste(strip, (0, grid.height))
out.save(R + 'contact_sheet.png'); print(R + 'contact_sheet.png', out.size)
