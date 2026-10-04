# 0.1.1 crystal asset notes

Only `enhanced_extension_crystal_2` was changed. The generated source and both family references are preserved in `artwork/source/v0.1.1`; `design_prompt.json` records the built-in image_gen mode, reference paths, and both exact prompts. The selected edited source is `enhanced_extension_crystal_2-imagegen-raw-v2.png`.

The reproducible import in `generate_crystal.py` thresholds alpha at 128 to find the subject bbox `(259,63,1016,1192)` in the 1254×1254 source, crops it, nearest-neighbor resizes proportionally to 19×28, places it at (6,2) on a transparent 32×32 canvas, and writes hard alpha 0/255 without repainting RGB. The imported sprite has 284 opaque texels and keeps a one-pixel transparent border.

The new single emerald orbit spans 18×14 texels and wraps diagonally around the cyan crystal. The fixed glow mask covers 33 emerald pixels; a two-pixel same-hue highlight moves around the ring over 16 frames at 4 ticks each (64 ticks / 3.2 seconds), with interpolation enabled. The GIF samples that interpolation at 50 ms per tick for 64 frames.

The model has one half-pixel box for every opaque texel, center UV `[x/2+0.25,y/2+0.25]`, north/south fullbright glow faces with `block_light=15`, `sky_light=15`, `ambient_occlusion=false`, base-textured silhouette side faces, no parent, and the preserved previous display transforms. Root's independent candidate audit passed before deployment.

The four candidate files are now deployed and frozen. The pre-deployment 0.1.0 files are preserved under `artwork/validation/v0.1.1/crystals/pre-deploy-0.1.0`; deployed SHA-256 values are recorded in `artwork/validation/v0.1.1/crystals/deployment-hashes.json`. Candidate base/model/glow/meta hashes match the deployed copies. No other production resources were changed.
