package com.jaysay.echotools;

import com.jaysay.echotools.loot.AncientCityEchoTemplateModifier;
import com.jaysay.echotools.loot.SculkEchoShardModifier;
import com.mojang.brigadier.Command;
import com.mojang.serialization.Codec;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.PickaxeItem;
import net.minecraft.world.item.Rarity;
import net.minecraft.world.item.SmithingTemplateItem;
import net.minecraft.world.item.Tiers;
import net.minecraft.world.item.enchantment.EnchantmentHelper;
import net.minecraft.world.item.enchantment.Enchantments;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SmithingRecipe;
import net.minecraft.world.item.crafting.RecipeSerializer;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.TransientCraftingContainer;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.LootDataType;
import net.minecraft.world.level.storage.loot.LootDataId;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.common.loot.IGlobalLootModifier;
import net.minecraftforge.common.loot.LootModifier;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppedEvent;
import net.minecraftforge.event.entity.player.ItemTooltipEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLEnvironment;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;

import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Mod(EchoMod.MOD_ID)
public class EchoMod {
    public static final String MOD_ID = "echopickaxe";
    private static final Map<UUID, ScanSession> SCAN_SESSIONS = new HashMap<>();
    private static final Map<UUID, Long> FILTER_SESSIONS = new HashMap<>();

    public static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, MOD_ID);
    public static final DeferredRegister<CreativeModeTab> CREATIVE_TABS =
            DeferredRegister.create(Registries.CREATIVE_MODE_TAB, MOD_ID);
    public static final RegistryObject<Item> ECHO_PICKAXE = ITEMS.register("echo_pickaxe",
            () -> new EchoPickaxe(new Item.Properties().stacksTo(1).rarity(Rarity.RARE).fireResistant()));
    public static final RegistryObject<Item> ECHO_UPGRADE_TEMPLATE = ITEMS.register("echo_upgrade_smithing_template",
            EchoMod::createTemplate);
    public static final RegistryObject<Item> ECHO_CRYSTAL = ITEMS.register("echo_crystal",
            () -> new Item(new Item.Properties().rarity(Rarity.UNCOMMON)));
    public static final RegistryObject<Item> RESONANCE_CRYSTAL = crystal("resonance_crystal");
    public static final RegistryObject<Item> ENHANCED_RESONANCE_CRYSTAL = crystal("enhanced_resonance_crystal");
    public static final RegistryObject<Item> FREQUENCY_CRYSTAL = crystal("frequency_crystal");
    public static final RegistryObject<Item> ENHANCED_FREQUENCY_CRYSTAL = crystal("enhanced_frequency_crystal");
    public static final RegistryObject<Item> ENHANCED_FREQUENCY_CRYSTAL_2 = crystal("enhanced_frequency_crystal_2");
    public static final RegistryObject<Item> TUNING_CRYSTAL = crystal("tuning_crystal");
    public static final RegistryObject<Item> EXTENSION_CRYSTAL = crystal("extension_crystal");
    public static final RegistryObject<Item> ENHANCED_EXTENSION_CRYSTAL = crystal("enhanced_extension_crystal");
    public static final RegistryObject<Item> ENHANCED_EXTENSION_CRYSTAL_2 = crystal("enhanced_extension_crystal_2");
    public static final RegistryObject<CreativeModeTab> ECHO_TOOLS_TAB = CREATIVE_TABS.register("echo_tools",
            () -> CreativeModeTab.builder()
                    .title(Component.translatable("itemGroup.echopickaxe.echo_tools"))
                    .icon(() -> new ItemStack(ECHO_PICKAXE.get()))
                    .displayItems((parameters, output) -> ITEMS.getEntries()
                            .forEach(entry -> output.accept(entry.get())))
                    .build());

    public static final DeferredRegister<RecipeSerializer<?>> RECIPE_SERIALIZERS =
            DeferredRegister.create(ForgeRegistries.RECIPE_SERIALIZERS, MOD_ID);
    public static final RegistryObject<RecipeSerializer<EchoSmithingRecipe>> ECHO_UPGRADE_SERIALIZER =
            RECIPE_SERIALIZERS.register("echo_upgrade", EchoSmithingRecipe.Serializer::new);

    public static final DeferredRegister<Codec<? extends IGlobalLootModifier>> LOOT_MODIFIERS =
            DeferredRegister.create(ForgeRegistries.Keys.GLOBAL_LOOT_MODIFIER_SERIALIZERS, MOD_ID);
    public static final RegistryObject<Codec<AncientCityEchoTemplateModifier>> ANCIENT_CITY_TEMPLATE_MODIFIER =
            LOOT_MODIFIERS.register("ancient_city_echo_template", () -> AncientCityEchoTemplateModifier.CODEC);
    public static final RegistryObject<Codec<SculkEchoShardModifier>> SCULK_ECHO_SHARD_MODIFIER =
            LOOT_MODIFIERS.register("sculk_echo_shard", () -> SculkEchoShardModifier.CODEC);

    public EchoMod() {
        IEventBus modBus = FMLJavaModLoadingContext.get().getModEventBus();
        ITEMS.register(modBus);
        CREATIVE_TABS.register(modBus);
        RECIPE_SERIALIZERS.register(modBus);
        LOOT_MODIFIERS.register(modBus);
        EchoNetwork.register();
        MinecraftForge.EVENT_BUS.register(this);
    }

    private static RegistryObject<Item> crystal(String name) {
        return ITEMS.register(name, () -> new Item(new Item.Properties().rarity(Rarity.UNCOMMON)));
    }

    private static Item createTemplate() {
        return new SmithingTemplateItem(
                Component.translatable("item.echopickaxe.echo_upgrade_smithing_template.applies_to"),
                Component.translatable("item.echopickaxe.echo_upgrade_smithing_template.ingredients"),
                Component.translatable("item.echopickaxe.echo_upgrade_smithing_template.upgrade_description"),
                Component.translatable("item.echopickaxe.echo_upgrade_smithing_template.base_slot_description"),
                Component.translatable("item.echopickaxe.echo_upgrade_smithing_template.additions_slot_description"),
                List.of(new ResourceLocation("minecraft", "item/empty_slot_pickaxe")),
                List.of(new ResourceLocation("minecraft", "item/empty_slot_amethyst_shard")));
    }

    @SubscribeEvent
    public void registerCommands(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("echo").requires(source -> source.hasPermission(2))
                .then(Commands.literal("demo").then(Commands.literal("confirm")
                        .executes(ctx -> buildDemo(ctx.getSource().getPlayerOrException()))))
                .then(Commands.literal("verify").executes(ctx -> verify(ctx.getSource().getPlayerOrException()))));
    }

    private int verify(ServerPlayer player) {
        ServerLevel level=player.serverLevel();
        try {
            var recipes = level.getServer().getRecipeManager();
            var crystalId = new ResourceLocation(MOD_ID, "echo_crystal");
            var templateId = new ResourceLocation(MOD_ID, "echo_upgrade_template");
            var upgradeId = new ResourceLocation(MOD_ID, "echo_pickaxe_upgrade");
            if (recipes.byKey(new ResourceLocation(MOD_ID, "echo_pickaxe")).isPresent())
                throw new IllegalStateException("old direct pickaxe recipe still exists");
            CraftingRecipe crystalRecipe = recipes.byKey(crystalId).filter(CraftingRecipe.class::isInstance)
                    .map(CraftingRecipe.class::cast).orElseThrow(() -> new IllegalStateException("crystal recipe missing"));
            CraftingRecipe templateRecipe = recipes.byKey(templateId).filter(CraftingRecipe.class::isInstance)
                    .map(CraftingRecipe.class::cast).orElseThrow(() -> new IllegalStateException("template recipe missing"));
            var craftMenu = new AbstractContainerMenu(null, 0) {
                @Override public ItemStack quickMoveStack(Player player, int slot) { return ItemStack.EMPTY; }
                @Override public boolean stillValid(Player player) { return true; }
            };
            var crafting = new TransientCraftingContainer(craftMenu, 3, 3);
            for (int i = 0; i < 9; i++) crafting.setItem(i, new ItemStack(i == 4 ? Items.DIAMOND : Items.ECHO_SHARD));
            if (!crystalRecipe.matches(crafting, level) || crystalRecipe.assemble(crafting, level.registryAccess()).getItem() != ECHO_CRYSTAL.get())
                throw new IllegalStateException("echo crystal recipe does not match the expected 8 shards + diamond");
            for (int i = 0; i < 9; i++) crafting.setItem(i, ItemStack.EMPTY);
            int[] sculkSlots = {0, 2, 3, 5, 6, 7, 8};
            for (int slot : sculkSlots) crafting.setItem(slot, new ItemStack(Blocks.SCULK));
            crafting.setItem(1, new ItemStack(Items.DIAMOND));
            crafting.setItem(4, ECHO_UPGRADE_TEMPLATE.get().getDefaultInstance());
            ItemStack copiedTemplate = templateRecipe.assemble(crafting, level.registryAccess());
            if (!templateRecipe.matches(crafting, level) || copiedTemplate.getItem() != ECHO_UPGRADE_TEMPLATE.get() || copiedTemplate.getCount() != 2)
                throw new IllegalStateException("template copy recipe failed");

            verifyUpgradeRecipes(level,player);
            verifyCrystalRecipes(level,recipes);
            verifyPickaxeMiningStats(player);

            SmithingRecipe upgrade = recipes.getAllRecipesFor(RecipeType.SMITHING).stream()
                    .filter(recipe -> recipe.getId().equals(upgradeId)).findFirst()
                    .orElseThrow(() -> new IllegalStateException("smithing upgrade recipe missing"));
            SimpleContainer smithing = new SimpleContainer(3);
            smithing.setItem(0, ECHO_UPGRADE_TEMPLATE.get().getDefaultInstance());
            ItemStack namedPick = new ItemStack(Items.DIAMOND_PICKAXE);
            namedPick.setDamageValue(31);
            namedPick.setHoverName(Component.literal("Echo Verify"));
            EnchantmentHelper.setEnchantments(java.util.Map.of(Enchantments.BLOCK_EFFICIENCY, 3), namedPick);
            smithing.setItem(1, namedPick);
            smithing.setItem(2, ECHO_CRYSTAL.get().getDefaultInstance());
            ItemStack upgraded = upgrade.assemble(smithing, level.registryAccess());
            if (!upgrade.matches(smithing, level) || upgraded.getItem() != ECHO_PICKAXE.get()
                    || upgraded.getDamageValue() != 31 || !upgraded.hasCustomHoverName()
                    || EnchantmentHelper.getItemEnchantmentLevel(Enchantments.BLOCK_EFFICIENCY, upgraded) != 3)
                throw new IllegalStateException("smithing output failed to preserve damage/name/enchantment");

            var ancientId = new ResourceLocation("minecraft", "chests/ancient_city");
            var ancientKey = new LootDataId<>(LootDataType.TABLE, ancientId);
            var ancientTable = level.getServer().getLootData().getElement(ancientKey);
            LootParams params = new LootParams.Builder(level).withParameter(LootContextParams.ORIGIN, Vec3.ZERO)
                    .create(LootContextParamSets.CHEST);
            boolean sawTemplate = false;
            boolean sawExistingLoot = false;
            for (long seed = 1; seed <= 1000; seed++) {
                var generated = ancientTable.getRandomItems(params, seed);
                sawTemplate |= generated.stream().anyMatch(stack -> stack.is(ECHO_UPGRADE_TEMPLATE.get()));
                sawExistingLoot |= generated.stream().anyMatch(stack -> !stack.is(ECHO_UPGRADE_TEMPLATE.get()));
            }
            var mineshaft = level.getServer().getLootData().getElement(new LootDataId<>(LootDataType.TABLE,
                    new ResourceLocation("minecraft", "chests/abandoned_mineshaft")));
            int mineshaftTemplateCount = 0;
            for (long seed = 0xEC40L; seed < 0xEC40L + 100; seed++) {
                var generated = mineshaft.getRandomItems(params, seed);
                if (generated.stream().anyMatch(stack -> stack.is(ECHO_UPGRADE_TEMPLATE.get()))) mineshaftTemplateCount++;
            }
            if (!sawTemplate || !sawExistingLoot || mineshaftTemplateCount != 0)
                throw new IllegalStateException("ancient-city additive loot check failed (templates=" + sawTemplate + ", vanilla=" + sawExistingLoot + ", non-city=" + mineshaftTemplateCount + ")");

            verifyWardenDrops(level.getServer().getLootData(), level, player);
            verifySculkDrops(level.getServer().getLootData(),level,player);
            verifyPickaxeItemProtection(level,player);
            level.getServer().getPlayerList().broadcastSystemMessage(
                    Component.literal("[Echo Pickaxe] VERIFY PASS: recipes/serializer, smithing NBT, city/Warden loot, Fortune-scaled sculk drops, item protection, netherite pickaxe stats, resonance mining speed").withStyle(ChatFormatting.GREEN), false);
            return Command.SINGLE_SUCCESS;
        } catch (Throwable error) {
            level.getServer().getPlayerList().broadcastSystemMessage(
                    Component.literal("[Echo Pickaxe] VERIFY FAIL: " + error.getMessage()).withStyle(ChatFormatting.RED), false);
            return 0;
        }
    }

    private void verifyPickaxeMiningStats(ServerPlayer player) {
        Item echoItem = ECHO_PICKAXE.get();
        Item netheriteItem = Items.NETHERITE_PICKAXE;
        if (!(echoItem instanceof PickaxeItem echoPickaxe) || !(netheriteItem instanceof PickaxeItem netheritePickaxe))
            throw new IllegalStateException("pickaxe registration type mismatch");
        if (echoPickaxe.getTier() != Tiers.NETHERITE || echoPickaxe.getTier().getLevel() != netheritePickaxe.getTier().getLevel()
                || echoItem.getMaxDamage() != netheriteItem.getMaxDamage()
                || echoItem.getEnchantmentValue() != netheriteItem.getEnchantmentValue()
                || !echoItem.getDefaultAttributeModifiers(net.minecraft.world.entity.EquipmentSlot.MAINHAND)
                        .equals(netheriteItem.getDefaultAttributeModifiers(net.minecraft.world.entity.EquipmentSlot.MAINHAND)))
            throw new IllegalStateException("Echo Pickaxe does not match Netherite tier, durability, enchantability, or attack modifiers");
        if (echoItem.getMaxDamage() != 2031 || echoItem.getEnchantmentValue() != 15)
            throw new IllegalStateException("unexpected Netherite pickaxe durability or enchantability");
        var modifiers = echoItem.getDefaultAttributeModifiers(net.minecraft.world.entity.EquipmentSlot.MAINHAND);
        double damage = 1.0 + modifiers.get(net.minecraft.world.entity.ai.attributes.Attributes.ATTACK_DAMAGE)
                .stream().mapToDouble(net.minecraft.world.entity.ai.attributes.AttributeModifier::getAmount).sum();
        double attackSpeed = 4.0 + modifiers.get(net.minecraft.world.entity.ai.attributes.Attributes.ATTACK_SPEED)
                .stream().mapToDouble(net.minecraft.world.entity.ai.attributes.AttributeModifier::getAmount).sum();
        if (Math.abs(damage - 6.0) > 1.0E-6 || Math.abs(attackSpeed - 1.2) > 1.0E-6)
            throw new IllegalStateException("unexpected attack damage/speed: " + damage + "/" + attackSpeed);
        System.out.println("[EchoVerify] netherite stats: durability=" + echoItem.getMaxDamage() + ", enchantability="
                + echoItem.getEnchantmentValue() + ", harvestLevel=" + echoPickaxe.getTier().getLevel()
                + ", totalDamage=" + damage + ", attackSpeed=" + attackSpeed);

        BlockState suitable = Blocks.STONE.defaultBlockState();
        BlockState unsuitable = Blocks.DIRT.defaultBlockState();
        if (!suitable.is(BlockTags.MINEABLE_WITH_PICKAXE) || unsuitable.is(BlockTags.MINEABLE_WITH_PICKAXE))
            throw new IllegalStateException("speed verification blocks no longer represent pickaxe suitability");
        ItemStack baseline = new ItemStack(netheriteItem);
        float baseSuitableSpeed = baseline.getDestroySpeed(suitable);
        float baseUnsuitableSpeed = baseline.getDestroySpeed(unsuitable);
        if (baseSuitableSpeed != 9.0F) throw new IllegalStateException("Netherite pickaxe baseline speed is not 9 on stone: " + baseSuitableSpeed);
        for (int resonance = 0; resonance <= 2; resonance++) {
            ItemStack test = new ItemStack(echoItem);
            EchoPickaxeData.setLevel(test, EchoPickaxeData.RESONANCE, resonance);
            float suitableSpeed = test.getDestroySpeed(suitable);
            float unsuitableSpeed = test.getDestroySpeed(unsuitable);
            if (suitableSpeed != 9.0F + resonance || unsuitableSpeed != baseUnsuitableSpeed)
                throw new IllegalStateException("resonance " + resonance + " speed mismatch: suitable=" + suitableSpeed + ", unsuitable=" + unsuitableSpeed);
            System.out.println("[EchoVerify] resonance=" + resonance + " baseSpeed=" + suitableSpeed);
        }
        ItemStack clamped = new ItemStack(echoItem);
        EchoPickaxeData.setLevel(clamped, EchoPickaxeData.RESONANCE, 99);
        if (clamped.getDestroySpeed(suitable) != 11.0F)
            throw new IllegalStateException("resonance level did not clamp to II");
        EchoPickaxeData.setLevel(clamped, EchoPickaxeData.RESONANCE, -1);
        if (clamped.getDestroySpeed(suitable) != 9.0F)
            throw new IllegalStateException("negative resonance level did not clamp to 0");

        boolean cleanEnvironment = player.onGround()
                && !player.isEyeInFluid(net.minecraft.tags.FluidTags.WATER)
                && !player.hasEffect(net.minecraft.world.effect.MobEffects.DIG_SPEED)
                && !player.hasEffect(net.minecraft.world.effect.MobEffects.DIG_SLOWDOWN);
        if (cleanEnvironment) {
            ItemStack originalHand = player.getMainHandItem().copy();
            try {
                ItemStack enchantedNetherite = new ItemStack(netheriteItem);
                EnchantmentHelper.setEnchantments(java.util.Map.of(Enchantments.BLOCK_EFFICIENCY, 3), enchantedNetherite);
                player.setItemInHand(InteractionHand.MAIN_HAND, enchantedNetherite);
                float efficiencyBaseline = player.getDestroySpeed(suitable);
                for (int resonance = 0; resonance <= 2; resonance++) {
                    ItemStack test = new ItemStack(echoItem);
                    EchoPickaxeData.setLevel(test, EchoPickaxeData.RESONANCE, resonance);
                    EnchantmentHelper.setEnchantments(java.util.Map.of(Enchantments.BLOCK_EFFICIENCY, 3), test);
                    player.setItemInHand(InteractionHand.MAIN_HAND, test);
                    float speed = player.getDestroySpeed(suitable);
                    if (Math.abs(speed - (efficiencyBaseline + resonance)) > 1.0E-5F)
                        throw new IllegalStateException("Efficiency III did not retain the resonance speed bonus: " + speed);
                    System.out.println("[EchoVerify] Efficiency III resonance=" + resonance + " playerSpeed=" + speed);
                }
            } finally {
                player.setItemInHand(InteractionHand.MAIN_HAND, originalHand);
            }
        } else {
            System.out.println("[EchoVerify] Efficiency III runtime composition skipped: player is not in a clean mining environment");
        }
    }

    private void verifyPickaxeItemProtection(ServerLevel level,ServerPlayer player) {
        var pos=player.position().add(0,2,0);
        for(var source:List.of(level.damageSources().onFire(),level.damageSources().lava(),level.damageSources().cactus())) {
            var entity=new net.minecraft.world.entity.item.ItemEntity(level,pos.x,pos.y,pos.z,ECHO_PICKAXE.get().getDefaultInstance());
            try {
                level.addFreshEntity(entity);
                boolean accepted=entity.hurt(source,100.0F);
                if(accepted || !entity.isAlive()) throw new IllegalStateException("Echo Pickaxe item entity did not reject fire/lava/cactus damage: "+source);
            } finally { entity.discard(); }
        }
        var vanilla=new net.minecraft.world.entity.item.ItemEntity(level,pos.x,pos.y,pos.z,new ItemStack(Items.DIAMOND_PICKAXE));
        try {
            level.addFreshEntity(vanilla);
            boolean controlTookDamage=vanilla.hurt(level.damageSources().cactus(),100.0F);
            if(!controlTookDamage || vanilla.isAlive()) throw new IllegalStateException("diamond pickaxe control unexpectedly resisted cactus damage");
        } finally { vanilla.discard(); }
    }

    private void verifyWardenDrops(net.minecraft.world.level.storage.loot.LootDataManager lootData,
                                   ServerLevel level, ServerPlayer player) {
        var table = lootData.getElement(new LootDataId<>(LootDataType.TABLE,
                new ResourceLocation("minecraft", "entities/warden")));
        var warden = EntityType.WARDEN.create(level);
        if (warden == null) throw new IllegalStateException("could not create a Warden loot-context entity");
        warden.setPos(player.position());
        ItemStack oldMain = player.getMainHandItem().copy();
        try {
            List<Set<Long>> hitsByLooting = new ArrayList<>();
            int samples = 1000;
            for (int looting = 0; looting <= 3; looting++) {
                ItemStack weapon = new ItemStack(Items.DIAMOND_SWORD);
                if (looting > 0) EnchantmentHelper.setEnchantments(Map.of(Enchantments.MOB_LOOTING, looting), weapon);
                player.setItemInHand(InteractionHand.MAIN_HAND, weapon);
                LootParams params = new LootParams.Builder(level)
                        .withParameter(LootContextParams.ORIGIN, player.position())
                        .withParameter(LootContextParams.THIS_ENTITY, warden)
                        .withParameter(LootContextParams.DAMAGE_SOURCE, level.damageSources().playerAttack(player))
                        .withParameter(LootContextParams.KILLER_ENTITY, player)
                        .withParameter(LootContextParams.DIRECT_KILLER_ENTITY, player)
                        .withParameter(LootContextParams.LAST_DAMAGE_PLAYER, player)
                        .create(LootContextParamSets.ENTITY);
                Set<Long> hits = new HashSet<>();
                for (int sample = 0; sample < samples; sample++) {
                    long seed = mixedLootSeed(0xA110L, sample);
                    var drops = table.getRandomItems(params, seed);
                    int templates = drops.stream().filter(stack -> stack.is(ECHO_UPGRADE_TEMPLATE.get()))
                            .mapToInt(ItemStack::getCount).sum();
                    int catalysts = drops.stream().filter(stack -> stack.is(Items.SCULK_CATALYST))
                            .mapToInt(ItemStack::getCount).sum();
                    if (templates > 1 || catalysts != 1)
                        throw new IllegalStateException("Warden loot did not preserve one catalyst / at most one template");
                    if (templates == 1) hits.add(seed);
                }
                double rate = hits.size() / (double) samples;
                double expected = 0.10 + looting * 0.01;
                if (Math.abs(rate - expected) > 0.04)
                    throw new IllegalStateException("Warden template rate outside broad Looting band at level " + looting + ": " + hits.size() + "/" + samples);
                if (looting > 0 && !hits.containsAll(hitsByLooting.get(looting - 1)))
                    throw new IllegalStateException("Warden Looting did not monotonically add same-seed template hits");
                hitsByLooting.add(hits);
                System.out.println("[EchoVerify] Warden Looting=" + looting + " templates=" + hits.size() + "/" + samples
                        + " expected=" + Math.round(expected * 100) + "%; catalyst=1");
            }

            LootParams nonPlayer = new LootParams.Builder(level)
                    .withParameter(LootContextParams.ORIGIN, player.position())
                    .withParameter(LootContextParams.THIS_ENTITY, warden)
                    .withParameter(LootContextParams.DAMAGE_SOURCE, level.damageSources().generic())
                    .create(LootContextParamSets.ENTITY);
            for (int sample = 0; sample < 128; sample++) {
                long seed = mixedLootSeed(0xB220L, sample);
                var drops = table.getRandomItems(nonPlayer, seed);
                if (drops.stream().anyMatch(stack -> stack.is(ECHO_UPGRADE_TEMPLATE.get()))
                        || drops.stream().filter(stack -> stack.is(Items.SCULK_CATALYST)).mapToInt(ItemStack::getCount).sum() != 1)
                    throw new IllegalStateException("non-player Warden death gained a template or lost its catalyst");
            }
            var zombieTable = lootData.getElement(new LootDataId<>(LootDataType.TABLE,
                    new ResourceLocation("minecraft", "entities/zombie")));
            LootParams playerKill = new LootParams.Builder(level)
                    .withParameter(LootContextParams.ORIGIN, player.position())
                    .withParameter(LootContextParams.THIS_ENTITY, warden)
                    .withParameter(LootContextParams.DAMAGE_SOURCE, level.damageSources().playerAttack(player))
                    .withParameter(LootContextParams.KILLER_ENTITY, player)
                    .withParameter(LootContextParams.DIRECT_KILLER_ENTITY, player)
                    .withParameter(LootContextParams.LAST_DAMAGE_PLAYER, player)
                    .create(LootContextParamSets.ENTITY);
            if (zombieTable.getRandomItems(playerKill, 0xB330L).stream()
                    .anyMatch(stack -> stack.is(ECHO_UPGRADE_TEMPLATE.get())))
                throw new IllegalStateException("Warden template modifier ran for a non-Warden loot table");
        } finally {
            player.setItemInHand(InteractionHand.MAIN_HAND, oldMain);
        }
    }

    private void verifySculkDrops(net.minecraft.world.level.storage.loot.LootDataManager lootData,
                                  ServerLevel level, ServerPlayer player) {
        boolean previousCreative = player.getAbilities().instabuild;
        if (previousCreative) { player.getAbilities().instabuild = false; player.onUpdateAbilities(); }
        ItemStack oldMain = player.getMainHandItem().copy();
        ItemStack oldOff = player.getOffhandItem().copy();
        try {
            var table = lootData.getElement(new LootDataId<>(LootDataType.TABLE, Blocks.SCULK.getLootTable()));
            List<Set<Long>> directHits = new ArrayList<>();
            int samples = 2000;
            for (int fortune = 0; fortune <= 3; fortune++) {
                ItemStack echo = upgradedEchoPickaxe(fortune);
                LootParams direct = sculkParams(level, player, Blocks.SCULK.defaultBlockState(), echo);
                Set<Long> hits = sampleEchoShardSeeds(table, direct, 0x1300L, samples);
                double rate = hits.size() / (double) samples;
                double expected = new double[]{0.10, 0.15, 0.20, 0.25}[fortune];
                if (Math.abs(rate - expected) > 0.04)
                    throw new IllegalStateException("sculk Fortune " + fortune + " rate outside broad band: " + hits.size() + "/" + samples);
                if (fortune > 0 && !hits.containsAll(directHits.get(fortune - 1)))
                    throw new IllegalStateException("sculk Fortune did not monotonically add same-seed bonus hits");
                directHits.add(hits);
                System.out.println("[EchoVerify] Sculk EchoPickaxe Fortune=" + fortune + " shards=" + hits.size()
                        + "/" + samples + " expected=" + Math.round(expected * 100) + "%");
            }

            ItemStack oldHoe = new ItemStack(Items.DIAMOND_HOE);
            ItemStack hoeFortuneThree = new ItemStack(Items.DIAMOND_HOE);
            EnchantmentHelper.setEnchantments(Map.of(Enchantments.BLOCK_FORTUNE, 3), hoeFortuneThree);
            ItemStack echoFortuneZero = upgradedEchoPickaxe(0);
            ItemStack echoFortuneThree = upgradedEchoPickaxe(3);

            player.setItemInHand(InteractionHand.OFF_HAND, echoFortuneZero);
            player.setItemInHand(InteractionHand.MAIN_HAND, oldHoe);
            Set<Long> hoeOffhandFortuneZero = sampleEchoShardSeeds(table,
                    sculkParams(level, player, Blocks.SCULK.defaultBlockState(), player.getMainHandItem()), 0x1300L, samples);
            player.setItemInHand(InteractionHand.MAIN_HAND, hoeFortuneThree);
            Set<Long> hoeFortuneMustNotContribute = sampleEchoShardSeeds(table,
                    sculkParams(level, player, Blocks.SCULK.defaultBlockState(), player.getMainHandItem()), 0x1300L, samples);
            if (!hoeOffhandFortuneZero.equals(directHits.get(0))
                    || !hoeFortuneMustNotContribute.equals(directHits.get(0)))
                throw new IllegalStateException("Hoe Fortune incorrectly changed offhand Echo Pickaxe shard chance");

            player.setItemInHand(InteractionHand.OFF_HAND, echoFortuneThree);
            player.setItemInHand(InteractionHand.MAIN_HAND, oldHoe);
            Set<Long> hoeOffhandFortuneThree = sampleEchoShardSeeds(table,
                    sculkParams(level, player, Blocks.SCULK.defaultBlockState(), player.getMainHandItem()), 0x1300L, samples);
            player.setItemInHand(InteractionHand.MAIN_HAND, hoeFortuneThree);
            Set<Long> bothFortuneThree = sampleEchoShardSeeds(table,
                    sculkParams(level, player, Blocks.SCULK.defaultBlockState(), player.getMainHandItem()), 0x1300L, samples);
            if (!hoeOffhandFortuneThree.equals(directHits.get(3)) || !bothFortuneThree.equals(directHits.get(3)))
                throw new IllegalStateException("Hoe/offhand combination did not use only Echo Pickaxe Fortune without stacking");

            ItemStack unupgradedFortuneThree = ECHO_PICKAXE.get().getDefaultInstance();
            EnchantmentHelper.setEnchantments(Map.of(Enchantments.BLOCK_FORTUNE, 3), unupgradedFortuneThree);
            if (!sampleEchoShardSeeds(table, sculkParams(level, player, Blocks.SCULK.defaultBlockState(), unupgradedFortuneThree),
                    0x1400L, 128).isEmpty())
                throw new IllegalStateException("unupgraded Echo Pickaxe received bonus shards");
            player.setItemInHand(InteractionHand.MAIN_HAND, new ItemStack(Items.DIAMOND_HOE));
            player.setItemInHand(InteractionHand.OFF_HAND, ItemStack.EMPTY);
            if (!sampleEchoShardSeeds(table, sculkParams(level, player, Blocks.SCULK.defaultBlockState(), player.getMainHandItem()),
                    0x1400L, 128).isEmpty())
                throw new IllegalStateException("Hoe without offhand Echo Pickaxe received bonus shards");
            player.setItemInHand(InteractionHand.OFF_HAND, unupgradedFortuneThree);
            if (!sampleEchoShardSeeds(table, sculkParams(level, player, Blocks.SCULK.defaultBlockState(), player.getMainHandItem()),
                    0x1400L, 128).isEmpty())
                throw new IllegalStateException("Hoe + unupgraded offhand Echo Pickaxe received bonus shards");

            LootParams wrongState = sculkParams(level, player, Blocks.SCULK_SENSOR.defaultBlockState(), echoFortuneThree);
            if (!sampleEchoShardSeeds(table, wrongState, 0x1450L, 128).isEmpty())
                throw new IllegalStateException("sculk sensor state received the sculk-block modifier");
            var sensorTable = lootData.getElement(new LootDataId<>(LootDataType.TABLE, Blocks.SCULK_SENSOR.getLootTable()));
            if (!sampleEchoShardSeeds(sensorTable, sculkParams(level, player, Blocks.SCULK_SENSOR.defaultBlockState(), echoFortuneThree),
                    0x14A0L, 128).isEmpty())
                throw new IllegalStateException("sculk sensor loot table received sculk-block bonus shards");
        } finally {
            player.setItemInHand(InteractionHand.MAIN_HAND, oldMain);
            player.setItemInHand(InteractionHand.OFF_HAND, oldOff);
            if (previousCreative) { player.getAbilities().instabuild = true; player.onUpdateAbilities(); }
        }
    }

    private static ItemStack upgradedEchoPickaxe(int fortune) {
        ItemStack echo = ECHO_PICKAXE.get().getDefaultInstance();
        EchoPickaxeData.setLevel(echo, EchoPickaxeData.TUNING, 1);
        if (fortune > 0) EnchantmentHelper.setEnchantments(Map.of(Enchantments.BLOCK_FORTUNE, fortune), echo);
        return echo;
    }

    private static LootParams sculkParams(ServerLevel level, ServerPlayer player, BlockState state, ItemStack tool) {
        return new LootParams.Builder(level).withParameter(LootContextParams.ORIGIN, player.position())
                .withParameter(LootContextParams.BLOCK_STATE, state).withParameter(LootContextParams.TOOL, tool)
                .withParameter(LootContextParams.THIS_ENTITY, player).create(LootContextParamSets.BLOCK);
    }

    private static Set<Long> sampleEchoShardSeeds(net.minecraft.world.level.storage.loot.LootTable table,
                                                   LootParams params, long firstSeed, int samples) {
        Set<Long> hits = new HashSet<>();
        for (int sample = 0; sample < samples; sample++) {
            long seed = mixedLootSeed(firstSeed, sample);
            int shards = table.getRandomItems(params, seed).stream().filter(stack -> stack.is(Items.ECHO_SHARD))
                    .mapToInt(ItemStack::getCount).sum();
            if (shards > 1) throw new IllegalStateException("sculk modifier generated more than one bonus shard");
            if (shards == 1) hits.add(seed);
        }
        return hits;
    }

    private static long mixedLootSeed(long salt, long sample) {
        long value = salt + 0x9E3779B97F4A7C15L * (sample + 1);
        value = (value ^ (value >>> 30)) * 0xBF58476D1CE4E5B9L;
        value = (value ^ (value >>> 27)) * 0x94D049BB133111EBL;
        return value ^ (value >>> 31);
    }

    private void verifyUpgradeRecipes(ServerLevel level,ServerPlayer player) {
        var manager=level.getServer().getRecipeManager();
        for(int rank=0;rank<=2;rank++) {
            ItemStack test=ECHO_PICKAXE.get().getDefaultInstance(); EchoPickaxeData.setLevel(test,EchoPickaxeData.RESONANCE,rank);
            if(cooldownTicks(test)!=(rank==0?100:rank==1?60:20)) throw new IllegalStateException("resonance cooldown mapping is wrong");
        }
        for(int rank=0;rank<=3;rank++) {
            ItemStack test=ECHO_PICKAXE.get().getDefaultInstance(); EchoPickaxeData.setLevel(test,EchoPickaxeData.FREQUENCY,rank);
            if(maxVeins(test)!=new int[]{1,3,5,8}[rank]) throw new IllegalStateException("frequency target limit is wrong");
            if(EchoPickaxeData.guidanceTicks(test)!=new int[]{140,280,420,560}[rank]) throw new IllegalStateException("frequency guidance duration is wrong");
        }
        for(int rank=0;rank<=2;rank++) {
            ItemStack test=ECHO_PICKAXE.get().getDefaultInstance(); EchoPickaxeData.setLevel(test,EchoPickaxeData.RESONANCE,rank);
            if(EchoPickaxeData.guidanceTicks(test)!=140) throw new IllegalStateException("resonance changed frequency-0 guidance duration");
        }
        ItemStack tuningOnly=ECHO_PICKAXE.get().getDefaultInstance(); EchoPickaxeData.setLevel(tuningOnly,EchoPickaxeData.TUNING,1);
        if(EchoPickaxeData.guidanceTicks(tuningOnly)!=140) throw new IllegalStateException("tuning changed frequency-0 guidance duration");
        ScanSession active=SCAN_SESSIONS.get(player.getUUID());
        if(active!=null && active.veins.size()>8) throw new IllegalStateException("live scan exceeded the protocol's eight vein cap");
        String[] ids={"echo_upgrade_resonance_1","echo_upgrade_resonance_2","echo_upgrade_frequency_1",
                "echo_upgrade_frequency_2","echo_upgrade_frequency_3","echo_upgrade_tuning",
                "echo_upgrade_extension_1","echo_upgrade_extension_2","echo_upgrade_extension_3"};
        Map<String,EchoSmithingRecipe> recipes=new HashMap<>();
        for(String path:ids) {
            var recipe=manager.byKey(new ResourceLocation(MOD_ID,path)).orElseThrow(() -> new IllegalStateException("missing "+path));
            if(!(recipe instanceof EchoSmithingRecipe echo) || echo.getSerializer()!=ECHO_UPGRADE_SERIALIZER.get())
                throw new IllegalStateException(path+" did not load with the custom serializer");
            recipes.put(path,echo);
            var buf=new net.minecraft.network.FriendlyByteBuf(io.netty.buffer.Unpooled.buffer());
            try {
                ECHO_UPGRADE_SERIALIZER.get().toNetwork(buf,echo);
                EchoSmithingRecipe copy=ECHO_UPGRADE_SERIALIZER.get().fromNetwork(echo.getId(),buf);
                if(!copy.upgradeKey().equals(echo.upgradeKey()) || copy.targetLevel()!=echo.targetLevel())
                    throw new IllegalStateException(path+" serializer network round-trip lost upgrade metadata");
            } finally { buf.release(); }
        }
        ItemStack tool=ECHO_PICKAXE.get().getDefaultInstance(); tool.setDamageValue(17);
        tool.setHoverName(Component.literal("Layered Echo"));
        EnchantmentHelper.setEnchantments(Map.of(Enchantments.BLOCK_EFFICIENCY,4),tool);
        if(matchesUpgrade(recipes.get("echo_upgrade_resonance_2"),level,tool,ENHANCED_RESONANCE_CRYSTAL.get()))
            throw new IllegalStateException("resonance II accepted a skipped level");
        if(matchesUpgrade(recipes.get("echo_upgrade_frequency_3"),level,tool,ENHANCED_FREQUENCY_CRYSTAL_2.get()))
            throw new IllegalStateException("frequency III accepted a skipped level");
        if(matchesUpgrade(recipes.get("echo_upgrade_extension_2"),level,tool,ENHANCED_EXTENSION_CRYSTAL.get())
                || matchesUpgrade(recipes.get("echo_upgrade_extension_3"),level,tool,ENHANCED_EXTENSION_CRYSTAL_2.get()))
            throw new IllegalStateException("extension upgrade accepted a skipped level");
        if(matchesUpgrade(recipes.get("echo_upgrade_tuning"),level,tool,TUNING_CRYSTAL.get()) && EchoPickaxeData.hasTuning(tool))
            throw new IllegalStateException("tuning was already present on fresh tool");
        tool=applyUpgrade(recipes.get("echo_upgrade_resonance_1"),level,tool,RESONANCE_CRYSTAL.get());
        tool=applyUpgrade(recipes.get("echo_upgrade_frequency_1"),level,tool,FREQUENCY_CRYSTAL.get());
        tool=applyUpgrade(recipes.get("echo_upgrade_tuning"),level,tool,TUNING_CRYSTAL.get());
        EchoPickaxeData.setFilter(tool,EchoOreKind.DIAMOND.id());
        ItemStack before=tool.copy();
        if(matchesUpgrade(recipes.get("echo_upgrade_tuning"),level,tool,TUNING_CRYSTAL.get()))
            throw new IllegalStateException("duplicate tuning level was accepted");
        tool=applyUpgrade(recipes.get("echo_upgrade_resonance_2"),level,tool,ENHANCED_RESONANCE_CRYSTAL.get());
        tool=applyUpgrade(recipes.get("echo_upgrade_frequency_2"),level,tool,ENHANCED_FREQUENCY_CRYSTAL.get());
        tool=applyUpgrade(recipes.get("echo_upgrade_frequency_3"),level,tool,ENHANCED_FREQUENCY_CRYSTAL_2.get());
        tool=applyUpgrade(recipes.get("echo_upgrade_extension_1"),level,tool,EXTENSION_CRYSTAL.get());
        tool=applyUpgrade(recipes.get("echo_upgrade_extension_2"),level,tool,ENHANCED_EXTENSION_CRYSTAL.get());
        tool=applyUpgrade(recipes.get("echo_upgrade_extension_3"),level,tool,ENHANCED_EXTENSION_CRYSTAL_2.get());
        if(EchoPickaxeData.level(tool,EchoPickaxeData.RESONANCE)!=2
                || EchoPickaxeData.level(tool,EchoPickaxeData.FREQUENCY)!=3
                || EchoPickaxeData.level(tool,EchoPickaxeData.EXTENSION)!=3
                || EchoPickaxeData.level(tool,EchoPickaxeData.TUNING)!=1
                || !EchoPickaxeData.filter(tool).equals(EchoOreKind.DIAMOND.id())
                || tool.getDamageValue()!=17 || !tool.hasCustomHoverName()
                || EnchantmentHelper.getItemEnchantmentLevel(Enchantments.BLOCK_EFFICIENCY,tool)!=4
                || before.getDamageValue()!=17)
            throw new IllegalStateException("upgrade chain failed to preserve independent NBT/name/enchant/damage");
    }
    private static boolean matchesUpgrade(EchoSmithingRecipe recipe,ServerLevel level,ItemStack tool,Item addition) {
        SimpleContainer grid=new SimpleContainer(3);
        grid.setItem(0,ECHO_UPGRADE_TEMPLATE.get().getDefaultInstance()); grid.setItem(1,tool);
        grid.setItem(2,addition.getDefaultInstance()); return recipe.matches(grid,level);
    }
    private static ItemStack applyUpgrade(EchoSmithingRecipe recipe,ServerLevel level,ItemStack tool,Item addition) {
        SimpleContainer grid=new SimpleContainer(3);
        grid.setItem(0,ECHO_UPGRADE_TEMPLATE.get().getDefaultInstance()); grid.setItem(1,tool);
        grid.setItem(2,addition.getDefaultInstance());
        if(!recipe.matches(grid,level)) throw new IllegalStateException("strict upgrade rejected valid preceding level: "+recipe.getId());
        return recipe.assemble(grid,level.registryAccess());
    }
    private void verifyCrystalRecipes(ServerLevel level, net.minecraft.world.item.crafting.RecipeManager manager) {
        Object[][] specs={
                {"resonance_crystal",Items.REDSTONE_BLOCK,ECHO_CRYSTAL.get()},
                {"enhanced_resonance_crystal",Items.DIAMOND_BLOCK,RESONANCE_CRYSTAL.get()},
                {"frequency_crystal",Items.AMETHYST_SHARD,ECHO_CRYSTAL.get()},
                {"enhanced_frequency_crystal",Items.DIAMOND,FREQUENCY_CRYSTAL.get()},
                {"enhanced_frequency_crystal_2",Items.DIAMOND_BLOCK,ENHANCED_FREQUENCY_CRYSTAL.get()},
                {"extension_crystal",Items.ENDER_EYE,ECHO_CRYSTAL.get()},
                {"enhanced_extension_crystal",Items.DIAMOND,EXTENSION_CRYSTAL.get()},
                {"enhanced_extension_crystal_2",Items.DIAMOND_BLOCK,ENHANCED_EXTENSION_CRYSTAL.get()},
                {"tuning_crystal",Items.NETHER_STAR,ECHO_CRYSTAL.get()}
        };
        int[] shards={0,2,3,5,6,7,8};
        for(Object[] spec:specs) {
            String id=(String)spec[0]; Item top=(Item)spec[1],center=(Item)spec[2];
            CraftingRecipe recipe=manager.byKey(new ResourceLocation(MOD_ID,id)).filter(CraftingRecipe.class::isInstance)
                    .map(CraftingRecipe.class::cast).orElseThrow(()->new IllegalStateException("missing crystal recipe "+id));
            var grid=new TransientCraftingContainer(new AbstractContainerMenu(null,0) {
                @Override public ItemStack quickMoveStack(Player player,int slot) { return ItemStack.EMPTY; }
                @Override public boolean stillValid(Player player) { return true; }
            },3,3);
            for(int slot:shards) grid.setItem(slot,new ItemStack(Items.ECHO_SHARD));
            grid.setItem(1,top.getDefaultInstance()); grid.setItem(4,center.getDefaultInstance());
            if(!recipe.matches(grid,level) || recipe.assemble(grid,level.registryAccess()).getItem()!=ITEMS.getEntries().stream()
                    .filter(entry->entry.getId().getPath().equals(id)).findFirst().orElseThrow().get())
                throw new IllegalStateException("crystal recipe layout/output failed: "+id);
        }
        if(matchesCrystalGrid(manager,level,"extension_crystal",Items.ENDER_PEARL,ECHO_CRYSTAL.get())
                || matchesCrystalGrid(manager,level,"enhanced_frequency_crystal",Items.DIAMOND_BLOCK,FREQUENCY_CRYSTAL.get())
                || matchesCrystalGrid(manager,level,"enhanced_frequency_crystal_2",Items.DIAMOND,ENHANCED_FREQUENCY_CRYSTAL.get())
                || matchesCrystalGrid(manager,level,"enhanced_extension_crystal",Items.DIAMOND_BLOCK,EXTENSION_CRYSTAL.get())
                || matchesCrystalGrid(manager,level,"enhanced_extension_crystal_2",Items.DIAMOND,ENHANCED_EXTENSION_CRYSTAL.get()))
            throw new IllegalStateException("crystal recipe accepted a wrong top ingredient");
    }

    private boolean matchesCrystalGrid(net.minecraft.world.item.crafting.RecipeManager manager,ServerLevel level,
                                       String id,Item top,Item center) {
        CraftingRecipe recipe=manager.byKey(new ResourceLocation(MOD_ID,id)).filter(CraftingRecipe.class::isInstance)
                .map(CraftingRecipe.class::cast).orElseThrow(()->new IllegalStateException("missing crystal recipe "+id));
        var grid=new TransientCraftingContainer(new AbstractContainerMenu(null,0) {
            @Override public ItemStack quickMoveStack(Player player,int slot) { return ItemStack.EMPTY; }
            @Override public boolean stillValid(Player player) { return true; }
        },3,3);
        for(int slot:new int[]{0,2,3,5,6,7,8}) grid.setItem(slot,new ItemStack(Items.ECHO_SHARD));
        grid.setItem(1,top.getDefaultInstance()); grid.setItem(4,center.getDefaultInstance());
        return recipe.matches(grid,level);
    }

    private static final class ScanSession {
        final ResourceLocation dimension;
        final long expiresAt;
        final int durationTicks;
        final List<Vein> veins;
        int selected;
        List<BlockPos> lastSent = List.of();
        ScanSession(ResourceLocation dimension, long expiresAt, int durationTicks, List<Vein> veins) {
            this.dimension=dimension; this.expiresAt=expiresAt; this.durationTicks=durationTicks; this.veins=veins;
        }
    }
    private static final class Vein {
        final EchoOreKind kind; final Set<BlockPos> blocks;
        Vein(EchoOreKind kind, Set<BlockPos> blocks) { this.kind=kind; this.blocks=blocks; }
    }
    private static List<BlockPos> sessionTargets(ServerPlayer player, ScanSession session) {
        return session.veins.stream().map(v -> representative(player, v)).toList();
    }
    private static BlockPos representative(ServerPlayer player, Vein vein) {
        return vein.blocks.stream().min(Comparator.comparingDouble(p -> p.distToCenterSqr(player.position())))
                .orElse(BlockPos.ZERO);
    }
    private static void sendSession(ServerPlayer player, ScanSession session, boolean force) {
        List<BlockPos> targets=sessionTargets(player,session);
        if (targets.isEmpty()) { SCAN_SESSIONS.remove(player.getUUID()); EchoNetwork.clearTarget(player); return; }
        BlockPos current=targets.get(session.selected);
        if (force || !targets.equals(session.lastSent)) {
            EchoNetwork.sendTargets(player,targets,session.selected,session.durationTicks);
            session.lastSent=List.copyOf(targets);
        }
        if (force) player.displayClientMessage(Component.translatable("message.echopickaxe.target_changed",
                session.selected+1,targets.size()).withStyle(ChatFormatting.AQUA),true);
    }
    public static void cycleTarget(ServerPlayer player) {
        ScanSession session=SCAN_SESSIONS.get(player.getUUID());
        if (session==null || !player.level().dimension().location().equals(session.dimension)
                || player.level().getGameTime()>=session.expiresAt) return;
        session.selected=(session.selected+1)%session.veins.size();
        sendSession(player,session,true);
    }
    public static void setOreFilter(ServerPlayer player, String id, InteractionHand hand) {
        ItemStack stack=player.getItemInHand(hand);
        EchoOreKind kind=EchoOreKind.byId(id);
        if (hand!=InteractionHand.MAIN_HAND || !stack.is(ECHO_PICKAXE.get()) || !EchoPickaxeData.hasTuning(stack) || kind==null) return;
        Long authorizedUntil=FILTER_SESSIONS.remove(player.getUUID());
        if (authorizedUntil==null) return;
        EchoPickaxeData.setFilter(stack,kind.id());
        SCAN_SESSIONS.remove(player.getUUID());
        EchoNetwork.clearTarget(player);
        if(!FMLEnvironment.production) System.out.println("[EchoVerify] server accepted ore filter="+kind.id()+" for tuned mainhand pickaxe");
        player.displayClientMessage(Component.translatable("message.echopickaxe.filter",
                Component.translatable("screen.echopickaxe.ore."+kind.id())).withStyle(ChatFormatting.AQUA),true);
    }
    @SubscribeEvent
    public void maintainScan(TickEvent.PlayerTickEvent event) {
        if (event.phase!=TickEvent.Phase.END || !(event.player instanceof ServerPlayer player)) return;
        ScanSession session=SCAN_SESSIONS.get(player.getUUID());
        if (session==null) return;
        if (!player.level().dimension().location().equals(session.dimension)
                || player.level().getGameTime()>=session.expiresAt) {
            SCAN_SESSIONS.remove(player.getUUID()); EchoNetwork.clearTarget(player); return;
        }
        if (player.level().getGameTime()%10!=0) return;
        Vein previousSelected=session.veins.get(session.selected);
        for (Vein vein:session.veins) vein.blocks.removeIf(pos -> !player.level().hasChunkAt(pos)
                || !vein.kind.matches(player.level().getBlockState(pos)));
        int oldIndex=session.selected;
        session.veins.removeIf(vein -> vein.blocks.isEmpty());
        if (session.veins.isEmpty()) { SCAN_SESSIONS.remove(player.getUUID()); EchoNetwork.clearTarget(player); return; }
        int stillSelected=session.veins.indexOf(previousSelected);
        if(stillSelected<0 && !FMLEnvironment.production) System.out.println("[EchoVerify] selected vein exhausted; advancing to next, remaining="+session.veins.size());
        session.selected=stillSelected>=0 ? stillSelected : oldIndex%session.veins.size();
        sendSession(player,session,false);
    }

    @SubscribeEvent
    public void clearScanOnLogout(PlayerEvent.PlayerLoggedOutEvent event) {
        SCAN_SESSIONS.remove(event.getEntity().getUUID());
        FILTER_SESSIONS.remove(event.getEntity().getUUID());
    }
    @SubscribeEvent
    public void clearScansOnServerStop(ServerStoppedEvent event) {
        SCAN_SESSIONS.clear();
        FILTER_SESSIONS.clear();
    }

    @SubscribeEvent
    public void addTooltip(ItemTooltipEvent event) {
        ItemStack stack=event.getItemStack();
        if (!stack.is(ECHO_PICKAXE.get())) return;
        event.getToolTip().add(Component.translatable("item.echopickaxe.echo_pickaxe.tip").withStyle(ChatFormatting.AQUA));
        int resonance=EchoPickaxeData.level(stack,EchoPickaxeData.RESONANCE);
        int frequency=EchoPickaxeData.level(stack,EchoPickaxeData.FREQUENCY);
        event.getToolTip().add(Component.translatable("item.echopickaxe.echo_pickaxe.tip2",
                EchoPickaxeData.scanRadius(stack),cooldownTicks(stack)/20,EchoPickaxeData.hasTuning(stack)
                        ? Component.translatable("item.echopickaxe.echo_pickaxe.filter_enabled") : Component.empty())
                .withStyle(ChatFormatting.GRAY));
        event.getToolTip().add(Component.translatable("item.echopickaxe.echo_pickaxe.guidance_duration",
                EchoPickaxeData.guidanceTicks(stack)/20).withStyle(ChatFormatting.GRAY));
        if (resonance>0) event.getToolTip().add(Component.translatable("item.echopickaxe.echo_pickaxe.upgrade.resonance",roman(resonance),resonance).withStyle(ChatFormatting.LIGHT_PURPLE));
        if (frequency>0) event.getToolTip().add(Component.translatable("item.echopickaxe.echo_pickaxe.upgrade.frequency",roman(frequency)).withStyle(ChatFormatting.LIGHT_PURPLE));
        int extension=EchoPickaxeData.level(stack,EchoPickaxeData.EXTENSION);
        if (extension>0) event.getToolTip().add(Component.translatable("item.echopickaxe.echo_pickaxe.upgrade.extension",roman(extension)).withStyle(ChatFormatting.LIGHT_PURPLE));
        if (EchoPickaxeData.hasTuning(stack)) {
            event.getToolTip().add(Component.translatable("item.echopickaxe.echo_pickaxe.upgrade.tuning").withStyle(ChatFormatting.LIGHT_PURPLE));
            event.getToolTip().add(Component.translatable("item.echopickaxe.echo_pickaxe.filter_status",
                    Component.translatable("screen.echopickaxe.ore."+EchoPickaxeData.filter(stack))).withStyle(ChatFormatting.GRAY));
        }
    }
    private static String roman(int value) { return switch(value) { case 1 -> "Ⅰ"; case 2 -> "Ⅱ"; case 3 -> "Ⅲ"; default -> ""; }; }
    private static int cooldownTicks(ItemStack stack) { return Math.max(20,(5-2*EchoPickaxeData.level(stack,EchoPickaxeData.RESONANCE))*20); }
    private static int maxVeins(ItemStack stack) { return new int[]{1,3,5,8}[EchoPickaxeData.level(stack,EchoPickaxeData.FREQUENCY)]; }

    private int buildDemo(Player player) {
        Level level = player.level();
        BlockPos origin = player.blockPosition();
        int demoY = Math.max(origin.getY() + 20, 160);
        if (demoY > level.getMaxBuildHeight() - 12) {
            player.displayClientMessage(Component.translatable("message.echopickaxe.demo_height").withStyle(ChatFormatting.RED), false);
            return 0;
        }
        BlockPos anchor = new BlockPos(origin.getX(), demoY, origin.getZ());
        for (BlockPos pos : BlockPos.betweenClosed(anchor.offset(-7, 1, -7), anchor.offset(7, 8, 7))) {
            if (!level.isEmptyBlock(pos)) {
                player.displayClientMessage(Component.translatable("message.echopickaxe.demo_blocked").withStyle(ChatFormatting.RED), false);
                return 0;
            }
        }

        BlockPos floor = anchor.above();
        for (int dx = -5; dx <= 5; dx++) {
            for (int dz = -3; dz <= 3; dz++) {
                boolean edge = Math.abs(dx) == 5 || Math.abs(dz) == 3;
                BlockPos tile = floor.offset(dx, 0, dz);
                level.setBlockAndUpdate(tile, edge && (dx + dz) % 2 == 0
                        ? Blocks.DEEPSLATE_TILES.defaultBlockState()
                        : Blocks.POLISHED_DEEPSLATE.defaultBlockState());
            }
        }
        level.setBlockAndUpdate(floor.offset(-2, 1, 0), Blocks.CRAFTING_TABLE.defaultBlockState());
        level.setBlockAndUpdate(floor.offset(-2, 1, -2), Blocks.SMITHING_TABLE.defaultBlockState());
        level.setBlockAndUpdate(floor.offset(0, 1, 2), Blocks.SCULK.defaultBlockState());
        level.setBlockAndUpdate(floor.offset(0, 1, -2), Blocks.DEEPSLATE_BRICKS.defaultBlockState());
        // Left target is exposed; the right target is intentionally behind this safe, new wall.
        for (int y = 1; y <= 4; y++) {
            for (int z = -2; z <= 2; z++) {
                level.setBlockAndUpdate(floor.offset(2, y, z), Blocks.POLISHED_DEEPSLATE.defaultBlockState());
            }
        }
        level.setBlockAndUpdate(anchor.offset(-4, 3, 0), Blocks.DIAMOND_ORE.defaultBlockState());
        level.setBlockAndUpdate(anchor.offset(4, 3, 0), Blocks.GOLD_ORE.defaultBlockState());

        ((ServerPlayer) player).teleportTo((ServerLevel) level,
                anchor.getX() + 1.25, floor.getY() + 1, anchor.getZ() + 0.5, -90.0F, 0.0F);
        player.getInventory().add(ECHO_PICKAXE.get().getDefaultInstance());
        player.getInventory().add(ECHO_CRYSTAL.get().getDefaultInstance());
        player.getInventory().add(RESONANCE_CRYSTAL.get().getDefaultInstance());
        player.getInventory().add(ENHANCED_RESONANCE_CRYSTAL.get().getDefaultInstance());
        player.getInventory().add(FREQUENCY_CRYSTAL.get().getDefaultInstance());
        player.getInventory().add(ENHANCED_FREQUENCY_CRYSTAL.get().getDefaultInstance());
        player.getInventory().add(ENHANCED_FREQUENCY_CRYSTAL_2.get().getDefaultInstance());
        player.getInventory().add(EXTENSION_CRYSTAL.get().getDefaultInstance());
        player.getInventory().add(ENHANCED_EXTENSION_CRYSTAL.get().getDefaultInstance());
        player.getInventory().add(ENHANCED_EXTENSION_CRYSTAL_2.get().getDefaultInstance());
        player.getInventory().add(TUNING_CRYSTAL.get().getDefaultInstance());
        player.getInventory().add(ECHO_UPGRADE_TEMPLATE.get().getDefaultInstance());
        player.getInventory().add(new ItemStack(Items.DIAMOND_PICKAXE));
        player.getInventory().add(new ItemStack(Items.ECHO_SHARD, 8));
        player.getInventory().add(new ItemStack(Items.DIAMOND, 8));
        player.getInventory().add(new ItemStack(Items.COBBLED_DEEPSLATE));
        player.displayClientMessage(Component.translatable("message.echopickaxe.demo_ready").withStyle(ChatFormatting.AQUA), false);
        return Command.SINGLE_SUCCESS;
    }

    private static final class EchoPickaxe extends PickaxeItem {
        private EchoPickaxe(Properties properties) { super(Tiers.NETHERITE,1,-2.8F,properties); }
        @Override public float getDestroySpeed(ItemStack stack, BlockState state) {
            float speed = super.getDestroySpeed(stack, state);
            return state.is(BlockTags.MINEABLE_WITH_PICKAXE)
                    ? speed + EchoPickaxeData.level(stack, EchoPickaxeData.RESONANCE) : speed;
        }
        @Override public boolean canBeHurtBy(net.minecraft.world.damagesource.DamageSource source) {
            return !source.is(net.minecraft.world.damagesource.DamageTypes.CACTUS) && super.canBeHurtBy(source);
        }
        @Override public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
            ItemStack stack=player.getItemInHand(hand);
            if (level.isClientSide) return InteractionResultHolder.success(stack);
            if (hand!=InteractionHand.MAIN_HAND) return InteractionResultHolder.pass(stack);
            if (player.isCrouching()) {
                if (EchoPickaxeData.hasTuning(stack)) {
                    ServerPlayer server=(ServerPlayer)player;
                    FILTER_SESSIONS.put(player.getUUID(),Long.MAX_VALUE);
                    EchoNetwork.openFilter(server,EchoPickaxeData.filter(stack));
                }
                else player.displayClientMessage(Component.translatable("message.echopickaxe.tuning_required").withStyle(ChatFormatting.GRAY),true);
                return InteractionResultHolder.success(stack);
            }
            if (player.getCooldowns().isOnCooldown(this)) return InteractionResultHolder.fail(stack);
            int cooldown=cooldownTicks(stack);
            BlockPos center=player.blockPosition();
            int r=EchoPickaxeData.scanRadius(stack), r2=r*r;
            EchoOreKind filter=EchoOreKind.byId(EchoPickaxeData.filter(stack));
            Set<BlockPos> remaining=new HashSet<>(); Map<BlockPos,EchoOreKind> kinds=new HashMap<>();
            long scanStarted=System.nanoTime();
            int loadedChunks=0, scannedBlocks=0;
            int minChunkX=Math.floorDiv(center.getX()-r,16), maxChunkX=Math.floorDiv(center.getX()+r,16);
            int minChunkZ=Math.floorDiv(center.getZ()-r,16), maxChunkZ=Math.floorDiv(center.getZ()+r,16);
            int minBuildY=level.getMinBuildHeight(), maxBuildY=level.getMaxBuildHeight()-1;
            for(int chunkX=minChunkX;chunkX<=maxChunkX;chunkX++) for(int chunkZ=minChunkZ;chunkZ<=maxChunkZ;chunkZ++) {
                int chunkMinX=chunkX<<4, chunkMinZ=chunkZ<<4;
                int x0=Math.max(center.getX()-r,chunkMinX), x1=Math.min(center.getX()+r,chunkMinX+15);
                int z0=Math.max(center.getZ()-r,chunkMinZ), z1=Math.min(center.getZ()+r,chunkMinZ+15);
                if(x0>x1 || z0>z1 || !level.hasChunkAt(new BlockPos(x0,center.getY(),z0))) continue;
                loadedChunks++;
                for(int x=x0;x<=x1;x++) for(int z=z0;z<=z1;z++) {
                    int dx=x-center.getX(), dz=z-center.getZ(), remainingRadius=r2-dx*dx-dz*dz;
                    if(remainingRadius<0) continue;
                    int dy=(int)Math.floor(Math.sqrt(remainingRadius));
                    int y0=Math.max(minBuildY,center.getY()-dy), y1=Math.min(maxBuildY,center.getY()+dy);
                    for(int y=y0;y<=y1;y++) {
                        scannedBlocks++;
                        BlockPos pos=new BlockPos(x,y,z);
                        var state=level.getBlockState(pos);
                        if(filter!=null && filter.matches(state)) {
                            EchoOreKind kind=oreKind(state);
                            if(kind!=null) { remaining.add(pos); kinds.put(pos,kind); }
                        }
                    }
                }
            }
            List<Vein> veins=new ArrayList<>();
            while (!remaining.isEmpty()) {
                BlockPos seed=remaining.iterator().next(); EchoOreKind kind=kinds.get(seed);
                Set<BlockPos> cluster=new HashSet<>(); ArrayDeque<BlockPos> queue=new ArrayDeque<>();
                remaining.remove(seed); queue.add(seed);
                while(!queue.isEmpty()) {
                    BlockPos pos=queue.removeFirst(); cluster.add(pos);
                    for (var direction:net.minecraft.core.Direction.values()) {
                        BlockPos neighbor=pos.relative(direction);
                        if (kind==kinds.get(neighbor) && remaining.remove(neighbor)) queue.addLast(neighbor);
                    }
                }
                veins.add(new Vein(kind,cluster));
            }
            veins.sort(Comparator.comparingDouble(v -> representative((ServerPlayer)player,v).distToCenterSqr(player.position())));
            int maxVeins=maxVeins(stack);
            if (veins.size()>maxVeins) veins=new ArrayList<>(veins.subList(0,maxVeins));
            long scanMillis=(System.nanoTime()-scanStarted)/1_000_000L;
            if(!FMLEnvironment.production) System.out.println("[EchoVerify] scan radius="+r+" filter="+filter.id()+" veins="+veins.size()+" cap="+maxVeins
                    +" cooldown="+cooldown+" loadedChunks="+loadedChunks+" scannedBlocks="+scannedBlocks+" scanMillis="+scanMillis
                    +" kinds="+veins.stream().map(v->v.kind.id()).toList()
                    +" targets="+veins.stream().map(v->representative((ServerPlayer)player,v)).toList());
            player.getCooldowns().addCooldown(this,cooldown);
            level.playSound(null,player.blockPosition(),SoundEvents.SCULK_CLICKING,SoundSource.PLAYERS,0.7F,1.15F);
            ServerPlayer serverPlayer=(ServerPlayer)player;
            if (veins.isEmpty()) {
                SCAN_SESSIONS.remove(player.getUUID()); EchoNetwork.clearTarget(serverPlayer);
                player.displayClientMessage(Component.translatable("message.echopickaxe.none",r).withStyle(ChatFormatting.GRAY),true);
            } else {
                int durationTicks=EchoPickaxeData.guidanceTicks(stack);
                ScanSession session=new ScanSession(level.dimension().location(),level.getGameTime()+durationTicks,durationTicks,veins);
                SCAN_SESSIONS.put(player.getUUID(),session);
                List<BlockPos> targets=sessionTargets(serverPlayer,session);
                EchoNetwork.startTargets(serverPlayer,targets,0,durationTicks); session.lastSent=List.copyOf(targets);
                BlockPos ore=targets.get(0); double distance=Math.sqrt(ore.distToCenterSqr(player.position()));
                player.displayClientMessage(Component.translatable("message.echopickaxe.found",
                        String.format(java.util.Locale.ROOT,"%.1f",distance),ore.getX(),ore.getY(),ore.getZ()).withStyle(ChatFormatting.AQUA),true);
                if (veins.size()>1) player.displayClientMessage(Component.translatable("message.echopickaxe.scan_count",veins.size()).withStyle(ChatFormatting.AQUA),false);
            }
            return InteractionResultHolder.success(stack);
        }
        private static EchoOreKind oreKind(net.minecraft.world.level.block.state.BlockState state) {
            for (EchoOreKind kind:EchoOreKind.values()) if(kind!=EchoOreKind.ALL && kind.matches(state)) return kind;
            return null;
        }
    }
}
