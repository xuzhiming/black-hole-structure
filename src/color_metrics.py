# colour match metrics: object pixels of reference crops vs renders (same views). Lab means, copper / purple / dark fractions,
# L* and hue histogram intersections. Usage: python3 color_metrics.py renders_dir [label]  -> prints + writes color_metrics_<label>.json
import sys, json, numpy as np
from PIL import Image
R = '/workspace/outputs/black_hole_structure/'
def lab(rgb):
    c = rgb / 255.0; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)
def pix(path, box=None):
    im = Image.open(path).convert('RGB')
    im = im.resize((420, int(420 * im.height / im.width)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float64); bg = np.median(np.r_[a[:4].reshape(-1, 3), a[-4:].reshape(-1, 3)], 0)
    d = np.abs(a - bg).sum(2); m = d > 60
    # drop label text / lines: thin dark grey strokes on the beige sheet -> require a 3x3 solid neighbourhood
    from scipy.ndimage import binary_erosion, binary_dilation
    m = binary_dilation(binary_erosion(m, iterations=2), iterations=1) & m
    return a[m]
def stats(P):
    L = lab(P); hsv_h = np.degrees(np.arctan2(L[:, 2], L[:, 1])) % 360; C = np.hypot(L[:, 1], L[:, 2])
    mx = P.max(1); mn = P.min(1); sat = (mx - mn) / np.maximum(mx, 1)
    copper = (P[:, 0] > P[:, 2] * 1.45) & (P[:, 0] > 95) & (sat > 0.38)
    purple = (P[:, 2] > P[:, 1] * 1.25) & (P[:, 0] > P[:, 1] * 1.15) & (sat > 0.3) & (mx > 70)
    dark = L[:, 0] < 22
    return dict(n=int(len(P)), mean_rgb=P.mean(0).round(1).tolist(), L=round(float(L[:, 0].mean()), 1), L_p10_p50_p90=np.percentile(L[:, 0], [10, 50, 90]).round(1).tolist(),
                a=round(float(L[:, 1].mean()), 1), b=round(float(L[:, 2].mean()), 1), chroma=round(float(C.mean()), 1),
                copper_frac=round(float(copper.mean()), 3), purple_frac=round(float(purple.mean()), 3), dark_frac=round(float(dark.mean()), 3)), L, hsv_h, C
def hist_int(x, y, bins, rng, wx=None, wy=None):
    hx, _ = np.histogram(x, bins, rng, weights=wx); hy, _ = np.histogram(y, bins, rng, weights=wy)
    hx = hx / max(hx.sum(), 1e-9); hy = hy / max(hy.sum(), 1e-9); return round(float(np.minimum(hx, hy).sum()), 3)
if __name__ == '__main__':
    rdir = sys.argv[1]; label = sys.argv[2] if len(sys.argv) > 2 else 'x'
    out = {}; tot = []
    for v in ['front', 'rear', 'left', 'right', 'top', 'axo']:
        sr, Lr, hr, Cr = stats(pix(R + f'ref/{v}.png')); sm, Lm, hm, Cm = stats(pix(f'{rdir}/{v}.png'))
        dE = float(np.linalg.norm(np.array([sr['L'], sr['a'], sr['b']]) - np.array([sm['L'], sm['a'], sm['b']])))
        hi_L = hist_int(Lr, Lm, 20, (0, 100)); hi_h = hist_int(hr, hm, 24, (0, 360), np.minimum(Cr, 40), np.minimum(Cm, 40))
        out[v] = dict(ref=sr, model=sm, dE_mean_lab=round(dE, 1), hist_L=hi_L, hist_hue=hi_h); tot.append((dE, hi_L, hi_h))
    t = np.array(tot); out['avg'] = dict(dE_mean_lab=round(float(t[:, 0].mean()), 1), hist_L=round(float(t[:, 1].mean()), 3), hist_hue=round(float(t[:, 2].mean()), 3))
    json.dump(out, open(R + f'color_metrics_{label}.json', 'w'), indent=1)
    for v in out:
        if v == 'avg': print('AVG', out[v]); continue
        o = out[v]; print(f"{v:6s} ref L{o['ref']['L']:5.1f} a{o['ref']['a']:5.1f} b{o['ref']['b']:5.1f} cu{o['ref']['copper_frac']:.3f} pu{o['ref']['purple_frac']:.3f} dk{o['ref']['dark_frac']:.3f} | "
                          f"model L{o['model']['L']:5.1f} a{o['model']['a']:5.1f} b{o['model']['b']:5.1f} cu{o['model']['copper_frac']:.3f} pu{o['model']['purple_frac']:.3f} dk{o['model']['dark_frac']:.3f} | dE {o['dE_mean_lab']:4.1f} hL {o['hist_L']} hHue {o['hist_hue']}")
