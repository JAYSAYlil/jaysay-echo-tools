package com.jaysay.echotools;

import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

import java.util.Locale;

/** Supported vanilla ore families. Deepslate variants share the same vanilla tags. */
public enum EchoOreKind {
    ALL,
    COAL,
    COPPER,
    IRON,
    GOLD,
    REDSTONE,
    LAPIS,
    DIAMOND,
    EMERALD,
    QUARTZ,
    NETHER_GOLD,
    ANCIENT_DEBRIS;

    public String id() {
        return name().toLowerCase(Locale.ROOT);
    }

    public boolean matches(BlockState state) {
        return switch (this) {
            case ALL -> isOre(state);
            case COAL -> state.is(BlockTags.COAL_ORES);
            case COPPER -> state.is(BlockTags.COPPER_ORES);
            case IRON -> state.is(BlockTags.IRON_ORES);
            case GOLD -> state.is(BlockTags.GOLD_ORES);
            case REDSTONE -> state.is(BlockTags.REDSTONE_ORES);
            case LAPIS -> state.is(BlockTags.LAPIS_ORES);
            case DIAMOND -> state.is(BlockTags.DIAMOND_ORES);
            case EMERALD -> state.is(BlockTags.EMERALD_ORES);
            case QUARTZ -> state.is(Blocks.NETHER_QUARTZ_ORE);
            case NETHER_GOLD -> state.is(Blocks.NETHER_GOLD_ORE);
            case ANCIENT_DEBRIS -> state.is(Blocks.ANCIENT_DEBRIS);
        };
    }

    public static EchoOreKind byId(String id) {
        if (id == null || id.isBlank()) return null;
        try {
            return valueOf(id.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ignored) {
            return null;
        }
    }

    private static boolean isOre(BlockState state) {
        for (EchoOreKind kind : values()) {
            if (kind != ALL && kind.matches(state)) return true;
        }
        return false;
    }
}
