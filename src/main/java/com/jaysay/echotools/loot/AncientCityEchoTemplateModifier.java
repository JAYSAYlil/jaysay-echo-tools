package com.jaysay.echotools.loot;

import com.jaysay.echotools.EchoMod;
import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.minecraftforge.common.loot.IGlobalLootModifier;
import net.minecraftforge.common.loot.LootModifier;
import org.jetbrains.annotations.NotNull;

/** Adds one reusable upgrade template to a small portion of ancient-city chests. */
public final class AncientCityEchoTemplateModifier extends LootModifier {
    public static final Codec<AncientCityEchoTemplateModifier> CODEC = RecordCodecBuilder.create(
            instance -> codecStart(instance).apply(instance, AncientCityEchoTemplateModifier::new));

    public AncientCityEchoTemplateModifier(LootItemCondition[] conditions) {
        super(conditions);
    }

    @NotNull
    @Override
    protected ObjectArrayList<ItemStack> doApply(ObjectArrayList<ItemStack> generatedLoot, LootContext context) {
        generatedLoot.add(EchoMod.ECHO_UPGRADE_TEMPLATE.get().getDefaultInstance());
        return generatedLoot;
    }

    @Override
    public Codec<? extends IGlobalLootModifier> codec() {
        return EchoMod.ANCIENT_CITY_TEMPLATE_MODIFIER.get();
    }
}
