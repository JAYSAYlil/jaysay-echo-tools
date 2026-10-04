# Echo Pickaxe upgrade visuals — v0.1.2 Tinkers Construct 2 study

This is the authoritative editable source for the 0.1.2 appearance candidate. The native texel map, not the earlier imagegen raster or archived 0.1.2 drafts, defines the textures. `echo-pickaxe-upgrades-concept.png` is the selected generated material-placement reference; it is not traced, sampled, or copied into the native map. `imagegen-record.json` and `prompt.json` preserve both prompt attempts and input/reference provenance.

## Reference and materials

The visual study references the official [Tinkers’ Construct 2 Minecraft 1.12 source branch](https://github.com/SlimeKnights/TinkersConstruct/tree/1.12), specifically its pickaxe Diamond and Luck modifier overlays: part-aligned crystal wrapping on tool-head edges and a faceted butt crystal. This informed placement and material integration only; no TConstruct image pixels or asset files are reused. The native map is fully drawn from Echo Pickaxe colors and structure.

- Resonance wraps the left blade end in warm red cut facets; tier II steps onto the upper shoulder.
- Frequency wraps the right blade tip in violet facets, extending upward by level.
- Tuning is a small four-point ice inlay with a 2×2 emissive center. The surrounding original cracks remain.
- Extension is a green faceted pommel eye; tier II adds a 2×2 ice core and tier III adds three restrained bone supports.

The original unupgraded source PNG, glow strip, metadata, crystals, runtime registration, and gameplay remain untouched. The development geometry checker was updated separately to validate attached crystal caps. Upgrade variants add at most 11 alpha texels at the blade ends and handle butt; each new texel edge-touches original alpha, stays within coordinates 1..30, and does not extend row 31. Each tier introduces an emissive pixel. Variant models are rebuilt from the final alpha mask so new exposed walls, pixel geometry and center UVs follow the real silhouette.

## Generate and review

From the repository root, run:

```powershell
python artwork/source/echo-pickaxe-upgrades-v0.1.2/generate_variants.py
python artwork/source/echo-pickaxe-upgrades-v0.1.2/generate_previews.py
python artwork/source/echo-pickaxe-upgrades-v0.1.2/render_preview.py
```

The first script writes 95 models, base sprites, 16-frame glow strips and byte-identical glow metadata only under `artwork/validation/v0.1.2/pickaxe/candidate/`. It checks 96 distinct 32px and nearest-neighbor 16px states, non-overlapping component masks, per-tier emission and the local silhouette expansion contract. The second script renders all 96 combinations on white, dark and inventory-size sheets, the 0.1.1-to-full-upgrade comparison, and a 96-frame GIF at 50ms per frame for two cycles of the original 16-frame/3-tick/interpolated animation. The third script renders the focused six-state / per-level boards from the same map.

No candidate file is deployed to `src/` by these generators. Independent resource audit is run separately by the root task owner.
