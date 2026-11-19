# 黑洞构筑体 · Black Hole Structure

**在线预览 / Live demo:** https://black-hole-structure.pages.dev

根据参考效果图，用 Blender（Python 脚本，bpy 5.3 无界面运行）程序化生成的"黑洞构筑体"3D 模型，附带基于 Three.js 的网页查看器。查看器支持环绕、辉光和中英文尺寸标注。
A procedural "black hole structure" 3D model generated in Blender (headless bpy 5.3 Python scripts) from a reference sheet, with a Three.js web viewer (orbit, bloom, CN/EN dimension overlay).

规格 / Spec: 包围盒 bbox 100 × 48 × 120 m（原点在底面中心，Z 轴向上，正面朝 −Y）· 洞口 opening Ø40 m 外环 / Ø26 m 内核，洞心 Z = 58 m，凹入 18 m · **v11 = v10 大形（用户 GLB）+ 顺流鳞片 + 原图配色**，195,986 三角面（≤20 万），鳞片在稠密网格上生成并烘焙为法线 / AO / 铜边 / 缝隙贴图 + Draco · v11 = v10 form + flow-aligned scales baked to normal / AO / copper-edge / cavity maps + reference palette, 196k tris, Draco.

![contact sheet](contact_sheet.png)

## 目录 / Layout

| 路径 Path | 说明 Description |
|---|---|
| `src/` | 建模、贴图、场景/渲染、校验、拼图、网页构建脚本 · build / texture / scene+render / verify / contact-sheet / web scripts（v10: `prep_tex_v10.py`, `scene_v10.py`, `verify_v10.py`, `rend_common.py`）|
| `model.blend` | Blender 源文件（v11，9.8 MB）· Blender source (v11) |
| `model.glb` | v11 glTF，未压缩（22.5 MB）· v11 glTF, uncompressed |
| `model_draco.glb` | v11 + Draco（16.3 MB）· v11 + Draco |
| `tex/v11_*.jpg` | v11 贴图：反照率、MR、法线、AO、漏斗自发光 · v11 maps |
| `tex/v10_*.jpg` | v10 贴图：GLB 反照率调色、MR、漏斗自发光、烘焙法线 / AO · v10 maps: graded GLB albedo, MR, funnel emission, baked normal / AO |
| `web/preview.html` | 网页查看器（已内嵌压缩模型，可离线打开）· Web viewer (compressed model embedded, works offline) |
| `web/model_web.glb` | 网页用模型（Draco + 2048 WebP，2.5 MB）· Web model (Draco + 2048 WebP) |
| `web/preview_screenshot*.png` | 无界面 Chrome 测试截图 · Headless-Chrome test screenshots |
| `renders/hero.png`, `renders/closeup.png` | Cycles 透视主图 / 细节特写 · Cycles hero / close-up renders |
| `contact_sheet.png` | 原图 vs v10 vs v11 六视图 + 细节对比 · Reference vs v10 vs v11, six views + close-up vs reference crop |
| `compare_v10_v11.png` | v10→v11 对比 · v10→v11 before / after |
| `color_metrics_v10.json`, `color_metrics_v11.json` | 与原图的颜色指标（Lab / 铜色 / 紫色 / 暗部占比）· colour metrics vs the reference |
| `tex/`, `ref/` | 程序化贴图与参考图裁切 · Procedural textures and reference crops |
| `measure.json`, `verify.json` | 尺寸实测 · Measured dimensions |

v7 起默认 `DECIMATE=0.08`（≤20 万面）并烘焙法线；`model.glb`（24.2 MB）已提交。设 `DECIMATE=1` 可生成完整版 `model_full.glb`（约 112 MB，忽略不提交）。
Default is `DECIMATE=0.08` (≤200k) + baked normals; `model.glb` (24.2 MB) is committed. `DECIMATE=1` writes ignored `model_full.glb` (~112 MB).

## 重新生成 / Rebuild

```bash
# v11 (cached stages, each resumable; cache in /tmp/v11):
blender -b --python src/v11_stageA.py      # v10 geometry -> A.blend + dense/low arrays
python3 src/scales_v11.py                  # scale field (displacement + masks)
blender -b --python src/v11_stageB.py      # displace + bake normal / col1 / col2 / AO (skips cached bakes)
RIM_LO=0.1 RIM_HI=0.5 python3 src/compose_v11.py && SAMPLES=64 blender -b --python src/v11_stageD.py
python3 src/verify_v10.py && python3 src/color_metrics.py renders v11 && python3 src/sheet.py && bash src/rebuild_web.sh && python3 src/test_preview.py && python3 src/compare_sheet.py
# v10 (needs the user's GLB at ref_glb/user_tripo.glb, kept out of git):
GRADE=0.75 ALB_CON=1.15 python3 src/prep_tex_v10.py && SAMPLES=64 blender -b --python src/scene_v10.py
python3 src/verify_v10.py && python3 src/sheet.py && bash src/rebuild_web.sh && python3 src/test_preview.py && python3 src/compare_sheet.py
# v9 and earlier (procedural):
python3 src/texture.py && SAMPLES=64 python3 src/scene.py   # textures -> mesh -> model.blend / model.glb / renders/
python3 src/verify.py && python3 src/sheet.py              # verify.json, contact_sheet.png
bash src/rebuild_web.sh && python3 src/test_preview.py      # model_draco.glb, web/model_web.glb (Draco) -> web/preview.html, headless test
python3 src/compare_sheet.py                               # compare_v5_v6.png
```

## 部署 / Deployment

推送到 `main` 后，GitHub Actions 会把 `web/` 打包到 `dist/`（`preview.html` 作为 `index.html`），并部署到 Cloudflare Pages。
Every push to `main` triggers GitHub Actions, which copies `web/` into `dist/` (`preview.html` served as `index.html`) and deploys to Cloudflare Pages.

需要的仓库 Secrets / Required repo secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.

---

## 版本记录 / Version notes

### v15：修正左右镜像 + 粗尾 + 纤维层叠 / handedness fix, heavy tail, fibrous lamellae
- **尾巴哪里反了**：全局坐标是对的（正视图右手 = +X，正面朝 −Y；背视图右手 = −X），但 v14 的卷须布局整体左右镜像了：
  - 尾巴：原图从洞口下方偏右（X≈+18）离开主体，沿底部扫向左，在左端（X≈−45）向上卷成顺时针（正视）浪头。v14 正好相反：根在左下，扫向右，右下末端逆时针卷。
  - 正面螺旋臂：原图顺时针向外扭出，v14 是逆时针。
  - 背面涡旋：原图从背面看顺时针内旋、涡心在背视图偏右（X≈−6），v14 方向相反。
  - 修正：`src/v15_geom.py` 在拟合包围盒前把所有卷须的 X 取反（洞口在 X=0，不受影响），尾巴、螺旋臂、背面涡旋、边缘卷须的旋向一起改对。
- **参考 SVG（`ref_svg/`）**：`svg_a` 是正视图的矢量描摹，透明背景，用它的 alpha 作精确正视轮廓遮罩（缩放到 100 × 120 m）。尾巴中心线（根 X≈+18 Z≈24 → 最低点 X≈−15 Z≈3.6 → 浪头 X≈−45 Z≈17.5）、右下钩形卷、右上高冠卷都按遮罩重新摆放。正视轮廓 IoU：v14 0.766 → v15 0.803（对比图 `silhouette_svg_a_vs_v15.png`：灰 = 重合，红 = 只有原图，蓝 = 只有模型）。同时用它确认了尾巴方向和卷曲旋向。`svg_b` 是六视图尺寸图，与 `ref_v14` 一致，用来核对。
- **粗尾**：根部 Ø12 m，逐渐收细到 Ø6.4 m，末端涡卷 1.75 圈收到 Ø0.75 m。外面缠两股绳状辅卷（各 2 圈），表面带孔洞。
- **纤维 / 层叠雕刻**（几何，进 SDF）：每条半径 > 0.9 m 的卷须按平行移动标架加平行纤维槽（间距约 1.5 m，略带扭转），并沿弧长加叠层台阶（片距 1.6–4 m，边缘呈扇贝形）。表面保持光滑，孔洞保留。背面涡旋细股带铜色斑点。
- **其他**：
  - 冠部卷须移到右上，拉伸上限 1.03，轮廓不再方。
  - 漏斗洋红更亮（MAG_GAIN 1.25、MAG_MIX 0.55、RING_GAIN 0.5），并加了少量发光沟缝。
  - 铜色压到约 3–4%（CR_LO 0.84、CU_W 0.45）。
  - 凹入深度改按唇口顶（每 10° 扇区最前的发光面）测量。
- **尺寸**：
  - 包围盒 100.0 × 48.0 × 120.0 m；洞口中心 (0.00, 58.00)。
  - 黑核 Ø26.00 ×4；发光环 Ø40.53。
  - 凹入（唇口顶 → 核口）**18.00 m**；v14 用的中位数窗口测法为 17.24 m。
  - 三角面 195,264。
- **颜色**（对 `ref_v14`）：
  - ΔE 平均 2.7（正视 2.1、背 3.3、左 3.2、右 2.8、顶 1.7、轴测 3.1）；L* 直方图交叠 0.899，色相 0.671。
  - 铜色占比：正视 3.7%、背 3.2%、左 3.6%、右 4.3%、顶 5.8%、轴测 5.0%。
  - 正视紫色 9.4%（原图 6.0%）。网页正视：紫色 7.6%、铜色 5.7%、ΔE 3.2。
- **流程**：`set -a; . src/v15_params.env; set +a` → `python3 src/v15_geom.py` → `blender -b --python src/v14_stageL.py` → `blender -b --python src/v14_stageB.py` → `python3 src/compose_v15.py` → `SAMPLES=64 blender -b --python src/v11_stageD.py` → `python3 src/verify_v10.py` → `bash src/rebuild_web.sh` → `python3 src/sheet_v15.py`。v14 备份在 `v14/`。

| 文件 File | v15 |
|---|---|
| `model.glb` | 23.8 MB |
| `model_draco.glb` | 17.6 MB |
| `web/model_web.glb` | 2.7 MB |
| `web/preview.html` | 4.7 MB |
| `model.blend` | 7.4 MB |

### v14：新效果图精细重建（程序化） / fine procedural reconstruction of the new reference sheet
- **参考**：`ref_v14/reference_sheet.png` + `ref_v14/spec.md`（数值优先于像素）。六视图裁图在 `ref_v14/*.png`。v13 备份在 `v13/`（不提交）。
- **建模方式（全部程序化，`src/v14_geom.py`）**：带符号距离场（0.25 m 体素，约 5000 万格）→ marching cubes 得到约 174 万面的高模，表面连续光滑，无折纸感。组成部分：
  - 碟形主壳：正面内凹、背面外凸，主要绕 X 轴弯曲，所以侧视是月牙形（上下尖端前伸，中部内收到入口平面）。
  - 正面 10 条主螺旋卷须（根部 Ø8.8–10.4 m）从漏斗内部向外扭出到边缘，末端卷成涡卷；另有 10 条细卷须嵌在沟里。
  - 背面 16 条细股组成大螺旋涡，涡心另有一个大卷。
  - 一条长尾卷须从左下沿底部扫向右下，末端向上卷起，外面缠一股绳状辅卷；左下另有一个钩形卷。
  - 34 个边缘卷须（涡卷收到末端 Ø0.75 m）。
  - 约 2,480 个多孔气泡状孔，带圆滑边缘；另加两层低幅凹凸噪声。
  - 漏斗切削：入口平面 Y = −9 m 处为 Ø40 唇口，沿 +Y 18 m 到 Y = +9 m 的 Ø26 黑核口。
  - 卷须布局先在漏斗区域之外拟合到包围盒，再生成距离场。
- **流程**：G 几何（`v14_geom.py`）→ L（`v14_stageL.py`：材质分区、减面到约 19.5 万面且保护漏斗、Ø26 缝精确吸附、smart UV、从高模传递自定义法线）→ B（`v14_stageB.py`：4096 切线法线、凸度 / 孔洞遮罩、16 位世界坐标、AO 烘焙）→ C（`compose_v14.py`：暗栗棕本体、凸脊铜色、孔洞和沟缝深梅黑；漏斗用 v13 的螺旋波纹 + 细条纹 + 洋红口环；漏斗附近沟缝和孔洞带微弱紫光）→ D（`v11_stageD.py`，`TAG=v14`，可选皮肤发光）→ `rebuild_web.sh`（Draco）→ `sheet_v14.py`。参数在 `src/v14_params.env`。
- **尺寸检查**（`verify.json`，从 model.glb 独立测量）：
  - 包围盒 100.0 × 48.0 × 120.0 m，X −50…50、Y −24…24、Z 0…120。
  - 洞口中心 X 0.00、Z 58.00。
  - 黑核 Ø26.00（4 个方向）；发光环外径 Ø40.53。
  - 凹入深度：建模平面 Y −9 → +9 为 18 m；网格测得唇口顶点中位数 Y -8.26 → 核口 8.98，即 17.24 m（唇口倒圆使测量值偏小）。
  - 三角面 195,394。
- **颜色**（与 `ref_v14` 裁图对比）：平均 ΔE 2.8；L* 直方图交叠 0.895；色相直方图交叠 0.617。正视紫色占比 8.3%（原图 6.0%）；网页正视紫色 6.3%。

| 文件 File | v14 |
|---|---|
| `model.glb` | 21.1 MB |
| `model_draco.glb` | 15.6 MB |
| `web/model_web.glb` | 2.3 MB |
| `web/preview.html` | 4.2 MB |
| `model.blend` | 7.2 MB |

### v13：保留漏斗波纹 / funnel ripples restored
- **为什么 v12 没有波纹**：v11 的波纹来自稠密网格上的漏斗位移（`0.2 × (ripple − 0.15)`，烘焙进法线贴图），以及同一个 ripple 信号驱动的反照率和发光。v12 为了画更细的条纹，把这部分位移和逐顶点 ripple 一起换成了逐纹素细条纹，所以波纹消失了。
- **v13 = v12 + v11 波纹**：新的 `src/ripple_v13.py` 重新实现 v11 的波纹公式（环距 0.95 m，角向噪声让环呈波浪状，再断成碎段），被两处共用：`src/scales_v13.py` 把它作为漏斗真实起伏烘焙进 4096 法线；`src/compose_v13.py` 用同一公式逐纹素生成发光和反照率，几何和颜色对得上。v11 用 2.2 圈扭转（非整数，θ = ±π 处有接缝）；v13 改为整数 `SWIRL=3`，形成连续、无接缝的三臂内旋螺旋。v12 的暗色漏斗、细螺旋条纹和 Ø26 口的洋红内环都保留（条纹增益 1.1→0.45，波纹发光 1.3，漏斗高光 GSPEC 0.1）。鳞片和身体与 v12 完全相同（scale field / col1 / col2 逐字节一致，只重烘了法线和 AO）。
- **紫色和指标**：网页正视紫色占比 6.8%（原图 6.1%；v11 11.7%，v12 5.3%），网页 ΔE 2.6；网页辉光默认值 1.8→1.0。Cycles 正视紫色 6.7%。平均 ΔE 3.4（v12 3.4，v11 3.8）；L* 直方图交叠 0.860；色相直方图交叠 0.619。
- 对比图：`contact_sheet.png`（原图 / v11 / v12 / v13 六视图 + 漏斗近景）、`funnel_closeup_compare.png`（正视漏斗裁图 / Cycles 近景 / 网页近景）。
- 重新生成：`set -a; . src/v13_params.env; set +a`，然后 `python3 src/scales_v13.py` → `blender -b --python src/v11_stageB.py`（col1 / col2 可复用 v12 的烘焙）→ `python3 src/compose_v13.py` → `blender -b --python src/v11_stageD.py` → `bash src/rebuild_web.sh` → `python3 src/sheet_v13.py`。

| 文件 File | v12 | v13 |
|---|---|---|
| 三角面 Tris | 195,986 | 195,986 |
| `model.glb` | 24.5 MB | 24.6 MB (23.5 MiB) |
| `model_draco.glb` | 18.3 MB | 18.4 MB |
| `web/model_web.glb` | 2.9 MB | 2.9 MB |
| `web/preview.html` | 5.0 MB | 5.0 MB |

### v12：漏斗细螺旋条纹 + 更薄更锐的带状鳞片 / fine funnel streaks + crisper strap scales
- **大形不变**：GLB 大形、洞口规格（外环 Ø40、内核 Ø26、中心 Z=58、凹入 18 m）、包围盒 100 × 48 × 120 m、195,986 三角面、平滑流程不变。v11 备份在 `v11/`（不提交）。
- **漏斗（重点）**：条纹宽约 0.5 m，比稠密网格顶点间距（约 0.2 m）配合 0.42 m 环宽能表达的更细，所以 v12 不再按顶点存条纹，而是把漏斗的极坐标（r/40、cosθ、sinθ）用 **16 位 PNG 烘焙到 4096**（`COL2_HI=1`），在 `src/compose_v12.py` 中逐纹素生成条纹：相位 `r/0.5 + 3θ/2π`（整数圈，无接缝）向内螺旋，每条条纹亮度随机、沿长度断续。整体以暗色为主，条纹向外渐暗，Ø26 口处为洋红 / 热紫内环。去掉了 v11 的均匀紫色和规则波浪带。网页洞内补光 2200→300（更短的衰减距离），身体褶皱上不再有紫色反光。
- **鳞片**：板更薄（SA 0.95 / SB 0.36）、自由边抬起更锐、缝隙更清楚，`col1.B` 改为板顶遮罩，板顶带灰蓝色光泽（SHEEN_W 0.3）。铜边阈值重调，铜色占比：顶视 8.3%→3.4%、轴测 6.7%→4.6%（原图约 3.7%）。背光改暖（RIM 3.6），背 / 右 L* 16.1 / 17.9 → 21.8 / 21.7（原图 21.2 / 22.0）。顶 / 左 / 轴测视图用每视图曝光补偿（`EXPO_TOP` 等，见 `src/v12_params.env`）。
- **颜色指标**：平均 ΔE v11 3.8 → v12 **3.4**；L* 直方图交叠 0.874 → 0.862；色相直方图交叠 0.611 → 0.624。网页正视：紫色占比 11.7% → **5.3%**（原图 6.1%），ΔE 4.9 → **2.4**。
- 重新生成：`set -a; . src/v12_params.env; set +a`，然后 `python3 src/scales_v12.py` → `COL2_RES=4096 COL2_HI=1 blender -b --python src/v11_stageB.py` → `python3 src/compose_v12.py` → `blender -b --python src/v11_stageD.py` → `bash src/rebuild_web.sh`。

| 视图 View | ΔE v11 | ΔE v12 | L* 原图 / v11 / v12 | 铜色 copper 原图 / v11 / v12 | 紫色 purple 原图 / v12 |
|---|---|---|---|---|---|
| front | 1.3 | 2.6 | 20.7 / 19.9 / 22.7 | 0.039 / 0.049 / 0.039 | 0.061 / 0.038 |
| rear | 5.5 | 3.3 | 21.2 / 16.1 / 21.8 | 0.032 / 0.021 / 0.022 | 0.011 / 0.000 |
| left | 3.5 | 3.8 | 20.8 / 23.1 / 22.9 | 0.027 / 0.047 / 0.016 | 0.051 / 0.000 |
| right | 5.0 | 2.8 | 22.0 / 17.9 / 21.7 | 0.028 / 0.023 / 0.010 | 0.045 / 0.001 |
| top | 5.4 | 4.9 | 23.2 / 25.8 / 24.3 | 0.037 / 0.083 / 0.034 | 0.032 / 0.000 |
| axo | 1.8 | 3.0 | 22.7 / 23.6 / 24.7 | 0.038 / 0.067 / 0.046 | 0.061 / 0.032 |

| 文件 File | v11 | v12 |
|---|---|---|
| 三角面 Tris | 195,986 | 195,986 |
| `model.glb` | 22.5 MB | 24.5 MB (23.4 MiB) |
| `model_draco.glb` | 16.3 MB | 18.3 MB |
| `web/model_web.glb` | 2.5 MB | 2.9 MB |
| `web/preview.html` | 4.5 MB | 5.0 MB |

### v11：鳞片 + 原图配色 / scales + reference palette
- **大形不变**：v10 的 GLB 大形、洞口规格、包围盒和 195,986 三角面保持不变（分阶段缓存流程：A 几何 → F 鳞片场 → B 烘焙 → C 合成贴图 → D 材质 / 导出 / 渲染）。
- **鳞片**：在 2 级细分稠密网格（111 万顶点）上生成两层重叠鳞片：大鳞约 2.6 m（4,529 片）、小鳞约 1.15 m（23,762 片）。每片是沿流向拉长的椭圆，自由边抬起，最高的一片覆盖下面的，形成叠瓦；其中 20% 是中间有凹坑的开口鳞。流向：触须 / 卷须按 PCA 主轴，其余按指向洞口的螺旋。位移约 ±0.5 m，烘焙成 4096 切线法线、AO，以及铜边 / 缝隙 / 高度遮罩。低模加了 ±0.1 m 的轻微真实位移（平滑处理），不会出现折纸感。
- **配色**：反照率在 UV 空间重做：近黑的青铜炭色本体（GLB 原图只保留低饱和的大尺度变化，所以身体褶皱上不再有紫色杂纹），鳞片自由边 / 凹坑边缘 / 卷须脊为铜色，缝隙和凹坑为深梅紫。本体粗糙度 0.36、铜边更金属，高光更锐利。漏斗是暗紫底加碎条纹紫光，靠近 Ø26 口偏洋红、向外变暗；去掉了漏斗的灰色高光，洞内补光 1200→300。
- **颜色指标**（`src/color_metrics.py`，与原图同视角裁图对比物体像素，ΔE 为 Lab 均值差）：平均 ΔE v10 8.4 → v11 **3.8**；L* 直方图交叠 0.842 → 0.874；色相直方图交叠 0.676 → 0.611。网页正视（深色背景、曝光 1.8）：ΔE 5.5 → 4.9。

| 视图 View | ΔE v10 | ΔE v11 | L* 原图 / v10 / v11 | 铜色占比 copper 原图 / v10 / v11 |
|---|---|---|---|---|
| front | 8.3 | 1.3 | 20.7 / 28.0 / 19.9 | 0.039 / 0.078 / 0.049 |
| rear | 5.3 | 5.5 | 21.2 / 21.5 / 16.1 | 0.032 / 0.039 / 0.021 |
| left | 7.7 | 3.5 | 20.8 / 28.1 / 23.1 | 0.027 / 0.039 / 0.047 |
| right | 1.0 | 5.0 | 22.0 / 22.4 / 17.9 | 0.028 / 0.009 / 0.023 |
| top | 14.5 | 5.4 | 23.2 / 35.9 / 25.8 | 0.037 / 0.131 / 0.083 |
| axo | 13.4 | 1.8 | 22.7 / 34.5 / 23.6 | 0.038 / 0.125 / 0.067 |

| 文件 File | v10 | v11 |
|---|---|---|
| 三角面 Tris | 195,986 | 195,986 |
| `model.glb` | 22.9 MB | 22.5 MB |
| `model_draco.glb` | 16.7 MB | 16.3 MB |
| `web/model_web.glb` | 2.1 MB | 2.5 MB |
| `web/preview.html` | 3.9 MB | 4.5 MB |

### v10：按用户 GLB 重建 / rebuilt from the user's GLB
- **来源**：用户提供的 Tripo GLB（31.3 MB，不入库）。它是单个网格，92,822 三角面 / 77,460 顶点（焊接后 46,423，8 个连通块），Y 轴向上，正面 +Z，原尺寸 82.8 × 51.7 × 97.8。1 个材质，4096 贴图（basecolor JPG、MR PNG 23.8 MB、法线 PNG 几乎是平的）。有洞口，但只是浅碗：洞心偏在 X −2.8 / Z 55.1，碗底 Ø≈20 m，比正面浅 16.5 m，不是通透的黑核。
- **拟合**：转成 Z 向上、正面 −Y、原点在底面中心，非等比缩放到 100 × 48 × 120（1.208 / 0.928 / 1.227）。焊接、补 9 个小洞，删去 54 个碎点。碗形径向重映射：洞心移到 X 0 / Z 58，碗底边 → Ø26 黑核口，唇缘 → Ø40；黑核口后推到凹入 18 m，中间再凹 5 m 成黑色碟面。洞口 24 m 外再做一次贴合包围盒的拉伸（洞口内不动）。
- **≤20 万面**：先 Catmull-Clark 细分 1 级（55.7 万面），按 Ø26 精确分界分出 皮肤 / 漏斗辉光 / 黑核 三个材质，再减面到 195,986（分界顶点锁定）。之后焊接、平滑着色，从 2 级细分稠密网格传递自定义法线。烘焙源用稠密网格加反照率高通浮雕（0.3 m），烘焙 2048 切线法线和 AO。减面时有 67 个面的 UV 跨过接缝铺满整张图，烘焙会盖掉别的岛，已修正。
- **材质**：沿用 GLB 反照率，调向参考图的暗青铜 / 铜色（保留紫色），MR 更哑光（粗糙度 +0.3，金属度 ×0.75）。漏斗自发光是从反照率生成的紫色纹路，黑核为纯黑无光。网页贴图升到 2048；修正了 v9 网页里轮廓光被注释吞掉、没加进场景的问题。
- **实测**：bbox 100.0 × 48.0 × 120.0，洞心 X 0.0 / Z 58.0，黑核 Ø26.0 / 26.0 / 25.7 / 25.4（四个方向，斜向因减面成多边形略小），辉光外缘 Ø≈41，凹入 18.0 m。

| 文件 File | v9 | v10 |
|---|---|---|
| 三角面 Tris | 195,460 | **195,986** |
| `model.glb` | 19.2 MB | 22.9 MB |
| `model_draco.glb` | 9.6 MB | 16.7 MB |
| `web/model_web.glb` | 2.4 MB（1024） | 2.1 MB（2048 WebP） |
| `web/preview.html` | 4.3 MB | 3.9 MB |

### v9：按参考图重做大形 / large-form rework
- **正面**：原来 11+11 条细前臂和满布的小卷须，改为 4 条连续大螺旋臂。臂从 Ø40 洞缘起，根部约 Ø11 m，旋转约 230° 后离开轮廓，末端是 Ø<1 m 的卷头；另有 4 条细紫脉臂走在臂间沟里。壳体沟纹改为与臂同旋率（8 条宽带 + 20 条细槽）。周边小卷须 72→33（变粗），表面小卷须 160→16（只在背面），唇缘卷须 34→12。
- **尾巴**：根部 Ø≈21 m，有机膨缩，逐渐收到 Ø≈12 m，再接一个大卷头（L 50 m，末端 Ø1.2 m）。整体抬高，避免压缩包围盒。
- **顶部**：新增 7 条冠部层叠卷脊，分前 / 中 / 后三层，起伏抬升；层叠触须集中到冠部，堆叠更高，俯视不再是一块平板。
- **背面**：18 条细臂改为 6 条粗的连续螺旋臂，背视能看出旋涡。
- **表面 / 低模**：显示网格改从**无孔洞的平滑版本**减面（同一随机种子、拟合和孔洞校正），带孔洞的 176 万面网格只作烘焙源，烘焙细节法线和 AO。v8 特写里的碎片高光是孔洞唇边被减面后形成的，现在消失了。漏斗 / 内核单独温和减面（Ø26 口沿锁定），把预算让给大形。包围盒拉伸在洞口 24 m 内淡出，洞心 Z 58.0、内核 Ø25.98 保持不变。紫色亮点 0.16→0.035，网页高光更哑光（粗糙度 +0.24，轮廓光 2.4→1.5）。
- **修正**：v8 网页的皮肤法线导出成了平铺的程序化 skin_normal（Bump 节点导致），不是烘焙图。v9 去掉 Bump，`normalTexture` / `occlusionTexture` 现在都指向烘焙图（TEXCOORD_1）。

| 文件 File | v8 | v9 |
|---|---|---|
| 三角面 Tris | 198,087 | **195,460** |
| `model.glb` | 24.0 MB | 19.2 MB |
| `model_draco.glb` | 14.4 MB | 9.6 MB |
| `web/model_web.glb` | 2.8 MB | 2.4 MB |
| `web/preview.html` | 4.9 MB | 4.3 MB |


### v8：消除折纸 / anti-origami（issue #2 补充）
- **根因**：v7 减面后大三角面在金属高光下显出平面（折纸感）；漏斗等处导出法线几乎贴齐面法线；v7 的 Mix 节点还曾让部分材质导出错误的 normalTexture。
- **修复**：`remove_doubles` 焊接 → `shade_smooth` → 从 ~62 万中模 **Data Transfer 自定义法线**到低模（连续平滑着色）→ 重新烘焙细节法线（清晰 TexImage→NormalMap 路径）→ 网页 `flatShading=false` 且保留自定义法线（不再 `computeVertexNormals`）。
- **面数**：198,087 tris（仍 ≤200k）。


### v7：≤20 万面 + 烘焙法线 / ≤200k tris + baked normals（issue #2）
- **减面**：Blender Decimate 比例 0.08，2,483,108 → **198,647** 三角面（Ø40 漏斗与 Ø26 内核顶点组保护）。包围盒仍精确 100×48×120 m；洞心 Z≈58.0、内核 Ø≈26.0、凹入 ≈18.1 m。
- **烘焙法线**：以 v6 密度（ratio 0.2，~497k）为源，Smart UV `BakeUV` + Cycles 切线空间法线烘焙到 1024² `tex/baked_detail_n.png`，与程序化微法线按 0.78 混合，法线强度 2.6；网页端 `normalScale≈1.75`。
- **Draco**：网页仍内嵌解码器；`preview.html` 9.0 → **4.9 MB**。

| 文件 File | 三角面 Tris | 大小 Size |
|---|---|---|
| v6 `model.glb` | 496,621 | 30.6 MB |
| v7 `model.glb` | 198,647 | 24.2 MB |
| v7 `model_draco.glb` | 198,647 | 14.6 MB |
| v6 `web/model_web.glb` | ~496k | 5.9 MB |
| v7 `web/model_web.glb` | ~198k | 2.8 MB |
| v6 → v7 `web/preview.html` | | 9.0 → 4.9 MB |


### v6：减面 + Draco 压缩 / decimation + Draco
- **减面 Decimation**：Blender Decimate（Collapse，比例 0.2），2,483,108 → 496,621 三角面。Ø40 漏斗与 Ø26 内核用顶点组保护、不减面，减面后再把包围盒精确拉回 100 × 48 × 120 m。实测洞心 Z 58.0、内核 Ø25.94、凹入 18.14 m，与 v5 一致。
- **Draco**：`gltf-transform draco` 使用默认量化（位置 14 bit）。网页里的 Draco 解码器（wasm + wrapper）直接内嵌在 `preview.html` 中，不依赖 CDN，离线和 file:// 也能打开。

| 文件 File | 三角面 Tris | 大小 Size |
|---|---|---|
| v5 `model.glb`（完整，未压缩 full, uncompressed） | 2,483,108 | 112.3 MB |
| v6 `model.glb`（减面，未压缩 decimated, uncompressed） | 496,621 | 30.6 MB |
| v6 `model_draco.glb`（减面 + Draco decimated + Draco） | 496,621 | 15.7 MB |
| v6 减面 + meshopt（仅作对比 comparison only） | 496,621 | 16.5 MB |
| v5 `web/model_web.glb`（简化 50% + meshopt） | ~1.24M | 17.5 MB |
| v6 `web/model_web.glb`（WebP + Draco） | 495,936 | 5.9 MB |
| v5 → v6 `web/preview.html` | | 24.2 → 9.0 MB |

完整分辨率的 GLB 中有 10.2 MB 是 PNG 贴图，所以几何数据的压缩效果更明显：未压缩 20.4 MB，Draco 5.5 MB，meshopt 6.2 MB。
Full-res GLBs carry 10.2 MB of PNG textures, so geometry alone shows the gain more clearly: 20.4 MB raw → 5.5 MB Draco → 6.2 MB meshopt.


本地备份 `v1/` 至 `v5/` 未提交到仓库（v3 是放弃的分支）。v5 的几何与 v4 完全相同（build.py 未改，网格缓存复用），只调整了明暗和材质。

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
