# Generation record — 0.1.2 TConstruct 2 inspired candidate

- Design authority: `native-pixel-map.json`, direct 32×32 material/facet texels.
- Art reference: official [Tinkers’ Construct 2 Minecraft 1.12 source branch](https://github.com/SlimeKnights/TinkersConstruct/tree/1.12), specifically Diamond pickaxe edge overlays and the Luck butt-gem overlay. Only placement and faceting principles informed this work; no reference pixels/assets copied.
- Concept: `echo-pickaxe-upgrades-concept.png` (selected imagegen material study; not used as pixel source).
- Prompt provenance: `imagegen-record.json` and `prompt.json` contain both imagegen prompts, references and output provenance.
- Source baseline: the existing unupgraded Echo Pickaxe image and glow resources; verified unchanged in the working tree.
- Components: left red blade-end wrap; right violet blade-end wrap; central four-point ice inlay; green faceted end-cap with ice eye and three bone supports.
- Silhouette: 11 mapped extra opaque pixels at three local ends; each is one edge-neighbor from original alpha; no y=31 additions.
- Model generation: one half-unit pixel prism per opaque texel; rebuild faces from final alpha adjacency, retain center UV mapping; emissive north/south faces use Forge 15/15/AO-off data.
- Glow generation: preserve all source fissure animation outside the four module masks; replace covered glow pixels with the mapped tier material and pulse each tier's own highlight across 16 frames.
- Metadata: copy original `echo_pickaxe_glow.png.mcmeta` bytes to every generated strip sidecar.
- Output: 95 variants plus base state in isolated candidate only. Deployment remains a separate authorized step.

- Deployment: root-authorized 95-variant deployment, exactly the 285 model/base/glow targets; candidate and deployed SHA-256 values match in artwork/validation/v0.1.2/pickaxe/deployment-sha256-tconstruct2.csv. The asset deployment preserved the base model/texture/glow/meta and all crystals. Separately, the development geometry checker was updated to validate the attached pixel caps; runtime selection and gameplay remain unchanged.
