package com.jaysay.echotools.client;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.jaysay.echotools.EchoMod;
import com.jaysay.echotools.EchoPickaxeData;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.renderer.block.model.BakedQuad;
import net.minecraft.client.renderer.item.ItemProperties;
import net.minecraft.client.resources.model.ModelBakery;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.enchantment.Enchantments;
import net.minecraft.core.Direction;
import net.minecraft.util.RandomSource;
import net.minecraftforge.client.model.IQuadTransformer;
import net.minecraftforge.client.event.ModelEvent;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;

import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/** Client-only item predicate and development verification for Echo Pickaxe variants. */
@Mod.EventBusSubscriber(modid = EchoMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.MOD)
public final class EchoItemVisuals {
    public static final ResourceLocation UPGRADE_VISUAL = new ResourceLocation(EchoMod.MOD_ID, "upgrade_visual");

    private EchoItemVisuals() {}

    @SubscribeEvent
    public static void onClientSetup(FMLClientSetupEvent event) {
        event.enqueueWork(() -> ItemProperties.register(EchoMod.ECHO_PICKAXE.get(), UPGRADE_VISUAL,
                (stack, level, entity, seed) -> visualIndex(stack)));
    }

    @SubscribeEvent
    public static void registerVariantModels(ModelEvent.RegisterAdditional event) {
        for (int index = 1; index <= 95; index++) {
            event.register(new ResourceLocation(EchoMod.MOD_ID, "item/echo_pickaxe_v%03d".formatted(index)));
        }
    }

    /** Maps clamped upgrade state to the asset override range 0..95. */
    public static int visualIndex(ItemStack stack) {
        int resonance = EchoPickaxeData.level(stack, EchoPickaxeData.RESONANCE);
        int frequency = EchoPickaxeData.level(stack, EchoPickaxeData.FREQUENCY);
        int tuning = EchoPickaxeData.level(stack, EchoPickaxeData.TUNING);
        int extension = EchoPickaxeData.level(stack, EchoPickaxeData.EXTENSION);
        return resonance * 32 + frequency * 8 + tuning * 4 + extension;
    }

    public static Screen createWhiteShowcaseScreen() {
        ItemStack base = new ItemStack(EchoMod.ECHO_PICKAXE.get());
        ItemStack resonance = upgradedStack(2, 0, 0, 0);
        ItemStack frequency = upgradedStack(0, 3, 0, 0);
        ItemStack tuning = upgradedStack(0, 0, 1, 0);
        ItemStack extension = upgradedStack(0, 0, 0, 3);
        ItemStack maximum = upgradedStack(2, 3, 1, 3);
        return new WhiteShowcaseScreen(new ItemStack[]{base, resonance, frequency, tuning, extension, maximum},
                new String[]{"BASE", "RESONANCE II", "FREQUENCY III", "TUNING I", "EXTENSION III", "ALL MAX"});
    }

    public static void verifyUpgradeShowcaseInventory(Minecraft minecraft) {
        int[][] expected = {
                {0, 0, 0, 0}, {1, 0, 0, 0}, {2, 2, 1, 1}, {2, 3, 1, 3}
        };
        for (int slot = 0; slot < expected.length; slot++) {
            ItemStack stack = minecraft.player.getInventory().getItem(slot);
            int[] actual = {
                    EchoPickaxeData.level(stack, EchoPickaxeData.RESONANCE),
                    EchoPickaxeData.level(stack, EchoPickaxeData.FREQUENCY),
                    EchoPickaxeData.level(stack, EchoPickaxeData.TUNING),
                    EchoPickaxeData.level(stack, EchoPickaxeData.EXTENSION)
            };
            if (!stack.is(EchoMod.ECHO_PICKAXE.get()) || !java.util.Arrays.equals(actual, expected[slot])) {
                throw new IllegalStateException("Hotbar showcase slot " + slot + " expected Echo Pickaxe levels "
                        + java.util.Arrays.toString(expected[slot]) + ", got "
                        + stack.getItem() + " " + java.util.Arrays.toString(actual));
            }
        }
        System.out.println("[EchoVisualSmoke] PASS: hotbar contains verified base, single-upgrade, mixed, and full-max pickaxes.");
    }

    private static ItemStack upgradedStack(int resonance, int frequency, int tuning, int extension) {
        ItemStack stack = new ItemStack(EchoMod.ECHO_PICKAXE.get());
        EchoPickaxeData.setLevel(stack, EchoPickaxeData.RESONANCE, resonance);
        EchoPickaxeData.setLevel(stack, EchoPickaxeData.FREQUENCY, frequency);
        EchoPickaxeData.setLevel(stack, EchoPickaxeData.TUNING, tuning);
        EchoPickaxeData.setLevel(stack, EchoPickaxeData.EXTENSION, extension);
        return stack;
    }

    private static final class WhiteShowcaseScreen extends Screen {
        private static final int[] ATTRIBUTES = {0xFFD9474E, 0xFF8151C5, 0xFF27A7D8, 0xFF3A9C64};
        private final ItemStack[] stacks;
        private final String[] labels;

        private WhiteShowcaseScreen(ItemStack[] stacks, String[] labels) {
            super(Component.literal("Echo Pickaxe Visual Showcase"));
            this.stacks = stacks;
            this.labels = labels;
        }

        @Override
        public boolean isPauseScreen() {
            return false;
        }

        @Override
        public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
            graphics.fill(0, 0, width, height, 0xFFFAFCFF);
            graphics.drawCenteredString(font, "ECHO PICKAXE", width / 2, 72, 0xFF17233B);
            graphics.drawCenteredString(font, "Four upgrade marks can combine on one tool", width / 2, 94, 0xFF52627A);
            int columns = stacks.length;
            int cardWidth = Math.min(176, width / columns - 12);
            int cardTop = 144;
            int cardBottom = Math.min(height - 104, 494);
            for (int i = 0; i < columns; i++) {
                int centerX = (i + 1) * width / (columns + 1);
                int left = centerX - cardWidth / 2;
                graphics.fill(left, cardTop, left + cardWidth, cardBottom, 0xFFF0F4F8);
                graphics.fill(left, cardTop, left + cardWidth, cardTop + 2, i == 5 ? 0xFF20A7B0 : 0xFFCAD4E0);
                graphics.drawCenteredString(font, labels[i], centerX, cardTop + 20, 0xFF26344B);
                if (i > 0 && i < 5) {
                    graphics.fill(centerX - 3, cardTop + 46, centerX + 4, cardTop + 53, ATTRIBUTES[i - 1]);
                } else if (i == 5) {
                    for (int mark = 0; mark < ATTRIBUTES.length; mark++) {
                        graphics.fill(centerX - 14 + mark * 9, cardTop + 46, centerX - 7 + mark * 9,
                                cardTop + 53, ATTRIBUTES[mark]);
                    }
                }
                graphics.pose().pushPose();
                graphics.pose().translate(centerX - 40, cardTop + 88, 0);
                graphics.pose().scale(5.0F, 5.0F, 1.0F);
                graphics.renderItem(stacks[i], 0, 0);
                graphics.pose().popPose();
                graphics.drawCenteredString(font, "echopickaxe", centerX, cardTop + 236, 0xFF66758B);
            }
            graphics.drawCenteredString(font, "Live Minecraft ItemRenderer · GUI-scale preview", width / 2, height - 64, 0xFF66758B);
        }
    }

    /**
     * Dev-smoke assertion against Minecraft's real item override resolver. This catches
     * missing JSONs, stale predicate registration, and wrong model threshold mappings.
     */
    public static void verifyResolvedVariants(Minecraft minecraft, String phase) {
        verifyModelJsonContract(minecraft, phase);
        Item item = EchoMod.ECHO_PICKAXE.get();
        ItemStack base = new ItemStack(item);
        requireResolved(minecraft, base, 0, phase + " base/no NBT");

        for (int resonance = 0; resonance <= 2; resonance++) {
            for (int frequency = 0; frequency <= 3; frequency++) {
                for (int tuning = 0; tuning <= 1; tuning++) {
                    for (int extension = 0; extension <= 3; extension++) {
                        ItemStack stack = new ItemStack(item);
                        EchoPickaxeData.setLevel(stack, EchoPickaxeData.RESONANCE, resonance);
                        EchoPickaxeData.setLevel(stack, EchoPickaxeData.FREQUENCY, frequency);
                        EchoPickaxeData.setLevel(stack, EchoPickaxeData.TUNING, tuning);
                        EchoPickaxeData.setLevel(stack, EchoPickaxeData.EXTENSION, extension);
                        int index = visualIndex(stack);
                        requireResolved(minecraft, stack, index, phase + " levels "
                                + resonance + "/" + frequency + "/" + tuning + "/" + extension);
                    }
                }
            }
        }

        verifyClampAndUnrelatedData(minecraft, phase);
        System.out.println("[EchoVisualSmoke] PASS: Minecraft resolved base plus all 95 upgrade models (" + phase + ").");
    }

    private static void verifyModelJsonContract(Minecraft minecraft, String phase) {
        JsonObject base = readModel(minecraft, "echo_pickaxe");
        JsonArray overrides = base.getAsJsonArray("overrides");
        if (overrides == null || overrides.size() != 95) {
            throw new IllegalStateException("Base pickaxe model must declare exactly 95 visual overrides (" + phase + ")");
        }
        pixelModelContract(base.getAsJsonArray("elements"), "echo_pickaxe");
        for (int index = 1; index <= 95; index++) {
            JsonObject override = overrides.get(index - 1).getAsJsonObject();
            JsonObject predicate = override.getAsJsonObject("predicate");
            String property = EchoMod.MOD_ID + ":upgrade_visual";
            String variantName = "echo_pickaxe_v%03d".formatted(index);
            String expectedName = EchoMod.MOD_ID + ":item/" + variantName;
            float threshold = predicate == null || !predicate.has(property) ? Float.NaN : predicate.get(property).getAsFloat();
            if (threshold != index || !expectedName.equals(override.get("model").getAsString())) {
                throw new IllegalStateException("Base pickaxe override " + index + " must map threshold " + index
                        + " to " + expectedName + " (" + phase + ")");
            }
            JsonObject variant = readModel(minecraft, variantName);
            if (variant.has("parent") || variant.has("overrides")) {
                throw new IllegalStateException("Variant " + expectedName + " must be parentless and have no overrides");
            }
            for (String key : new String[]{"gui_light", "display", "ambientocclusion"}) {
                if (!base.has(key) || !variant.has(key) || !base.get(key).equals(variant.get(key))) {
                    throw new IllegalStateException("Variant " + expectedName + " changed base " + key + " data");
                }
            }
            verifyVariantTextures(variant, variantName);
            verifyGlowBindings(variant.getAsJsonArray("elements"), expectedName);
            pixelModelContract(variant.getAsJsonArray("elements"), variantName);
        }
    }

    private static void verifyVariantTextures(JsonObject variant, String variantName) {
        JsonObject textures = variant.getAsJsonObject("textures");
        if (textures == null
                || !textures.has("layer0") || !textures.get("layer0").getAsString().equals(EchoMod.MOD_ID + ":item/" + variantName)
                || !textures.has("glow") || !textures.get("glow").getAsString().equals(EchoMod.MOD_ID + ":item/" + variantName + "_glow")
                || !textures.has("particle") || !textures.get("particle").getAsString().equals("#layer0")) {
            throw new IllegalStateException("Variant " + variantName + " must reference its matching base/glow textures");
        }
    }

    /**
     * Validate the registered item's native 64x64 mesh. The grid occupies
     * the same 16-unit model space as the upgraded meshes.
     */
    private static void pixelModelContract(JsonArray elements, String modelId) {
        if (elements == null) throw new IllegalStateException("Missing elements in " + modelId);
        if (elements.isEmpty()) throw new IllegalStateException("Missing pixel voxels in " + modelId);
        JsonObject firstElement = elements.get(0).getAsJsonObject();
        JsonArray firstFrom = firstElement.getAsJsonArray("from");
        JsonArray firstTo = firstElement.getAsJsonArray("to");
        double firstCellWidth = firstTo.get(0).getAsDouble() - firstFrom.get(0).getAsDouble();
        int grid = exactPixel(16.0 / firstCellWidth, modelId);
        int expectedGrid = modelId.equals("echo_pickaxe") ? 64 : modelId.matches("echo_pickaxe_v\\d{3}") ? 128 : -1;
        if (grid != expectedGrid) {
            throw new IllegalStateException("Pixel grid in " + modelId + " must match its registered texture size (expected " + expectedGrid + "x" + expectedGrid + ", got " + grid + ")");
        }
        double cell = 16.0 / grid;
        Map<Integer, JsonObject> pixels = new HashMap<>();
        for (JsonElement elementValue : elements) {
            JsonObject element = elementValue.getAsJsonObject();
            if (element.has("rotation") || !element.has("shade") || !element.get("shade").isJsonPrimitive()
                    || element.get("shade").getAsBoolean()) {
                throw new IllegalStateException("Pixel voxels in " + modelId + " must remain unrotated and unshaded");
            }
            JsonArray from = element.getAsJsonArray("from");
            JsonArray to = element.getAsJsonArray("to");
            if (from == null || to == null || from.size() != 3 || to.size() != 3) {
                throw new IllegalStateException("Invalid pixel box bounds in " + modelId);
            }
            int x = exactPixel(from.get(0).getAsDouble() / cell, modelId);
            int y = exactPixel((16.0 - to.get(1).getAsDouble()) / cell, modelId);
            int pixel = y * grid + x;
            if (x < 0 || x >= grid || y < 0 || y >= grid) {
                throw new IllegalStateException("Pixel outside " + grid + "x" + grid + " item texture in " + modelId + ": " + x + "," + y);
            }
            requireCoordinate(from.get(0).getAsDouble(), x * cell, modelId);
            requireCoordinate(from.get(1).getAsDouble(), 16.0 - (y + 1) * cell, modelId);
            requireCoordinate(from.get(2).getAsDouble(), 7.5, modelId);
            requireCoordinate(to.get(0).getAsDouble(), (x + 1) * cell, modelId);
            requireCoordinate(to.get(1).getAsDouble(), 16.0 - y * cell, modelId);
            requireCoordinate(to.get(2).getAsDouble(), 8.5, modelId);
            if (pixels.putIfAbsent(pixel, element) != null) {
                throw new IllegalStateException("Duplicate pixel box " + x + "," + y + " in " + modelId);
            }
        }

        Set<Integer> pixelSet = pixels.keySet();

        for (Map.Entry<Integer, JsonObject> entry : pixels.entrySet()) {
            int x = entry.getKey() % grid;
            int y = entry.getKey() / grid;
            JsonObject faces = entry.getValue().getAsJsonObject("faces");
            if (faces == null) throw new IllegalStateException("Missing faces in " + modelId);
            Set<String> expectedFaces = new HashSet<>(Set.of("north", "south"));
            if (x == 0 || !pixelSet.contains(y * grid + x - 1)) expectedFaces.add("west");
            if (x == grid - 1 || !pixelSet.contains(y * grid + x + 1)) expectedFaces.add("east");
            if (y == 0 || !pixelSet.contains((y - 1) * grid + x)) expectedFaces.add("up");
            if (y == grid - 1 || !pixelSet.contains((y + 1) * grid + x)) expectedFaces.add("down");
            Set<String> actualFaces = new HashSet<>(faces.keySet());
            if (!actualFaces.equals(expectedFaces)) {
                throw new IllegalStateException("Incorrect exposed side faces at " + x + "," + y + " in " + modelId
                        + ": expected " + expectedFaces + ", got " + actualFaces);
            }
            double centerU = (x + 0.5) * cell;
            double centerV = (y + 0.5) * cell;
            for (Map.Entry<String, JsonElement> faceEntry : faces.entrySet()) {
                JsonArray uv = faceEntry.getValue().getAsJsonObject().getAsJsonArray("uv");
                if (uv == null || uv.size() != 4) {
                    throw new IllegalStateException("Invalid center UV on " + faceEntry.getKey() + " in " + modelId);
                }
                for (int coordinate = 0; coordinate < 4; coordinate++) {
                    requireCoordinate(uv.get(coordinate).getAsDouble(), coordinate % 2 == 0 ? centerU : centerV, modelId);
                }
            }
        }
    }

    private static int exactPixel(double value, String modelId) {
        int pixel = (int) Math.round(value);
        if (Math.abs(value - pixel) > 0.0001) {
            throw new IllegalStateException("Non-pixel-aligned geometry in " + modelId + ": " + value);
        }
        return pixel;
    }

    private static void requireCoordinate(double actual, double expected, String modelId) {
        if (Math.abs(actual - expected) > 0.0001) {
            throw new IllegalStateException("Unexpected pixel geometry/UV in " + modelId + ": expected "
                    + expected + ", got " + actual);
        }
    }

    private static void verifyGlowBindings(JsonArray elements, String modelId) {
        if (elements == null) throw new IllegalStateException("Missing elements in " + modelId);
        for (JsonElement element : elements) {
            JsonObject faces = element.getAsJsonObject().getAsJsonObject("faces");
            if (faces == null) throw new IllegalStateException("Missing faces in " + modelId);
            for (Map.Entry<String, JsonElement> entry : faces.entrySet()) {
                JsonObject face = entry.getValue().getAsJsonObject();
                String texture = face.get("texture").getAsString();
                if (texture.equals("#glow")) {
                    JsonObject forgeData = face.getAsJsonObject("forge_data");
                    if (forgeData == null || !forgeData.has("block_light") || forgeData.get("block_light").getAsInt() != 15
                            || !forgeData.has("sky_light") || forgeData.get("sky_light").getAsInt() != 15
                            || !forgeData.has("ambient_occlusion") || forgeData.get("ambient_occlusion").getAsBoolean()) {
                        throw new IllegalStateException("Glow face " + entry.getKey() + " on " + modelId
                                + " must use block/sky light 15 and disable AO");
                    }
                } else if (face.has("forge_data")) {
                    throw new IllegalStateException("Non-glow face " + entry.getKey() + " on " + modelId + " must not have forge_data");
                }
            }
        }
    }

    private static JsonObject readModel(Minecraft minecraft, String name) {
        ResourceLocation resourceId = new ResourceLocation(EchoMod.MOD_ID, "models/item/" + name + ".json");
        var resource = minecraft.getResourceManager().getResource(resourceId).orElseThrow(
                () -> new IllegalStateException("Missing model JSON " + resourceId));
        try (var reader = new InputStreamReader(resource.open(), StandardCharsets.UTF_8)) {
            return JsonParser.parseReader(reader).getAsJsonObject();
        } catch (java.io.IOException error) {
            throw new IllegalStateException("Cannot read model JSON " + resourceId, error);
        }
    }

    private static void verifyClampAndUnrelatedData(Minecraft minecraft, String phase) {
        ItemStack stack = new ItemStack(EchoMod.ECHO_PICKAXE.get());
        var upgrades = stack.getOrCreateTag().getCompound(EchoPickaxeData.NBT_ROOT);
        upgrades.putInt(EchoPickaxeData.RESONANCE, 99);
        upgrades.putInt(EchoPickaxeData.FREQUENCY, -12);
        upgrades.putInt(EchoPickaxeData.TUNING, 99);
        upgrades.putInt(EchoPickaxeData.EXTENSION, 99);
        stack.getOrCreateTag().put(EchoPickaxeData.NBT_ROOT, upgrades);
        if (visualIndex(stack) != 71) {
            throw new IllegalStateException("Echo upgrade visual clamp failed: expected 71, got " + visualIndex(stack));
        }
        requireResolved(minecraft, stack, 71, phase + " invalid-level clamp");

        stack.setDamageValue(17);
        stack.setHoverName(Component.literal("Predicate smoke"));
        stack.enchant(Enchantments.BLOCK_EFFICIENCY, 1);
        EchoPickaxeData.setFilter(stack, "diamond");
        if (visualIndex(stack) != 71) {
            throw new IllegalStateException("Damage, name, enchantment, or filter changed the visual index");
        }
        requireResolved(minecraft, stack, 71, phase + " damage/name/enchantment/filter");
    }

    private static void requireResolved(Minecraft minecraft, ItemStack stack, int index, String context) {
        if (index < 0 || index > 95) throw new IllegalStateException("Visual index out of range: " + index);
        Item item = stack.getItem();
        ResourceLocation modelId = index == 0
                ? new ResourceLocation(EchoMod.MOD_ID, "item/echo_pickaxe")
                : new ResourceLocation(EchoMod.MOD_ID, "item/echo_pickaxe_v%03d".formatted(index));
        BakedModel expected = index == 0
                ? minecraft.getItemRenderer().getItemModelShaper().getItemModel(item)
                : minecraft.getModelManager().getModel(modelId);
        BakedModel missing = minecraft.getModelManager().getModel(ModelBakery.MISSING_MODEL_LOCATION);
        if (expected == missing) {
            throw new IllegalStateException("Missing baked variant asset " + modelId + " for " + context);
        }
        BakedModel resolved = minecraft.getItemRenderer().getModel(stack, minecraft.level, minecraft.player, 0);
        if (resolved != expected) {
            throw new IllegalStateException("ItemOverrides.resolve chose " + describe(resolved) + " instead of "
                    + modelId + " for " + context + " (index=" + index + ")");
        }
        requireAnimatedFaceLayers(resolved, modelId, context);
    }

    private static void requireAnimatedFaceLayers(BakedModel model, ResourceLocation modelId, String context) {
        int emissiveFaces = 0;
        int ordinaryFaces = 0;
        int expectedTextureSize = modelId.getPath().equals("item/echo_pickaxe") ? 64 : modelId.getPath().matches("item/echo_pickaxe_v\\d{3}") ? 128 : 32;
        for (BakedQuad quad : model.getQuads(null, null, RandomSource.create())) {
            Direction face = quad.getDirection();
            if (face != Direction.NORTH && face != Direction.SOUTH) continue;
            boolean emissive = quad.getVertices()[IQuadTransformer.UV2] == 0x00F000F0;
            if (emissive) {
                emissiveFaces++;
                var contents = quad.getSprite().contents();
                if (contents.width() != expectedTextureSize || contents.height() != expectedTextureSize
                        || contents.getUniqueFrames().count() < 2) {
                    throw new IllegalStateException("Missing animated " + expectedTextureSize + "x" + expectedTextureSize
                            + " glow frames on " + modelId + " for " + context);
                }
            } else {
                ordinaryFaces++;
            }
        }
        if (emissiveFaces == 0 || ordinaryFaces == 0) {
            throw new IllegalStateException("Expected both lit glow and ordinary front faces on " + modelId
                    + " for " + context + "; glow=" + emissiveFaces + ", ordinary=" + ordinaryFaces);
        }
    }

    private static String describe(BakedModel model) {
        return model == null ? "null" : model.getClass().getName() + "@" + Integer.toHexString(System.identityHashCode(model));
    }
}
