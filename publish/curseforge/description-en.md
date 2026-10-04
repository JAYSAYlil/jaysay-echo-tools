# JaySay's Echo Tools

**A sculk-forged pickaxe that senses nearby ores and guides you to them with a luminous echo trail.**

Minecraft Java **1.20.1** · Forge **47.x** (developed and verified against Forge 47.4.21)

---

## What it does

Hold an **Echo Pickaxe** and right-click. The pickaxe scans a sphere around you (loaded chunks only) and marks every ore vein it finds. A bright cyan trail plus an arrow points at the main target, and the outlines stay visible through walls. **Only the player who scanned can see the marks.** Press **V** to cycle between the veins you found; when the main vein is mined out, the guide moves on to the next one automatically.

No new blocks, no worldgen changes, no new ores. The whole mod is one tool, one smithing template, and ten crystals.

## Getting started

1. **Echo Crystal** — craft a diamond surrounded by 8 echo shards.
2. **Echo Upgrade Smithing Template** — found in **ancient city chests (5%)**, or dropped by the **Warden** when a player kills it (**10%**, +1 percentage point per Looting level; non-player kills do not drop it). Copy it on a crafting table, two templates per craft.
3. **Echo Pickaxe** — smithing table: template + diamond pickaxe + echo crystal. Custom names, enchantments and durability damage are preserved.

The Echo Pickaxe is netherite-tier: **2031 durability**, enchantability 15, 6 attack damage, 1.2 attack speed.

## Upgrades

Four independent paths, applied on a smithing table with the template, your pickaxe and the matching crystal. You must upgrade one level at a time; other upgrades, your ore filter, name, enchantments and durability damage are kept.

| Path | Unupgraded | I | II | III |
| --- | --- | --- | --- | --- |
| **Resonance** — scan cooldown | 5 s | 3 s | 1 s | — |
| | *+ mining speed on pickaxe-mineable blocks* | +1 | +2 | — |
| **Frequency** — veins found / guidance time | 1 / 7 s | 3 / 14 s | 5 / 21 s | 8 / 28 s |
| **Tuning** — ore filter | all ores | unlocks the filter | — | — |
| **Extension** — scan radius | 12 blocks | 18 | 24 | 30 |

Once Tuning is unlocked, **sneak-right-click** opens the ore filter (all ores, coal, copper, iron, gold, redstone, lapis, diamond, emerald, nether quartz, nether gold, ancient debris). Ores that touch on a block face merge into one vein.

## Extras

- **Bonus echo shards** — mining a sculk block with an upgraded Echo Pickaxe has a Fortune-scaled chance to drop an extra echo shard: Fortune 0/I/II/III gives **10% / 15% / 20% / 25%**. A hoe in your main hand plus an upgraded pickaxe in your offhand works too, and always reads the *pickaxe's* Fortune.
- **Drop protection** — a dropped Echo Pickaxe survives fire, lava, magma and cactus.
- **Three advancements**, including a challenge for fully upgrading resonance, frequency, tuning and extension on a single pickaxe (100 XP).
- **Own creative tab** with all 12 items.
- **Emissive textures** — the glowing parts stay lit in the dark, with no shader pack and no OptiFine required.

## Multiplayer

Client and server **must install the same version** (network protocol 4). Works on dedicated servers.

## Language

English and Simplified Chinese, including item tooltips and advancement text.

---

## License

All rights reserved. Please do not redistribute the mod or its assets without permission.
