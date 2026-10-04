# TConstruct 2 style pickaxe material study

This is an isolated design draft for the Echo Pickaxe only. The original production texture and the official Tinkers’ Construct 2 / Minecraft 1.12 comparison sheet were visual references; no reference texture pixels were copied. The imagegen concept is a placement/material study only. `native-pixel-map.json` is the editable pixel-level source for preview rendering.

## Current concept

- Resonance forms a warm red faceted cap around the left blade end and rises along the shoulder at tier II.
- Frequency forms a violet faceted cap around the right blade end and develops upward through tiers II and III.
- Tuning is a compact four-point ice inlay with a 2×2 luminous core; the surrounding sculk cracks remain visible.
- Extension forms a green faceted handle-end eye; tier II adds a cyan 2×2 core and tier III adds three small bone supports.
- Only the four component regions use color changes. Eleven added opaque texels expand local blade/pommel edges by one pixel; no new texel reaches row 31, so handle length stays unchanged. The untouched base-state image remains byte-identical to the production source.

## Preview and validation

Run `python render_preview.py` from the repository root. Outputs go only to `artwork/validation/v0.1.2/tconstruct2-preview/`. The generator emits the six-state comparison, each of the nine single-attribute levels plus base/full maximum, exact 16px nearest-neighbor sheets, and a 96-frame GIF sampled every 50ms for two cycles of the original 16-frame × 3-tick animation. The validation checks the approved one-pixel silhouette additions, module separation, opaque mapped pixels, and unique appearance of all progression states at 16px.

No 95-variant pack, model edits, production assets, Java, or installation is part of this draft.
