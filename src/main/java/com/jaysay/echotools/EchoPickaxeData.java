package com.jaysay.echotools;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.world.item.ItemStack;

/** Persistent per-tool resonance, frequency, and ore filter settings. */
public final class EchoPickaxeData {
    public static final String NBT_ROOT = "EchoUpgrades";
    public static final String RESONANCE = "resonance";
    public static final String FREQUENCY = "frequency";
    public static final String TUNING = "tuning";
    public static final String EXTENSION = "extension";
    public static final String FILTER = "filter";

    private EchoPickaxeData() {}

    public static int level(ItemStack stack, String key) {
        CompoundTag root = stack.getTag();
        if (root == null || !root.contains(NBT_ROOT, Tag.TAG_COMPOUND)) return 0;
        int value = root.getCompound(NBT_ROOT).getInt(key);
        int maximum = key.equals(RESONANCE) ? 2 : key.equals(FREQUENCY) || key.equals(EXTENSION) ? 3 : key.equals(TUNING) ? 1 : 0;
        return Math.max(0, Math.min(value, maximum));
    }

    public static boolean hasTuning(ItemStack stack) {
        return level(stack, TUNING) >= 1;
    }

    public static boolean isUpgraded(ItemStack stack) {
        return level(stack, RESONANCE) > 0 || level(stack, FREQUENCY) > 0 || level(stack, EXTENSION) > 0 || hasTuning(stack);
    }

    public static int scanRadius(ItemStack stack) {
        return switch (level(stack, EXTENSION)) {
            case 1 -> 18;
            case 2 -> 24;
            case 3 -> 30;
            default -> 12;
        };
    }

    public static int guidanceTicks(ItemStack stack) {
        return switch (level(stack, FREQUENCY)) {
            case 1 -> 280;
            case 2 -> 420;
            case 3 -> 560;
            default -> 140;
        };
    }

    public static void setLevel(ItemStack stack, String key, int level) {
        CompoundTag tag = stack.getOrCreateTag();
        CompoundTag upgrades = tag.contains(NBT_ROOT, Tag.TAG_COMPOUND)
                ? tag.getCompound(NBT_ROOT) : new CompoundTag();
        upgrades.putInt(key, level);
        tag.put(NBT_ROOT, upgrades);
    }

    public static String filter(ItemStack stack) {
        if (!hasTuning(stack) || stack.getTag() == null) return "all";
        CompoundTag upgrades = stack.getTag().getCompound(NBT_ROOT);
        String value = upgrades.getString(FILTER);
        return EchoOreKind.byId(value) == null ? "all" : value;
    }

    public static void setFilter(ItemStack stack, String oreId) {
        if (!hasTuning(stack) || EchoOreKind.byId(oreId) == null) return;
        CompoundTag tag = stack.getOrCreateTag();
        CompoundTag upgrades = tag.contains(NBT_ROOT, Tag.TAG_COMPOUND)
                ? tag.getCompound(NBT_ROOT) : new CompoundTag();
        upgrades.putString(FILTER, oreId);
        tag.put(NBT_ROOT, upgrades);
    }
}
