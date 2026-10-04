package com.jaysay.echotools;

import com.google.gson.JsonObject;
import net.minecraft.core.RegistryAccess;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.GsonHelper;
import net.minecraft.world.Container;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeSerializer;
import net.minecraft.world.item.crafting.SmithingTransformRecipe;
import net.minecraft.world.level.Level;

/** A strict one-step smithing upgrade. The input stack is copied so all unrelated NBT survives. */
public final class EchoSmithingRecipe extends SmithingTransformRecipe {
    private final String upgradeKey;
    private final int targetLevel;
    private final Ingredient templateIngredient;
    private final Ingredient baseIngredient;
    private final Ingredient additionIngredient;

    public EchoSmithingRecipe(ResourceLocation id, Ingredient template, Ingredient base, Ingredient addition,
                              String upgradeKey, int targetLevel) {
        super(id, template, base, addition, EchoMod.ECHO_PICKAXE.get().getDefaultInstance());
        this.upgradeKey = upgradeKey;
        this.targetLevel = targetLevel;
        this.templateIngredient = template;
        this.baseIngredient = base;
        this.additionIngredient = addition;
    }

    public String upgradeKey() {
        return upgradeKey;
    }

    public int targetLevel() {
        return targetLevel;
    }
    public Ingredient templateIngredient() { return templateIngredient; }
    public Ingredient baseIngredient() { return baseIngredient; }
    public Ingredient additionIngredient() { return additionIngredient; }

    @Override
    public RecipeSerializer<?> getSerializer() {
        return EchoMod.ECHO_UPGRADE_SERIALIZER.get();
    }

    @Override
    public boolean matches(Container container, Level level) {
        if (!super.matches(container, level)) return false;
        ItemStack base = container.getItem(1);
        return base.is(EchoMod.ECHO_PICKAXE.get())
                && EchoPickaxeData.level(base, upgradeKey) == targetLevel - 1;
    }

    @Override
    public ItemStack assemble(Container container, RegistryAccess registryAccess) {
        ItemStack result = container.getItem(1).copy();
        EchoPickaxeData.setLevel(result, upgradeKey, targetLevel);
        return result;
    }

    public static final class Serializer implements RecipeSerializer<EchoSmithingRecipe> {
        @Override
        public EchoSmithingRecipe fromJson(ResourceLocation id, JsonObject json) {
            String upgrade = GsonHelper.getAsString(json, "upgrade");
            int level = GsonHelper.getAsInt(json, "level");
            if (!(EchoPickaxeData.RESONANCE.equals(upgrade) && level >= 1 && level <= 2)
                    && !(EchoPickaxeData.FREQUENCY.equals(upgrade) && level >= 1 && level <= 3)
                    && !(EchoPickaxeData.EXTENSION.equals(upgrade) && level >= 1 && level <= 3)
                    && !(EchoPickaxeData.TUNING.equals(upgrade) && level == 1)) {
                throw new IllegalArgumentException("Invalid Echo Pickaxe upgrade " + upgrade + " level " + level);
            }
            return new EchoSmithingRecipe(id, Ingredient.fromJson(GsonHelper.getAsJsonObject(json, "template")),
                    Ingredient.fromJson(GsonHelper.getAsJsonObject(json, "base")),
                    Ingredient.fromJson(GsonHelper.getAsJsonObject(json, "addition")), upgrade, level);
        }

        @Override
        public EchoSmithingRecipe fromNetwork(ResourceLocation id, FriendlyByteBuf buffer) {
            return new EchoSmithingRecipe(id, Ingredient.fromNetwork(buffer), Ingredient.fromNetwork(buffer),
                    Ingredient.fromNetwork(buffer), buffer.readUtf(32), buffer.readVarInt());
        }

        @Override
        public void toNetwork(FriendlyByteBuf buffer, EchoSmithingRecipe recipe) {
            recipe.templateIngredient.toNetwork(buffer);
            recipe.baseIngredient.toNetwork(buffer);
            recipe.additionIngredient.toNetwork(buffer);
            buffer.writeUtf(recipe.upgradeKey, 32);
            buffer.writeVarInt(recipe.targetLevel);
        }
    }
}
