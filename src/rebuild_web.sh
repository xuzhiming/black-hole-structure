#!/bin/bash
# model.blend -> model.glb -> web/model_web.glb (dedup + 1024 webp + simplify 0.6 + meshopt high) -> web/preview.html (same pipeline as cyber_louvre)
set -e
cd /workspace/outputs/black_hole_structure/src
python3 export_glb.py 2>&1 | tail -1
G="npx --yes @gltf-transform/cli"
cd ..
$G dedup model.glb /tmp/bh_a.glb >/dev/null 2>&1 && $G resize /tmp/bh_a.glb /tmp/bh_b.glb --width 1024 --height 1024 >/dev/null 2>&1 \
 && $G webp /tmp/bh_b.glb /tmp/bh_c.glb >/dev/null 2>&1 \
 && $G simplify /tmp/bh_c.glb /tmp/bh_s.glb --ratio 0.5 --error 0.0005 >/dev/null 2>&1 \
 && $G meshopt /tmp/bh_s.glb web/model_web.glb --level high 2>&1 | tail -1   # v2: 2.35M -> ~1.3M tris for the web so preview.html stays < 25 MB
ls -la web/model_web.glb
python3 src/make_preview.py
