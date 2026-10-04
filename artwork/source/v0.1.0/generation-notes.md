# 0.1.0 crystal asset candidates

Only `tuning_crystal` and `enhanced_extension_crystal_2` are in scope. Both approved assets are deployed and frozen in `src/main/resources/assets/echopickaxe`; the pre-deployment 1.7.5 files are snapshotted under `artwork/validation/v0.1.0/crystals/pre-deploy-1.7.5`.

`enhanced_extension_crystal_2` uses `artwork/source/v0.1.0/enhanced_extension_crystal_2-imagegen-raw-v2.png`, generated and edited through built-in image_gen with transparent background. The reproducible importer thresholds source alpha at 128 only to calculate its crop box, crops that bbox, nearest-neighbor scales the subject to 18x28, centers it at (7,2) on a 32x32 canvas, preserves RGB, and thresholds alpha to 0/255. The output has 251 opaque texels. `artwork/source/v0.1.0/design_prompt.md` records both prompts, reference roles, and built-in tool paths.

The new tier-two model uses the standard half-pixel per-opaque-texel mesh, center UV, north/south faces, and layer0 side faces only at the outer alpha boundary. It has no item/generated parent and reuses the previous model display transforms.

`tuning_crystal` base PNG and all unchanged facets are copied byte-exact from the current production resource. Its original 1.7.5 glow strip (16 frames, 6 ticks/frame, 96 ticks / 4.8 seconds, interpolate=true) is the per-frame base. The center pixel (14,15) stays bright. Each existing ray has an inner/original/extended set: N (14,13)/(14,12)/(14,11), S (14,18)/(14,19)/(14,20), W (12,15)/(11,15)/(10,15), E (16,15)/(17,15)/(18,15). Contracted states show cyan tips and low-cyan outer afterglow; expanded states have all three white pixels; four sparkle frames move the white endpoint around the rays. The existing 132-pixel mask and every RGBA pixel outside the 13-pixel star ROI are preserved per frame; the fixed union mask has 141 pixels. New emissive faces bind only north/south with block/sky light 15 and ambient occlusion false.

`enhanced_extension_crystal_2` glow uses a fixed 14-texel emerald/cyan circuit mask and advances a two-pixel same-hue highlight around the central ring. Its 16x4-tick cycle is 3.2 seconds; crystal facets and outer silhouette stay steady. Both glow strips have a fixed binary alpha mask and 16 frames.

Previews in `artwork/validation/v0.1.0/crystals/` include the three-tier 32/real-16px family comparison, tuning labeled phases and coordinate diagram, and per-item tick-sampled GIFs.


Deployment is frozen. The eight deployed files (two item models, two base textures, two glow strips, and two .mcmeta files) match the approved candidate byte-for-byte. SHA-256 before/after values are recorded in artwork/validation/v0.1.0/crystals/deployment-hashes.json; root's independent candidate audit passed, including preserved 1.7.5 tuning animation outside the star ROI. No other production resources were changed.
