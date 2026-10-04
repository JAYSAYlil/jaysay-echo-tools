# Built-in imagegen prompt — 1.7.3 enhanced extension crystal II

Tool mode: built-in `image_gen.imagegen` (default mode; no CLI/API).
Operation: create a new sprite using one local reference board as visual input.
Input image 1: `artwork/validation/v1.7.3/source-reference-board.png`; panel 1 is the target current `enhanced_extension_crystal_2` design; panel 2 is the basic `extension_crystal` style reference; panel 3 is `enhanced_extension_crystal` style reference. The board was nearest-neighbor enlarged from the original family PNGs in `artwork/source/emissive-v1.6.0/base_textures/`.
Transparency: `transparent_background=true`.

Exact prompt sent:

> Use case: game-asset pixel-art redesign. Asset: one Minecraft inventory crystal item icon, transparent background. Image 1 reference board roles: panel 1 is the target third-tier extension crystal to redesign; panels 2 and 3 are the lower tiers' style references. Redesign only the target as a compact, refined, vertically tapered jewel, centered on a square canvas. Preserve a crisp discrete square-pixel style, dark outline, lighting direction and jewel material of the references. Make it clearly third-tier but simpler: one small dark teal vertical eye-core surrounded by a clean emerald-green ring; a few restrained cyan facet accents; a sparse, balanced bone-white frame with only a few distinct corner facets/highlights. Readable at 32x32 and 16x16. Transparent pixels outside silhouette, at least one transparent pixel margin. No letters, labels, UI, extra crystals, blur, bloom, particles, outside shadow, tangled crossing cyan lines, dense overlapping white shards, oversized iris, eyelashes or photographic realism. Pixel clusters should use flat square blocks, no smooth gradients.

The successful generated original was saved by Codex at `C:\Users\<user>\.codex\generated_images\01a0ec08-2a53-7a73-9bbc-5432772b5af6\exec-7dd1021c-c726-493c-9196-72b2984d1bbd.png` (1254x1254 RGBA), then copied byte-for-byte to `artwork/source/structural-v1.7.3/enhanced_extension_crystal_2-imagegen.png`. The first tool attempt did not expose its response payload in the exec output and was not used; the saved source and all downstream assets correspond to the successful second built-in call recorded above.
