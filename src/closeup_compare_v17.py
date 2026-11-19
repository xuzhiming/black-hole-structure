# close-up comparison v16 vs v17 (Cycles: v17_closeups.py, web: web_closeups.py) -> closeups_v16_v17.png
import sys
from PIL import Image, ImageDraw, ImageFont
F = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 22)
K = [('tentacles', '卷须 tentacles'), ('tail', '尾巴 tail'), ('tailfill', '尾巴填充 tail-fill'), ('rear', '背面涡旋 rear vortex')]
rows = [('Cycles v16', sys.argv[1]), ('Cycles v17', sys.argv[2]), ('Web v16', sys.argv[3]), ('Web v17', sys.argv[4])]
w, h = 480, 360; out = Image.new('RGB', (len(K) * w + 150, len(rows) * h + 40), (20, 16, 24)); d = ImageDraw.Draw(out)
for i, (k, lab) in enumerate(K): d.text((150 + i * w + 8, 6), lab, fill=(235, 220, 255), font=F)
for j, (lab, dr) in enumerate(rows):
    d.text((8, 40 + j * h + h // 2 - 12), lab, fill=(235, 220, 255), font=F)
    for i, (k, _) in enumerate(K): out.paste(Image.open(f'{dr}/{k}.png').convert('RGB').resize((w, h), Image.LANCZOS), (150 + i * w, 40 + j * h))
out.save(sys.argv[5]); print(sys.argv[5], out.size)
