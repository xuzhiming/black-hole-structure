#!/bin/bash
# v6: model.glb (decimated ~0.5M tris, written by scene.py) ->
#   model_draco.glb       : Draco-compressed full-texture GLB (download / DCC use)
#   web/model_web.glb     : dedup + 1024 webp textures + Draco -> embedded in web/preview.html (Draco decoder embedded too)
#   /tmp/bh_cmp_*.glb     : meshopt variants for the size comparison only
set -e
cd /workspace/outputs/black_hole_structure
[ -f model.glb ] || (cd src && python3 export_glb.py)
G="npx --yes @gltf-transform/cli"
$G draco model.glb model_draco.glb >/dev/null 2>&1
$G meshopt model.glb /tmp/bh_cmp_meshopt_full.glb --level high >/dev/null 2>&1
$G dedup model.glb /tmp/bh_a.glb >/dev/null 2>&1 && $G resize /tmp/bh_a.glb /tmp/bh_b.glb --width 1024 --height 1024 >/dev/null 2>&1 \
 && $G webp /tmp/bh_b.glb /tmp/bh_c.glb >/dev/null 2>&1 \
 && $G draco /tmp/bh_c.glb web/model_web.glb >/dev/null 2>&1 \
 && $G meshopt /tmp/bh_c.glb /tmp/bh_cmp_meshopt_web.glb --level high >/dev/null 2>&1
ls -la model.glb model_draco.glb web/model_web.glb /tmp/bh_c.glb /tmp/bh_cmp_meshopt_full.glb /tmp/bh_cmp_meshopt_web.glb
python3 src/make_preview.py
