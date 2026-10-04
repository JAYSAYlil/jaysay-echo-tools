package com.jaysay.echotools.loot;

import com.jaysay.echotools.EchoMod;
import com.jaysay.echotools.EchoPickaxeData;
import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.HoeItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.enchantment.EnchantmentHelper;
import net.minecraft.world.item.enchantment.Enchantments;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.minecraftforge.common.loot.IGlobalLootModifier;
import net.minecraftforge.common.loot.LootModifier;
import org.jetbrains.annotations.NotNull;
import java.util.List;

/** Adds one data-driven bonus chance for a qualifying upgraded Echo Pickaxe. */
public final class SculkEchoShardModifier extends LootModifier {
    private static final Codec<List<Float>> FORTUNE_CHANCES = Codec.FLOAT.listOf();
    public static final Codec<SculkEchoShardModifier> CODEC = RecordCodecBuilder.create(
            instance -> codecStart(instance)
                    .and(FORTUNE_CHANCES.optionalFieldOf("fortune_chances", List.of(1.0F)).forGetter(modifier -> modifier.fortuneChances))
                    .apply(instance, SculkEchoShardModifier::new));

    private final List<Float> fortuneChances;

    public SculkEchoShardModifier(LootItemCondition[] conditions) {
        this(conditions, List.of(1.0F));
    }

    public SculkEchoShardModifier(LootItemCondition[] conditions, List<Float> fortuneChances) {
        super(conditions);
        if (fortuneChances.isEmpty() || fortuneChances.stream().anyMatch(chance -> !Float.isFinite(chance) || chance < 0.0F || chance > 1.0F))
            throw new IllegalArgumentException("fortune_chances must be a non-empty list of values from 0 to 1");
        this.fortuneChances = List.copyOf(fortuneChances);
    }

    @NotNull
    @Override
    protected ObjectArrayList<ItemStack> doApply(ObjectArrayList<ItemStack> generatedLoot, LootContext context) {
        var state = context.getParamOrNull(LootContextParams.BLOCK_STATE);
        if (state == null || !state.is(Blocks.SCULK)) return generatedLoot;
        ItemStack tool = context.getParamOrNull(LootContextParams.TOOL);
        var entity = context.getParamOrNull(LootContextParams.THIS_ENTITY);
        if (!(entity instanceof Player player) || player.getAbilities().instabuild) return generatedLoot;

        ItemStack qualifyingPickaxe = tool != null && tool.is(EchoMod.ECHO_PICKAXE.get())
                && EchoPickaxeData.isUpgraded(tool) ? tool
                : tool != null && tool.getItem() instanceof HoeItem
                        && player.getOffhandItem().is(EchoMod.ECHO_PICKAXE.get())
                        && EchoPickaxeData.isUpgraded(player.getOffhandItem()) ? player.getOffhandItem() : ItemStack.EMPTY;
        if (!qualifyingPickaxe.isEmpty()) {
            int fortune = EnchantmentHelper.getItemEnchantmentLevel(Enchantments.BLOCK_FORTUNE, qualifyingPickaxe);
            float chance = fortuneChances.get(Math.min(Math.max(0, fortune), fortuneChances.size() - 1));
            if (context.getRandom().nextFloat() < chance) generatedLoot.add(new ItemStack(Items.ECHO_SHARD));
        }
        return generatedLoot;
    }

    @Override
    public Codec<? extends IGlobalLootModifier> codec() {
        return EchoMod.SCULK_ECHO_SHARD_MODIFIER.get();
    }
}
