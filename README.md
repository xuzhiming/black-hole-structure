# 黑洞构筑体 · Black Hole Structure

**在线预览 / Live demo:** https://black-hole-structure.pages.dev

根据参考效果图，用 Blender（Python 脚本，bpy 5.3 无界面运行）程序化生成的"黑洞构筑体"3D 模型，附带基于 Three.js 的网页查看器。查看器支持环绕、辉光和中英文尺寸标注。
A procedural "black hole structure" 3D model generated in Blender (headless bpy 5.3 Python scripts) from a reference sheet, with a Three.js web viewer (orbit, bloom, CN/EN dimension overlay).

规格 / Spec: 包围盒 bbox 100 × 48 × 120 m（原点在底面中心，Z 轴向上，正面朝 −Y）· 洞口 opening Ø40 m 外环 / Ø26 m 内核，洞心 Z = 58 m，凹入 18 m · 约 248 万三角面 ~2.48M tris。

![contact sheet](contact_sheet.png)

## 目录 / Layout

| 路径 Path | 说明 Description |
|---|---|
| `src/` | 建模、贴图、场景/渲染、校验、拼图、网页构建脚本 · build / texture / scene+render / verify / contact-sheet / web scripts |
| `model.blend` | Blender 源文件（完整精度）· Blender source file (full detail) |
| `web/preview.html` | 网页查看器（已内嵌压缩模型，可离线打开）· Web viewer (compressed model embedded, works offline) |
| `web/model_web.glb` | 网页用压缩模型（简化 50% + meshopt + WebP）· Web-optimized model |
| `web/preview_screenshot*.png` | 无界面 Chrome 测试截图 · Headless-Chrome test screenshots |
| `renders/hero.png`, `renders/closeup.png` | Cycles 透视主图 / 细节特写 · Cycles hero / close-up renders |
| `contact_sheet.png` | 参考图与 v4 / v5 各视图对比 · Reference vs v4 vs v5 per view |
| `tex/`, `ref/` | 程序化贴图与参考图裁切 · Procedural textures and reference crops |
| `measure.json`, `verify.json` | 尺寸实测 · Measured dimensions |

完整的 `model.glb`（约 112 MB，超过 GitHub 的 100 MB 上限）未提交，可用下面的命令重新生成。
The full-res `model.glb` (~112 MB, over GitHub's 100 MB limit) is not committed; regenerate it with the commands below.

## 重新生成 / Rebuild

```bash
python3 src/texture.py && SAMPLES=64 python3 src/scene.py   # textures -> mesh -> model.blend / model.glb / renders/
python3 src/verify.py && python3 src/sheet.py              # verify.json, contact_sheet.png
bash src/rebuild_web.sh && python3 src/test_preview.py      # web/model_web.glb -> web/preview.html, headless test
```

## 部署 / Deployment

推送到 `main` 后，GitHub Actions 会把 `web/` 打包到 `dist/`（`preview.html` 作为 `index.html`），并部署到 Cloudflare Pages。
Every push to `main` triggers GitHub Actions, which copies `web/` into `dist/` (`preview.html` served as `index.html`) and deploys to Cloudflare Pages.

需要的仓库 Secrets / Required repo secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.

---

## 版本记录 / Version notes


本地备份 `v1/` 至 `v4/` 未提交到仓库（v3 是放弃的分支）。v5 的几何与 v4 完全相同（build.py 未改，网格缓存复用），只调整了明暗和材质。

### v5 相对 v4 的改动（提亮）
- **贴图**：青铜底色约提亮 2.7 倍，偏炭灰紫；棱上的锈橙高光更宽、更亮；缝隙里的紫色更强。
- **Blender 材质**：
  - 顶点色铜色减半（与中性色 50% 混合），只有棱顶保持暖色。
  - 缝隙李子紫亮度约提高 2.4 倍；金属度 0.72→0.55，漫反射为主，不再整片发橙。
  - 孔边铜色减弱。
- **灯光**：主光 5→6.5，紫色轮廓光 1.6→2.4，环境光 0.22→0.35。
- **曝光**：正交视图 0.6→0.95，主图和特写 0.9→1.1。
- **网页**：toneMappingExposure 1.15→1.6；主光 3.2→4.6；新增正面补光；半球光 0.5→1.3；环境反射 0.8→1.3。
v4 以 v2 的源码为基础，保留 v2 的细节密度：卷头、分枝，以及主臂上的真实孔洞。

### v4 相对 v2 的改动（保留）
- **从 v3 带过来的安全修复**
  - 把向内的面翻正（管体原先是反向缠绕，这影响法线贴图和光照）。
  - 孔底改为不反光（Specular 0.04），去掉了灰色发白。
- **颜色**
  - 底色是炭黑偏紫的暗青铜。
  - 用两尺度 KD-tree 计算凹凸度，写入顶点色 `Tint`：只有最凸的棱边才是铜橙色，凹处偏紫。
  - Blender 中深缝隙再混入李子紫漫反射（属性 `Cav`，不发光）。
  - 贴图里锈色只出现在最高的棱上，孔边铜色减弱。
- **正面旋涡**
  - 11 条粗主臂从漏斗边缘起，沿更长的螺旋（2.3–2.9 rad）向外卷，主臂保留孔洞。
  - 主臂之间的槽里穿插 11 条细的紫脉臂。
  - 正面壳体的螺旋凸纹改成和主臂同样的扭转率，让沟槽加强旋涡的走向。
- **尾巴**
  - 只保留一条从右下绕到左下、末端 44 m 卷头的尾巴，材质为带孔青铜。
  - 去掉副尾巴；附着的小卷头从 9 个减到 4 个；尾巴区域的外围卷头减半；尾巴根部后移，保持侧面新月形。
- **漏斗**
  - 更深更暗：辉光底色近黑，隧道渐暗。
  - 条纹改为不规则、断续的亮纹，几何脊线用扭曲相位和噪声调幅生成，外加随机鼓包。
  - 新月凹勺加深（12→13 m）。
- **网页预览**：顶点色经 COLOR_0 带入（李子紫混合只在 Blender 里有）。v2 沿用同一套流程：bpy 5.3 无界面运行，1 BU = 1 m，Z 轴向上，正面朝 −Y，原点在包围盒底面中心。

### v2 相对 v1 的改动
- **卷头 / 分枝**：829 个蕨类卷头（曲率半径沿长度递减，成圆形涡卷），411 个二、三级分枝，共 970 条管体。
  - 轮廓周边 72 个大小不一的卷头，大的带拱形茎。
  - 另有 16 个角状卷头、7 根高冠茎，以及 160 个表面小卷头。
- **真实孔洞**：13,119 个几何凹坑（KD-tree 位移：碗形、唇边、凸瘤），共 43 万个暗色孔面和 17.7 万个铜锈色磨损唇边面。
  - 洞口附近 242 个孔底有紫色发光珠。
  - 细卷头尖端保持光滑，轮廓更清晰。
- **背部和顶部**：110 条分层叠压的触手，加上背面 18 条旋臂和大块隆起，俯视图呈厚重的堆叠体。
- **侧面**：新月凹勺更深（A_SCOOP 12 m）。隧道壁为发光材质，从洞内深处的黑渐变到洞口最亮。
- **漏斗**：紫色辉光漏斗，边缘有脊和有机凸起；洞口线和外环处有辉光带。
- **材质**：7 种材质，分别是青铜皮肤、紫脉、辉光、内核、暗孔、发光孔、铜锈边。
  - 法线强度 2.0，裂缝中的紫色更明显。
  - 贴图 2048，含 2000 个孔洞和 1400 个凸瘤。
- **渲染**：新增 `renders/closeup.png` 细节特写；`contact_sheet.png` 为三列对照：参考 / v1 / v2。
- **网页**：模型简化到 60%（约 143 万三角面），用 meshopt high 压缩，保证 html 小于 25 MB；新增"细节 Close-up"视角。

## 流程 / Pipeline
- `src/texture.py`：生成程序化 PBR 贴图。
- `src/build.py`：生成 numpy 网格。`python3 src/build.py --fast [--pores]` 做快速检查。
- `src/scene.py`：设置材质、灯光和 8 个相机，输出 model.blend、model.glb 和渲染图。
  - 网格缓存在 `/tmp/bh_mesh_<md5>.pkl`。
  - 可用环境变量：SAMPLES、ONLY、EXPO、EXPO_HERO。
- `src/verify.py`：用最终网格的顶点数值验证尺寸，结果写入 verify.json。
- `src/sheet.py`：拼出 contact_sheet.png。
- `src/rebuild_web.sh`：model.glb → dedup → resize 1024 → webp → simplify 0.6 → meshopt high → `web/preview.html`。
- `src/test_preview.py`：用无界面 Chrome 打开页面，检查 console，并截 hero / front / left / close 四张图。

完整重建命令：`python3 src/texture.py && SAMPLES=64 python3 src/scene.py && python3 src/verify.py && python3 src/sheet.py && bash src/rebuild_web.sh && python3 src/test_preview.py`
