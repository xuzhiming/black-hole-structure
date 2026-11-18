# contact sheet v13: per view 原图 REF | v11 | v12 | v13, then a funnel close-up strip (ref funnel crop | v11 | v12 | v13 close-ups), footer
# + funnel_closeup_compare.png: row 1 front-view funnel crops (ref / v11 / v12 / v13), row 2 Cycles close-ups, row 3 web close-ups
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
VER = [('v11/', 'v11'), ('v12/', 'v12'), ('', 'v13 波纹')]
names = [('front', '正立面 FRONT'), ('rear', '背立面 REAR'), ('left', '左立面 LEFT'), ('right', '右立面 RIGHT'), ('top', '俯视图 TOP'), ('axo', '轴测 AXO')]
M = json.load(open(R + 'verify.json'))
c = 320; pad = 8; hdr = 64; W = 2 * (4 * c + 5 * pad)
grid = Image.new('RGB', (W, hdr + 3 * (c + 32)), BG); d = ImageDraw.Draw(grid)
d.text((20, 10), f"黑洞构筑体 · 原图 vs v11 vs v12 vs v13（{M['tris']:,} 面 · v13 = v12 + 恢复漏斗螺旋波纹）· Blender Cycles", fill=(60, 40, 40), font=F(30))
for i, (n, lab) in enumerate(names):
    x0 = (i % 2) * (4 * c + 5 * pad) + pad; y = hdr + (i // 2) * (c + 32)
    for j, (src, tl) in enumerate([(R + f'ref/{n}.png', '原图 REF')] + [(R + f'{b}renders/{n}.png', t) for b, t in VER]):
        x = x0 + j * (c + pad); grid.paste(fit(Image.open(src), c), (x, y + 26)); d.rectangle([x, y + 26, x + c - 1, y + 25 + c], outline=(200, 190, 175))
        d.text((x + 4, y + 2), f'{lab} · {tl}', fill=(110, 30, 130) if j == 3 else (60, 40, 40), font=F(18))
# funnel crops
REFC = (193, 137, 343, 287); FRC = (250, 250, 650, 650); CLC = (880, 40, 1600, 1000)
def funnel_row(kind, s):
    out = []
    if kind == 'front':
        out.append(('原图 REF 漏斗', Image.open(R + 'ref/front.png').crop(REFC)))
        out += [(t, Image.open(R + f'{b}renders/front.png').crop(FRC)) for b, t in VER]
    elif kind == 'close':
        out.append(('原图 REF 漏斗', Image.open(R + 'ref/front.png').crop(REFC)))
        out += [(t, Image.open(R + f'{b}renders/closeup.png').crop(CLC)) for b, t in VER]
    else:
        out.append(('原图 REF 轴测', Image.open(R + 'ref/axo.png')))
        out += [(t + ' web', Image.open(R + f'{b}web/preview_screenshot_close.png')) for b, t in VER]
    return [(t, fit(im, s, (14, 10, 18))) for t, im in out]
s2 = (W - 5 * pad) // 4
strip = Image.new('RGB', (W, s2 + 100), (18, 14, 22)); ds = ImageDraw.Draw(strip)
ds.text((14, 8), '漏斗细节 FUNNEL CLOSE-UP（Cycles 近景）', fill=(230, 210, 255), font=F(26))
for j, (t, im) in enumerate(funnel_row('close', s2)):
    x = pad + j * (s2 + pad); strip.paste(im, (x, 44)); ds.text((x + 8, 50), t, fill=(240, 225, 255), font=F(24))
s_ = M['bbox_size']
ds.text((14, s2 + 56), f"v13 bbox {s_[0]:.1f} × {s_[1]:.1f} × {s_[2]:.1f} m · tris {M['tris']:,} · core Ø{sum(M['core_diameter_measured_4dirs'])/4:.1f} m · ring Ø{M['ring_d_param'][0]:.0f} m · hole centre Z {M['hole_centre_xz_from_core'][1]:.1f} m · recess {M['recess_front_face_to_core_mouth']:.1f} m",
        fill=(220, 210, 235), font=F(22))
out = Image.new('RGB', (W, grid.height + strip.height)); out.paste(grid, (0, 0)); out.paste(strip, (0, grid.height))
out.save(R + 'contact_sheet.png'); print(R + 'contact_sheet.png', out.size)
# funnel close-up comparison
s3 = 520; W3 = 4 * s3 + 5 * pad; rows = [('front', '正视漏斗 front-view crop'), ('close', 'Cycles 近景 close-up'), ('web', '网页近景 web close-up')]
fc = Image.new('RGB', (W3, 70 + len(rows) * (s3 + 40)), (18, 14, 22)); df = ImageDraw.Draw(fc)
df.text((14, 14), '黑洞构筑体 漏斗对比 · 原图 vs v11（波纹·均匀紫）vs v12（细条纹·无波纹）vs v13（细条纹 + 螺旋波纹 + 洋红内环）', fill=(240, 225, 255), font=F(28))
for i, (k, lab) in enumerate(rows):
    y = 70 + i * (s3 + 40); df.text((14, y), lab, fill=(200, 180, 225), font=F(24))
    for j, (t, im) in enumerate(funnel_row(k, s3)):
        x = pad + j * (s3 + pad); fc.paste(im, (x, y + 36)); df.text((x + 8, y + 42), t, fill=(255, 235, 255), font=F(24))
fc.save(R + 'funnel_closeup_compare.png'); print(R + 'funnel_closeup_compare.png', fc.size)
