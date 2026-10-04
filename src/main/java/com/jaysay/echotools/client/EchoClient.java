package com.jaysay.echotools.client;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.jaysay.echotools.EchoMod;
import com.jaysay.echotools.EchoNetwork;
import com.jaysay.echotools.EchoOreKind;
import com.jaysay.echotools.EchoPickaxeData;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.blaze3d.vertex.VertexFormat;
import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.Camera;
import net.minecraft.client.CameraType;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderStateShard;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.client.renderer.texture.TextureAtlas;
import net.minecraft.world.inventory.InventoryMenu;
import net.minecraft.client.renderer.block.model.BakedQuad;
import net.minecraftforge.client.model.IQuadTransformer;
import net.minecraft.client.gui.screens.inventory.CreativeModeInventoryScreen;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.client.gui.screens.advancements.AdvancementsScreen;
import net.minecraft.advancements.Advancement;
import net.minecraft.advancements.AdvancementProgress;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.HumanoidArm;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.util.RandomSource;
import org.lwjgl.opengl.GL11;
import org.lwjgl.glfw.GLFW;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.gui.components.Button;
import com.mojang.blaze3d.platform.InputConstants;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLEnvironment;
import net.minecraft.world.item.ItemStack;
import java.util.List;
import java.util.Map;
import java.lang.reflect.Field;
import java.util.concurrent.CompletableFuture;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;

@Mod.EventBusSubscriber(modid = EchoMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class EchoClient {
    private static final int DEFAULT_DISPLAY_TICKS = 140;
    private static final int PATH_CYAN = 0x2FE8E0;
    private static final int BONE_WHITE = 0xE9FFF9;

    private static BlockPos target;
    private static List<BlockPos> targets = List.of();
    private static int selectedTarget;
    private static ResourceLocation dimension;
    private static final KeyMapping CYCLE_TARGET = new KeyMapping("key.echopickaxe.cycle_target", InputConstants.KEY_V, "key.categories.echopickaxe");
    private static long receivedAtTick;
    private static int displayTicks = DEFAULT_DISPLAY_TICKS;
    private static int smokeStage;
    private static long smokeNextTick;
    private static boolean smokeStarted;
    private static int whiteItemSmokeStage;
    private static long whiteItemSmokeNextTick;
    private static boolean whiteItemSmokeStarted;
    private static int guidanceSmokeStage;
    private static long guidanceSmokeNextTick;
    private static long guidanceSmokeStartTick;
    private static boolean guidanceSmokeStarted;
    private static int rangeSmokeStage;
    private static long rangeSmokeNextTick;
    private static boolean rangeSmokeStarted;
    private static BlockPos rangeCenter;
    private static boolean rangeSmokePassed=true;
    private static int creativeTabSmokeStage;
    private static long creativeTabSmokeNextTick;
    private static boolean creativeTabSmokeStarted;
    private static int ancientDebrisSmokeStage;
    private static long ancientDebrisSmokeNextTick;
    private static boolean ancientDebrisSmokeStarted;
    private static BlockPos ancientDebrisCenter;
    private static boolean ancientDebrisSmokePassed=true;
    private static int progressSmokeStage;
    private static long progressSmokeNextTick;
    private static boolean progressSmokeStarted;
    private static boolean progressSmokePassed=true;
    private static int emissiveSmokeStage;
    private static long emissiveSmokeNextTick;
    private static boolean emissiveSmokeStarted;
    private static boolean visualVariantsChecked;
    private static int emissiveOriginalGuiScale = -1;
    private static CameraType emissiveOriginalCameraType;
    private static HumanoidArm emissiveOriginalMainArm;
    private static boolean emissiveThirdPersonComparison;
    private static java.lang.reflect.Method emissiveCameraPositionSetter;
    private static CompletableFuture<Void> emissiveReload;
    private static String emissivePendingScreenshot;
    private static long emissiveCaptureAt;

    private EchoClient() {}

    public static void receive(ResourceLocation nextDimension, List<BlockPos> nextTargets, int selected, boolean resetTimer, int durationTicks) {
        Minecraft mc = Minecraft.getInstance();
        if (nextTargets.isEmpty() || mc.level == null || mc.player == null
                || !mc.level.dimension().location().equals(nextDimension)
                || (durationTicks!=140 && durationTicks!=280 && durationTicks!=420 && durationTicks!=560)) { clear(); return; }
        targets = nextTargets.stream().limit(8).map(BlockPos::immutable).toList();
        selectedTarget = Math.max(0, Math.min(selected, targets.size()-1));
        target = targets.get(selectedTarget);
        if (Boolean.getBoolean("echopickaxe.visualSmoke") && !FMLEnvironment.production)
            System.out.println("[EchoSmoke] S2C targets="+targets+" selected="+(selectedTarget+1));
        dimension = nextDimension;
        if (resetTimer || receivedAtTick == 0) {
            receivedAtTick = mc.level.getGameTime();
            displayTicks = durationTicks;
        }
    }

    static KeyMapping targetKey() { return CYCLE_TARGET; }
    public static void openFilter(String current) { Minecraft.getInstance().setScreen(new EchoFilterScreen(current)); }

    private static void clear() {
        target = null;
        targets = List.of();
        selectedTarget = 0;
        dimension = null;
        displayTicks = DEFAULT_DISPLAY_TICKS;
    }

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null) {
            clear();
            return;
        }
        if (target != null && (!mc.level.dimension().location().equals(dimension)
                || mc.level.getGameTime() - receivedAtTick >= displayTicks)) clear();
        while (CYCLE_TARGET.consumeClick()) if (mc.screen == null && target != null) EchoNetwork.cycleTarget();
        tickVisualSmoke(mc);
    }

    private static void tickVisualSmoke(Minecraft mc) {
        if (FMLEnvironment.production || mc.level == null || mc.player == null || mc.gameMode == null) return;
        boolean visualSmoke=Boolean.getBoolean("echopickaxe.visualSmoke");
        boolean itemSmoke=Boolean.getBoolean("echopickaxe.visualItemSmoke");
        if (Boolean.getBoolean("echopickaxe.emissiveSmoke")) { tickEmissiveSmoke(mc); return; }
        if (Boolean.getBoolean("echopickaxe.ancientDebrisSmoke")) { tickAncientDebrisSmoke(mc); return; }
        if (Boolean.getBoolean("echopickaxe.creativeTabSmoke")) { tickCreativeTabSmoke(mc); return; }
        if (Boolean.getBoolean("echopickaxe.guidanceSmoke")) { tickGuidanceSmoke(mc); return; }
        if (Boolean.getBoolean("echopickaxe.progressSmoke")) { tickProgressSmoke(mc); return; }
        if (Boolean.getBoolean("echopickaxe.rangeSmoke")) { tickRangeSmoke(mc); return; }
        if (visualSmoke && smokeStage!=7) { tickGuideSmoke(mc); return; }
        if (itemSmoke) { tickWhiteItemSmoke(mc); return; }
        return;
    }

    private static void tickCreativeTabSmoke(Minecraft mc) {
        long now=mc.level.getGameTime();
        if(!creativeTabSmokeStarted) { creativeTabSmokeStarted=true; creativeTabSmokeNextTick=now+80; return; }
        if(now<creativeTabSmokeNextTick) return;
        if(creativeTabSmokeStage==0) {
            mc.player.connection.sendCommand("echo verify");
            var tab=EchoMod.ECHO_TOOLS_TAB.get();
            tab.buildContents(new CreativeModeTab.ItemDisplayParameters(mc.level.enabledFeatures(),mc.player.hasPermissions(2),mc.level.registryAccess()));
            var items=tab.getDisplayItems().stream().map(stack->BuiltInRegistries.ITEM.getKey(stack.getItem()).toString()).toList();
            var tools=BuiltInRegistries.CREATIVE_MODE_TAB.get(CreativeModeTabs.TOOLS_AND_UTILITIES.location());
            var ingredients=BuiltInRegistries.CREATIVE_MODE_TAB.get(CreativeModeTabs.INGREDIENTS.location());
            boolean cleanOldTabs=tools.getDisplayItems().stream().noneMatch(s->BuiltInRegistries.ITEM.getKey(s.getItem()).getNamespace().equals(EchoMod.MOD_ID))
                    && ingredients.getDisplayItems().stream().noneMatch(s->BuiltInRegistries.ITEM.getKey(s.getItem()).getNamespace().equals(EchoMod.MOD_ID));
            System.out.println("[EchoCreativeSmoke] tabTitle="+tab.getDisplayName().getString()+" itemCount="+items.size()+" items="+items+" oldVanillaTabsClean="+cleanOldTabs);
            var screen=new CreativeModeInventoryScreen(mc.player,mc.level.enabledFeatures(),mc.player.hasPermissions(2));
            mc.setScreen(screen);
            boolean paged=screen.mouseClicked(mc.getWindow().getGuiScaledWidth()/2.0+132,18,0);
            System.out.println("[EchoCreativeSmoke] clicked next tab page="+paged+" page="+screen.getCurrentPage());
            creativeTabSmokeStage=1; creativeTabSmokeNextTick=now+5;
        } else if(creativeTabSmokeStage==1) {
            var screen=(CreativeModeInventoryScreen)mc.screen;
            try {
                var pagesField=CreativeModeInventoryScreen.class.getDeclaredField("pages");
                pagesField.setAccessible(true);
                var pages=(List<?>)pagesField.get(screen);
                var targetPage=pages.stream().map(net.minecraftforge.client.gui.CreativeTabsScreenPage.class::cast)
                        .filter(page->page.getVisibleTabs().contains(EchoMod.ECHO_TOOLS_TAB.get())).findFirst().orElseThrow();
                screen.setCurrentPage(targetPage);
                var selector=CreativeModeInventoryScreen.class.getDeclaredMethod("selectTab",CreativeModeTab.class);
                selector.setAccessible(true);
                selector.invoke(screen,EchoMod.ECHO_TOOLS_TAB.get());
                boolean visible=screen.getCurrentPage().getVisibleTabs().contains(EchoMod.ECHO_TOOLS_TAB.get());
                System.out.println("[EchoCreativeSmoke] page count="+pages.size()+" modTabVisible="+visible);
            } catch(Exception e) { System.out.println("[EchoCreativeSmoke] FAIL selecting tab: "+e); }
            creativeTabSmokeStage=2; creativeTabSmokeNextTick=now+40;
        } else if(creativeTabSmokeStage==2) {
            saveSmokeScreenshot(mc,"echo-tools-creative-tab.png");
            creativeTabSmokeStage=3; creativeTabSmokeNextTick=now+10;
        } else {
            System.out.println("[EchoCreativeSmoke] Completed; closing isolated client."); mc.stop();
        }
    }

    private static void tickGuidanceSmoke(Minecraft mc) {
        long now=mc.level.getGameTime();
        if (!guidanceSmokeStarted) { guidanceSmokeStarted=true; guidanceSmokeNextTick=now+80; return; }
        if (now<guidanceSmokeNextTick) return;
        mc.options.keyAttack.setDown(false); mc.options.keyUse.setDown(false);
        switch (guidanceSmokeStage) {
            case 0 -> {
                if (!mc.player.hasPermissions(2)) {
                    System.out.println("[EchoDurationSmoke] FAIL: isolated quick-play world lacks permission 2."); guidanceSmokeStage=9; return;
                }
                mc.player.connection.sendCommand("item replace entity @s hotbar.0 with echopickaxe:echo_pickaxe");
                mc.player.getInventory().selected=0;
                guidanceSmokeStage=1; guidanceSmokeNextTick=now+20;
            }
            case 1 -> {
                mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND);
                guidanceSmokeStage=2; guidanceSmokeNextTick=now+10;
            }
            case 2 -> {
                if (target==null || displayTicks!=140) {
                    System.out.println("[EchoDurationSmoke] FAIL: frequency-0 scan did not receive a 140-tick target session."); guidanceSmokeStage=9; return;
                }
                guidanceSmokeStartTick=receivedAtTick;
                System.out.println("[EchoDurationSmoke] frequency-0 session started @"+guidanceSmokeStartTick+" duration="+displayTicks+".");
                guidanceSmokeStage=3; guidanceSmokeNextTick=now+120;
            }
            case 3 -> {
                if (target==null || receivedAtTick!=guidanceSmokeStartTick) {
                    System.out.println("[EchoDurationSmoke] FAIL: frequency-0 target expired early or timer reset before cycle."); guidanceSmokeStage=9; return;
                }
                EchoNetwork.cycleTarget();
                guidanceSmokeStage=4; guidanceSmokeNextTick=now+15;
            }
            case 4 -> {
                long age=now-guidanceSmokeStartTick;
                if (target!=null || age<140 || age>155) {
                    System.out.println("[EchoDurationSmoke] FAIL: frequency-0 expiry age="+age+" targetActive="+(target!=null)); guidanceSmokeStage=9; return;
                }
                System.out.println("[EchoDurationSmoke] PASS: 140-tick base duration expired at age="+age+"; cycle did not extend it.");
                mc.player.connection.sendCommand("item replace entity @s hotbar.0 with echopickaxe:echo_pickaxe{EchoUpgrades:{frequency:3}}");
                guidanceSmokeStage=5; guidanceSmokeNextTick=now+20;
            }
            case 5 -> {
                mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND);
                guidanceSmokeStage=6; guidanceSmokeNextTick=now+10;
            }
            case 6 -> {
                if (target==null || displayTicks!=560) {
                    System.out.println("[EchoDurationSmoke] FAIL: frequency-III scan did not receive a 560-tick target session."); guidanceSmokeStage=9; return;
                }
                guidanceSmokeStartTick=receivedAtTick;
                EchoNetwork.cycleTarget();
                System.out.println("[EchoDurationSmoke] frequency-III session started @"+guidanceSmokeStartTick+" duration="+displayTicks+"; cycled target.");
                guidanceSmokeStage=7; guidanceSmokeNextTick=now+540;
            }
            case 7 -> {
                long age=now-guidanceSmokeStartTick;
                if (target==null || receivedAtTick!=guidanceSmokeStartTick || age<535 || age>=560) {
                    System.out.println("[EchoDurationSmoke] FAIL: frequency-III target/timer invalid before deadline, age="+age); guidanceSmokeStage=9; return;
                }
                System.out.println("[EchoDurationSmoke] PASS: target still active at age="+age+" after cycle; timer unchanged.");
                guidanceSmokeStage=8; guidanceSmokeNextTick=now+20;
            }
            case 8 -> {
                long age=now-guidanceSmokeStartTick;
                boolean passed=target==null && age>=560 && age<=580;
                System.out.println("[EchoDurationSmoke] "+(passed?"PASS":"FAIL")+": frequency-III 560-tick expiry age="+age+" targetActive="+(target!=null)+".");
                guidanceSmokeStage=9; guidanceSmokeNextTick=now+40;
            }
            case 9 -> { System.out.println("[EchoDurationSmoke] Completed; closing isolated development client."); guidanceSmokeStage=10; mc.stop(); }
            default -> { }
        }
    }

    private static void tickProgressSmoke(Minecraft mc) {
        long now=mc.level.getGameTime();
        if(!progressSmokeStarted) { progressSmokeStarted=true; progressSmokeNextTick=now+80; return; }
        if(now<progressSmokeNextTick) return;
        if(progressSmokeStage==0) {
            if(!mc.player.hasPermissions(2)) { System.out.println("[EchoProgressSmoke] FAIL: isolated world lacks permission 2."); mc.stop(); return; }
            mc.player.connection.sendCommand("echo verify");
            mc.player.connection.sendCommand("clear @s echopickaxe:echo_pickaxe");
            mc.player.connection.sendCommand("give @s echopickaxe:echo_pickaxe");
            progressSmokeStage=1; progressSmokeNextTick=now+50;
        } else if(progressSmokeStage==1) {
            boolean first=advancementDone(mc,"first_echo");
            System.out.println("[EchoProgressSmoke] inventory_changed for plain Echo Pickaxe completed first_echo="+first);
            progressSmokePassed &= first;
            mc.player.connection.sendCommand("clear @s echopickaxe:echo_pickaxe");
            mc.player.connection.sendCommand("give @s echopickaxe:echo_pickaxe{EchoUpgrades:{resonance:1}}");
            progressSmokeStage=2; progressSmokeNextTick=now+50;
        } else if(progressSmokeStage==2) {
            boolean firstUpgrade=advancementDone(mc,"first_upgrade");
            boolean challenge=advancementDone(mc,"all_echoes");
            System.out.println("[EchoProgressSmoke] any upgraded pickaxe completed first_upgrade="+firstUpgrade+" challengePremature="+challenge);
            progressSmokePassed &= firstUpgrade && !challenge;
            mc.player.connection.sendCommand("clear @s echopickaxe:echo_pickaxe");
            mc.player.connection.sendCommand("give @s echopickaxe:echo_pickaxe{EchoUpgrades:{resonance:2}}");
            mc.player.connection.sendCommand("give @s echopickaxe:echo_pickaxe{EchoUpgrades:{frequency:3}}");
            mc.player.connection.sendCommand("give @s echopickaxe:echo_pickaxe{EchoUpgrades:{tuning:1}}");
            mc.player.connection.sendCommand("give @s echopickaxe:echo_pickaxe{EchoUpgrades:{extension:3}}");
            mc.player.connection.sendCommand("give @s echopickaxe:echo_pickaxe{EchoUpgrades:{resonance:1,frequency:3,tuning:1,extension:3}}");
            progressSmokeStage=3; progressSmokeNextTick=now+60;
        } else if(progressSmokeStage==3) {
            boolean firstUpgrade=advancementDone(mc,"first_upgrade");
            boolean challenge=advancementDone(mc,"all_echoes");
            System.out.println("[EchoProgressSmoke] separate single-attribute tools + one near-full tool first_upgrade="+firstUpgrade+" all_echoesPremature="+challenge);
            progressSmokePassed &= firstUpgrade && !challenge;
            mc.player.connection.sendCommand("clear @s echopickaxe:echo_pickaxe");
            mc.player.connection.sendCommand("give @s echopickaxe:echo_pickaxe{EchoUpgrades:{resonance:2,frequency:3,tuning:1,extension:3}}");
            progressSmokeStage=4; progressSmokeNextTick=now+60;
        } else if(progressSmokeStage==4) {
            boolean full=advancementDone(mc,"all_echoes");
            System.out.println("[EchoProgressSmoke] same fully upgraded item completed challenge="+full);
            progressSmokePassed &= full;
            var clientAdvancements=mc.player.connection.getAdvancements();
            Advancement root=clientAdvancements.getAdvancements().get(new ResourceLocation(EchoMod.MOD_ID,"first_echo"));
            mc.setScreen(new AdvancementsScreen(clientAdvancements));
            clientAdvancements.setSelectedTab(root,true);
            progressSmokeStage=5; progressSmokeNextTick=now;
        } else if(progressSmokeStage==5) {
            saveSmokeScreenshot(mc,"echo-advancement-all-echoes.png");
            System.out.println("[EchoProgressSmoke] "+(progressSmokePassed?"PASS":"FAIL")+"; screenshot shows the completed native advancement chain.");
            mc.stop();
        }
    }

    private static boolean advancementDone(Minecraft mc,String path) {
        try {
            var client=mc.player.connection.getAdvancements();
            Advancement advancement=client.getAdvancements().get(new ResourceLocation(EchoMod.MOD_ID,path));
            if(advancement==null) throw new IllegalStateException("advancement not loaded: "+path);
            Field field=client.getClass().getDeclaredField("progress"); field.setAccessible(true);
            @SuppressWarnings("unchecked") Map<Advancement,AdvancementProgress> progress=(Map<Advancement,AdvancementProgress>)field.get(client);
            AdvancementProgress state=progress.get(advancement);
            return state!=null && state.isDone();
        } catch(ReflectiveOperationException error) { throw new IllegalStateException("cannot read client advancement state",error); }
    }

    private static void tickAncientDebrisSmoke(Minecraft mc) {
        long now=mc.level.getGameTime();
        if(!ancientDebrisSmokeStarted) { ancientDebrisSmokeStarted=true; ancientDebrisSmokeNextTick=now+80; return; }
        if(now<ancientDebrisSmokeNextTick) return;
        mc.options.keyAttack.setDown(false); mc.options.keyUse.setDown(false);
        switch(ancientDebrisSmokeStage) {
            case 0 -> {
                if(!mc.player.hasPermissions(2)) { System.out.println("[EchoAncientDebrisSmoke] FAIL: isolated world lacks permission 2."); mc.stop(); return; }
                mc.player.connection.sendCommand("tp @s 300 200 300 -90 0");
                ancientDebrisSmokeStage=1; ancientDebrisSmokeNextTick=now+60;
            }
            case 1 -> {
                ancientDebrisCenter=new BlockPos(300,200,300);
                int cx=300,cy=200,cz=300;
                mc.player.connection.sendCommand("fill 290 199 290 310 199 310 minecraft:polished_deepslate");
                mc.player.connection.sendCommand("fill 297 200 297 303 204 303 minecraft:air");
                mc.player.connection.sendCommand("setblock 304 200 300 minecraft:ancient_debris");
                mc.player.connection.sendCommand("setblock 305 200 300 minecraft:ancient_debris");
                mc.player.connection.sendCommand("setblock 309 200 300 minecraft:nether_quartz_ore");
                mc.player.connection.sendCommand("setblock 300 200 309 minecraft:nether_gold_ore");
                mc.player.connection.sendCommand("item replace entity @s hotbar.0 with echopickaxe:echo_pickaxe{EchoUpgrades:{resonance:2,frequency:3,extension:3,tuning:1}}");
                mc.player.getInventory().selected=0;
                mc.player.connection.sendCommand("tp @s "+cx+" "+cy+" "+cz+" -90 0");
                ancientDebrisSmokeStage=2; ancientDebrisSmokeNextTick=now+50;
            }
            case 2 -> {
                mc.options.keyShift.setDown(true); ancientDebrisSmokeStage=3; ancientDebrisSmokeNextTick=now+5;
            }
            case 3 -> {
                mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND); mc.options.keyShift.setDown(false);
                ancientDebrisSmokeStage=4; ancientDebrisSmokeNextTick=now+30;
            }
            case 4 -> {
                boolean open=mc.screen instanceof EchoFilterScreen;
                boolean clicked=open && clickFilterOption(mc,"远古残骸","Ancient debris");
                System.out.println("[EchoAncientDebrisSmoke] filter screen opened="+open+" ancient-debris button clicked="+clicked);
                ancientDebrisSmokePassed &= open && clicked;
                ancientDebrisSmokeStage=5; ancientDebrisSmokeNextTick=now+30;
            }
            case 5 -> {
                String filter=EchoPickaxeData.filter(mc.player.getMainHandItem());
                boolean accepted=filter.equals(EchoOreKind.ANCIENT_DEBRIS.id());
                System.out.println("[EchoAncientDebrisSmoke] server filter synchronized to client="+filter+" PASS="+accepted);
                ancientDebrisSmokePassed &= accepted;
                mc.options.keyShift.setDown(true); ancientDebrisSmokeStage=6; ancientDebrisSmokeNextTick=now+5;
            }
            case 6 -> {
                mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND); mc.options.keyShift.setDown(false);
                ancientDebrisSmokeStage=7; ancientDebrisSmokeNextTick=now+30;
            }
            case 7 -> {
                boolean reopened=mc.screen instanceof EchoFilterScreen;
                boolean selected=reopened && ((EchoFilterScreen)mc.screen).children().stream().filter(Button.class::isInstance)
                        .map(Button.class::cast).anyMatch(b->b.getMessage().getString().contains("✓")
                                && (b.getMessage().getString().contains("远古残骸") || b.getMessage().getString().contains("Ancient debris")));
                System.out.println("[EchoAncientDebrisSmoke] reopened filter marks ancient debris selected="+selected);
                ancientDebrisSmokePassed &= reopened && selected;
                saveSmokeScreenshot(mc,"echo-filter-ancient-debris.png");
                mc.setScreen(null); mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND);
                ancientDebrisSmokeStage=8; ancientDebrisSmokeNextTick=now+60;
            }
            case 8 -> {
                boolean filtered=targets.size()==1 && (targets.get(0).getX()==304 || targets.get(0).getX()==305);
                System.out.println("[EchoAncientDebrisSmoke] ancient filter scan="+targets+" PASS="+filtered);
                ancientDebrisSmokePassed &= filtered;
                mc.options.keyShift.setDown(true); ancientDebrisSmokeStage=9; ancientDebrisSmokeNextTick=now+5;
            }
            case 9 -> {
                mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND); mc.options.keyShift.setDown(false);
                ancientDebrisSmokeStage=10; ancientDebrisSmokeNextTick=now+30;
            }
            case 10 -> {
                boolean clicked=mc.screen instanceof EchoFilterScreen && clickFilterOption(mc,"全部矿石","All ores");
                ancientDebrisSmokePassed &= clicked;
                ancientDebrisSmokeStage=11; ancientDebrisSmokeNextTick=now+30;
            }
            case 11 -> {
                String filter=EchoPickaxeData.filter(mc.player.getMainHandItem());
                boolean all=filter.equals(EchoOreKind.ALL.id());
                System.out.println("[EchoAncientDebrisSmoke] all-ores filter synchronized="+filter+" PASS="+all);
                ancientDebrisSmokePassed &= all;
                mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND);
                ancientDebrisSmokeStage=12; ancientDebrisSmokeNextTick=now+60;
            }
            case 12 -> {
                boolean allFound=targets.size()==3 && targets.contains(ancientDebrisCenter.offset(4,0,0));
                System.out.println("[EchoAncientDebrisSmoke] all-filter scan targets="+targets+" PASS="+allFound+" (debris pair is one vein)");
                ancientDebrisSmokePassed &= allFound;
                System.out.println("[EchoAncientDebrisSmoke] "+(ancientDebrisSmokePassed?"PASS":"FAIL")+"; completed in isolated copy.");
                mc.stop();
            }
            default -> { }
        }
    }

    private static boolean clickFilterOption(Minecraft mc,String firstLabel,String secondLabel) {
        if(!(mc.screen instanceof EchoFilterScreen screen)) return false;
        Button button=screen.children().stream().filter(Button.class::isInstance).map(Button.class::cast)
                .filter(b->b.getMessage().getString().contains(firstLabel)||b.getMessage().getString().contains(secondLabel))
                .findFirst().orElse(null);
        if(button==null) return false;
        double x=button.getX()+button.getWidth()/2.0, y=button.getY()+button.getHeight()/2.0;
        screen.mouseClicked(x,y,0); screen.mouseReleased(x,y,0);
        return true;
    }

    private static void tickRangeSmoke(Minecraft mc) {
        long now=mc.level.getGameTime();
        if (!rangeSmokeStarted) { rangeSmokeStarted=true; rangeSmokeNextTick=now+80; return; }
        if (now<rangeSmokeNextTick) return;
        mc.options.keyAttack.setDown(false); mc.options.keyUse.setDown(false);
        switch(rangeSmokeStage) {
            case 0 -> {
                if(!mc.player.hasPermissions(2)) { System.out.println("[EchoRangeSmoke] FAIL: isolated world lacks permission 2."); rangeSmokeStage=30; return; }
                mc.player.connection.sendCommand("gamerule doDaylightCycle false");
                mc.player.connection.sendCommand("gamerule doWeatherCycle false");
                mc.player.connection.sendCommand("time set day");
                // Load the test area first, then let the player settle before issuing fills.
                mc.player.connection.sendCommand("tp @s 300 300 300 -90 0");
                rangeSmokePassed=true;
                rangeSmokeStage=18; rangeSmokeNextTick=now+160;
            }
            case 18 -> {
                rangeCenter=new BlockPos(300,200,300);
                int cx=rangeCenter.getX(),cy=rangeCenter.getY(),cz=rangeCenter.getZ();
                for(int y=cy-30;y<=cy+30;y+=8) {
                    int end=Math.min(cy+30,y+7);
                    mc.player.connection.sendCommand("fill "+(cx-30)+" "+y+" "+(cz-30)+" "+(cx+30)+" "+end+" "+(cz+30)+" minecraft:stone");
                }
                mc.player.connection.sendCommand("fill "+(cx-1)+" "+cy+" "+(cz-1)+" "+(cx+1)+" "+(cy+2)+" "+(cz+1)+" minecraft:air");
                prepareRangeTier(mc,0);
                mc.player.connection.sendCommand("tp @s "+cx+" "+cy+" "+cz+" -90 0");
                rangeSmokeStage=1; rangeSmokeNextTick=now+80;
            }
            case 1 -> {
                mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND);
                rangeSmokeStage=2; rangeSmokeNextTick=now+60;
            }
            case 2 -> {
                boolean ok=expectRangeTarget(1,10,0,0);
                rangeSmokePassed &= ok;
                System.out.println("[EchoRangeSmoke] "+(ok?"PASS":"FAIL")+": base range 12 included x=10 and excluded x=13,z=2; targets="+targets);
                prepareRangeTier(mc,1);
                rangeSmokeStage=3; rangeSmokeNextTick=now+50;
            }
            case 3 -> { mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND); rangeSmokeStage=4; rangeSmokeNextTick=now+60; }
            case 4 -> {
                boolean ok=expectRangeTarget(1,17,0,4);
                rangeSmokePassed &= ok;
                System.out.println("[EchoRangeSmoke] "+(ok?"PASS":"FAIL")+": extension I range 18 included distance 17.46 and excluded distance 19; targets="+targets);
                prepareRangeTier(mc,2); rangeSmokeStage=5; rangeSmokeNextTick=now+50;
            }
            case 5 -> { mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND); rangeSmokeStage=6; rangeSmokeNextTick=now+60; }
            case 6 -> {
                boolean ok=expectRangeTarget(1,23,0,0);
                rangeSmokePassed &= ok;
                System.out.println("[EchoRangeSmoke] "+(ok?"PASS":"FAIL")+": extension II range 24 included distance 23 and excluded distance 25; targets="+targets);
                prepareRangeTier(mc,3); rangeSmokeStage=7; rangeSmokeNextTick=now+50;
            }
            case 7 -> { mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND); rangeSmokeStage=8; rangeSmokeNextTick=now+60; }
            case 8 -> {
                boolean ok=expectRangeTarget(1,18,0,24);
                rangeSmokePassed &= ok;
                System.out.println("[EchoRangeSmoke] "+(ok?"PASS":"FAIL")+": extension III range 30 included sphere boundary (18,24) and excluded corner (22,22); targets="+targets);
                rangeSmokeStage=9; rangeSmokeNextTick=now+50;
            }
            case 9 -> { mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND); rangeSmokeStage=10; rangeSmokeNextTick=now+60; }
            case 10 -> { System.out.println("[EchoRangeSmoke] warm scan complete; repeating max-radius scan."); mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND); rangeSmokeStage=11; rangeSmokeNextTick=now+20; }
            case 11 -> { mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND); rangeSmokeStage=12; rangeSmokeNextTick=now+10; }
            case 12 -> {
                mc.player.connection.sendCommand("echo verify");
                rangeSmokeStage=13; rangeSmokeNextTick=now+40;
            }
            case 13 -> {
                int cx=rangeCenter.getX(),cy=rangeCenter.getY(),cz=rangeCenter.getZ();
                int[][] allPoints={{10,0,13,2},{17,4,19,0},{23,0,25,0},{18,24,22,22}};
                for(int[] p:allPoints) for(int i=0;i<4;i+=2)
                    mc.player.connection.sendCommand("setblock "+(cx+p[i])+" "+cy+" "+(cz+p[i+1])+" minecraft:stone");
                mc.player.connection.sendCommand("fill "+(cx+1)+" "+(cy-2)+" "+(cz-4)+" "+(cx+2)+" "+(cy+5)+" "+(cz+4)+" minecraft:air");
                mc.player.connection.sendCommand("time set day");
                mc.player.connection.sendCommand("weather clear 1000000");
                mc.player.connection.sendCommand("effect give @s minecraft:night_vision 99999 0 true");
                mc.player.connection.sendCommand("fill "+(cx-3)+" "+(cy-1)+" "+(cz-3)+" "+(cx+3)+" "+(cy-1)+" "+(cz+3)+" minecraft:snow_block");
                mc.player.connection.sendCommand("fill "+(cx+3)+" "+(cy-2)+" "+(cz-4)+" "+(cx+3)+" "+(cy+5)+" "+(cz+4)+" minecraft:snow_block");
                mc.player.connection.sendCommand("tp @s "+cx+" "+cy+" "+cz+" -90 0");
                mc.player.connection.sendCommand("item replace entity @s hotbar.1 with echopickaxe:extension_crystal");
                mc.player.connection.sendCommand("item replace entity @s hotbar.2 with echopickaxe:enhanced_extension_crystal");
                mc.player.connection.sendCommand("item replace entity @s hotbar.3 with echopickaxe:enhanced_extension_crystal_2");
                mc.options.mainHand().set(HumanoidArm.RIGHT); mc.player.getInventory().selected=1;
                rangeSmokeStage=14; rangeSmokeNextTick=now+60;
            }
            case 14 -> { saveSmokeScreenshot(mc,"echo-white-extension-crystal.png"); mc.player.getInventory().selected=2; rangeSmokeStage=15; rangeSmokeNextTick=now+40; }
            case 15 -> { saveSmokeScreenshot(mc,"echo-white-enhanced-extension-crystal.png"); mc.player.getInventory().selected=3; rangeSmokeStage=16; rangeSmokeNextTick=now+40; }
            case 16 -> {
                saveSmokeScreenshot(mc,"echo-white-enhanced-extension-crystal-2.png");
                System.out.println("[EchoRangeSmoke] "+(rangeSmokePassed?"PASS":"FAIL")+": all four radius boundaries; captured extension crystals against snow. Scan logs above include dense-stone max-radius scanMillis.");
                rangeSmokeStage=17; rangeSmokeNextTick=now+40;
            }
            case 17 -> { System.out.println("[EchoRangeSmoke] Completed; closing isolated client."); rangeSmokeStage=30; mc.stop(); }
            default -> { }
        }
    }

    private static void prepareRangeTier(Minecraft mc,int rank) {
        int[][] points={{10,0,13,2},{17,4,19,0},{23,0,25,0},{18,24,22,22}};
        String[][] ores={{"diamond_ore","iron_ore"},{"gold_ore","redstone_ore"},{"emerald_ore","lapis_ore"},{"nether_quartz_ore","nether_gold_ore"}};
        int previous=rank-1;
        if(previous>=0) {
            mc.player.connection.sendCommand("setblock "+(rangeCenter.getX()+points[previous][0])+" "+rangeCenter.getY()+" "+(rangeCenter.getZ()+points[previous][1])+" minecraft:stone");
            mc.player.connection.sendCommand("setblock "+(rangeCenter.getX()+points[previous][2])+" "+rangeCenter.getY()+" "+(rangeCenter.getZ()+points[previous][3])+" minecraft:stone");
        }
        mc.player.connection.sendCommand("setblock "+(rangeCenter.getX()+points[rank][0])+" "+rangeCenter.getY()+" "+(rangeCenter.getZ()+points[rank][1])+" minecraft:"+ores[rank][0]);
        mc.player.connection.sendCommand("setblock "+(rangeCenter.getX()+points[rank][2])+" "+rangeCenter.getY()+" "+(rangeCenter.getZ()+points[rank][3])+" minecraft:"+ores[rank][1]);
        mc.player.connection.sendCommand("item replace entity @s hotbar.0 with echopickaxe:echo_pickaxe{EchoUpgrades:{resonance:2,frequency:3,extension:"+rank+"}}");
        mc.player.getInventory().selected=0;
    }

    private static boolean expectRangeTarget(int count,int dx,int dy,int dz) {
        return rangeCenter!=null && targets.size()==count
                && targets.get(0).equals(rangeCenter.offset(dx,dy,dz));
    }

    private static void tickGuideSmoke(Minecraft mc) {
        long now = mc.level.getGameTime();
        if (!smokeStarted) {
            smokeStarted = true;
            smokeNextTick = now + 80;
            return;
        }
        if (smokeStage == 0 && now >= smokeNextTick) {
            if (!mc.player.hasPermissions(2)) {
                System.out.println("[EchoSmoke] Abort: quick-play world does not grant command permission 2.");
                smokeStage = 7;
                return;
            }
            mc.player.connection.sendCommand("time set day");
            mc.player.connection.sendCommand("gamerule doDaylightCycle false");
            mc.player.connection.sendCommand("weather clear 1000000");
            mc.player.connection.sendCommand("gamerule doWeatherCycle false");
            mc.player.connection.sendCommand("echo demo confirm");
            smokeStage = 1;
            smokeNextTick = now + 50;
            return;
        }
        if (now < smokeNextTick) return;
        switch (smokeStage) {
            case 1 -> {
                String[] ores={
                        "setblock ~1 ~-1 ~3 minecraft:coal_ore","setblock ~2 ~-1 ~3 minecraft:deepslate_coal_ore",
                        "setblock ~1 ~-1 ~-3 minecraft:copper_ore","setblock ~-1 ~-1 ~3 minecraft:iron_ore",
                        "setblock ~-1 ~-1 ~-3 minecraft:redstone_ore","setblock ~3 ~-1 ~3 minecraft:lapis_ore",
                        "setblock ~-3 ~-1 ~3 minecraft:emerald_ore","setblock ~3 ~-1 ~-3 minecraft:nether_quartz_ore",
                        "setblock ~-3 ~-1 ~-3 minecraft:nether_gold_ore"};
                for(String command:ores) mc.player.connection.sendCommand(command);
                mc.player.connection.sendCommand("item replace entity @s hotbar.0 with echopickaxe:echo_pickaxe{EchoUpgrades:{resonance:2,frequency:3,tuning:1}}");
                mc.player.getInventory().selected = 0;
                smokeStage = 2;
                smokeNextTick = now + 8;
            }
            case 2 -> {
                selectPickaxe(mc);
                mc.gameMode.useItem(mc.player, InteractionHand.MAIN_HAND);
                smokeStage = 3;
                smokeNextTick = now + 14;
            }
            case 3 -> {
                saveSmokeScreenshot(mc, "echo-guide-through-wall.png");
                boolean cooling=mc.player.getCooldowns().isOnCooldown(EchoMod.ECHO_PICKAXE.get());
                System.out.println("[EchoSmoke] resonance-II cooldown at tick ~14/20: "+(cooling?"PASS":"FAIL"));
                EchoNetwork.cycleTarget();
                smokeStage = 10;
                smokeNextTick = now + 8;
            }
            case 10 -> {
                saveSmokeScreenshot(mc,"echo-guide-cycle.png");
                boolean cooling=mc.player.getCooldowns().isOnCooldown(EchoMod.ECHO_PICKAXE.get());
                System.out.println("[EchoSmoke] resonance-II cooldown after >20 ticks: "+(!cooling?"PASS":"FAIL"));
                if(target!=null) {
                    for(int dx=-1;dx<=1;dx++) for(int dy=-1;dy<=1;dy++) for(int dz=-1;dz<=1;dz++)
                        mc.player.connection.sendCommand("setblock "+(target.getX()+dx)+" "+(target.getY()+dy)+" "+(target.getZ()+dz)+" minecraft:air");
                    System.out.println("[EchoSmoke] Removed the selected test ore block and its adjacent test cluster in the isolated copy.");
                }
                smokeStage = 13;
                smokeNextTick = now + 16;
            }
            case 13 -> {
                saveSmokeScreenshot(mc,"echo-guide-next-after-mining.png");
                mc.player.connection.sendCommand("echo verify");
                smokeStage = 4;
                smokeNextTick = now + 40;
            }
            case 4 -> {
                mc.options.keyShift.setDown(true);
                smokeStage = 8;
                smokeNextTick = now + 5;
            }
            case 8 -> {
                mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND);
                mc.options.keyShift.setDown(false);
                smokeStage = 9;
                smokeNextTick = now + 10;
            }
            case 9 -> {
                saveSmokeScreenshot(mc,"echo-filter-screen.png");
                EchoNetwork.sendFilter("diamond",InteractionHand.MAIN_HAND);
                smokeStage = 11;
                smokeNextTick = now + 8;
            }
            case 11 -> {
                mc.setScreen(null);
                mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND);
                smokeStage = 12;
                smokeNextTick = now + 14;
            }
            case 12 -> {
                saveSmokeScreenshot(mc,"echo-filtered-scan.png");
                mc.player.connection.sendCommand("tp @s ~-2.75 ~ ~ 90 0");
                smokeStage = 5;
                smokeNextTick = now + 108;
            }
            case 5 -> {
                selectPickaxe(mc);
                mc.gameMode.useItem(mc.player, InteractionHand.MAIN_HAND);
                smokeStage = 6;
                smokeNextTick = now + 14;
            }
            case 6 -> {
                saveSmokeScreenshot(mc, "echo-guide-line-of-sight.png");
                mc.player.displayClientMessage(net.minecraft.network.chat.Component.literal(
                        "[EchoSmoke] Screenshots saved: through-wall and line-of-sight"), false);
                System.out.println("[EchoSmoke] Completed; inspect run/screenshots/echo-guide-*.png");
                smokeStage = 7;
            }
            default -> { }
        }
    }

    private static void tickWhiteItemSmoke(Minecraft mc) {
        if (FMLEnvironment.production || !Boolean.getBoolean("echopickaxe.visualItemSmoke")) return;
        long now=mc.level.getGameTime();
        if (!whiteItemSmokeStarted) { whiteItemSmokeStarted=true; whiteItemSmokeNextTick=now+80; return; }
        if(now<whiteItemSmokeNextTick) return;
        mc.options.keyAttack.setDown(false); mc.options.keyUse.setDown(false);
        switch(whiteItemSmokeStage) {
            case 0 -> {
                if(!mc.player.hasPermissions(2)) { System.out.println("[EchoCrystalSmoke] Abort: test world lacks command permission 2."); whiteItemSmokeStage=8; return; }
                mc.player.connection.sendCommand("time set day");
                mc.player.connection.sendCommand("gamerule doDaylightCycle false");
                mc.player.connection.sendCommand("weather clear 1000000");
                mc.player.connection.sendCommand("gamerule doWeatherCycle false");
                mc.player.connection.sendCommand("fill ~1 ~-30 ~-25 ~7 ~20 ~25 air");
                mc.player.connection.sendCommand("fill ~8 ~-30 ~-25 ~8 ~20 ~25 minecraft:snow_block");
                mc.player.connection.sendCommand("fill ~-20 ~-1 ~-20 ~20 ~-1 ~20 minecraft:snow_block");
                mc.player.connection.sendCommand("item replace entity @s hotbar.0 with echopickaxe:echo_pickaxe");
                String[] ids={"resonance_crystal","enhanced_resonance_crystal","frequency_crystal","enhanced_frequency_crystal","enhanced_frequency_crystal_2","tuning_crystal"};
                for(int i=0;i<ids.length;i++) mc.player.connection.sendCommand("item replace entity @s hotbar."+(i+1)+" with echopickaxe:"+ids[i]);
                mc.player.connection.sendCommand("tp @s ~ ~ ~ -90 0");
                whiteItemSmokeStage=1; whiteItemSmokeNextTick=now+220;
            }
            case 1 -> { mc.options.mainHand().set(HumanoidArm.RIGHT); mc.player.getInventory().selected=1; whiteItemSmokeStage=2; whiteItemSmokeNextTick=now+40; }
            case 2 -> { saveSmokeScreenshot(mc,"echo-white-resonance-crystal.png"); mc.player.getInventory().selected=2; whiteItemSmokeStage=3; whiteItemSmokeNextTick=40+now; }
            case 3 -> { saveSmokeScreenshot(mc,"echo-white-enhanced-resonance-crystal.png"); mc.player.getInventory().selected=3; whiteItemSmokeStage=4; whiteItemSmokeNextTick=40+now; }
            case 4 -> { saveSmokeScreenshot(mc,"echo-white-frequency-crystal.png"); mc.player.getInventory().selected=4; whiteItemSmokeStage=5; whiteItemSmokeNextTick=40+now; }
            case 5 -> { saveSmokeScreenshot(mc,"echo-white-enhanced-frequency-crystal.png"); mc.player.getInventory().selected=5; whiteItemSmokeStage=6; whiteItemSmokeNextTick=40+now; }
            case 6 -> { saveSmokeScreenshot(mc,"echo-white-enhanced-frequency-crystal-2.png"); mc.player.getInventory().selected=6; whiteItemSmokeStage=7; whiteItemSmokeNextTick=40+now; }
            case 7 -> {
                saveSmokeScreenshot(mc,"echo-white-tuning-crystal.png");
                System.out.println("[EchoCrystalSmoke] Captured all six new crystal items against snow.");
                mc.options.mainHand().set(HumanoidArm.RIGHT); whiteItemSmokeStage=8;
            }
            default -> { }
        }
    }

    private static void tickEmissiveSmoke(Minecraft mc) {
        if (FMLEnvironment.production || !Boolean.getBoolean("echopickaxe.emissiveSmoke")) return;
        if (!visualVariantsChecked) {
            EchoItemVisuals.verifyResolvedVariants(mc, "initial-bake");
            visualVariantsChecked = true;
        }
        long now = mc.level.getGameTime();
        if (!emissiveSmokeStarted) {
            emissiveSmokeStarted = true;
            emissiveOriginalCameraType = mc.options.getCameraType();
            emissiveOriginalMainArm = mc.options.mainHand().get();
            emissiveSmokeNextTick = now + 80;
            return;
        }
        if (emissivePendingScreenshot != null) {
            if (now < emissiveCaptureAt) return;
            if (!ensureSmokeFramebuffer(mc, emissivePendingScreenshot)) {
                emissiveCaptureAt = now + 20;
                return;
            }
            String screenshot = emissivePendingScreenshot;
            emissivePendingScreenshot = null;
            Screenshot.grab(mc.gameDirectory, screenshot, mc.getMainRenderTarget(),
                    result -> System.out.println("[EchoEmissiveSmoke] Screenshot " + screenshot + ": " + result.getString()));
            return;
        }
        if (now < emissiveSmokeNextTick) return;
        mc.options.keyAttack.setDown(false);
        mc.options.keyUse.setDown(false);
        switch (emissiveSmokeStage) {
            case 0 -> {
                if (!mc.player.hasPermissions(2)) {
                    System.out.println("[EchoEmissiveSmoke] Abort: isolated world lacks command permission 2.");
                    emissiveSmokeStage = 10;
                    return;
                }
                mc.player.connection.sendCommand("echo verify");
                mc.player.connection.sendCommand("time set midnight");
                mc.player.connection.sendCommand("gamerule doDaylightCycle false");
                mc.player.connection.sendCommand("weather clear 1000000");
                mc.player.connection.sendCommand("gamerule doWeatherCycle false");
                mc.player.connection.sendCommand("fill ~-6 ~-2 ~-6 ~6 ~6 ~10 minecraft:black_concrete hollow");
                mc.player.connection.sendCommand("tp @s ~ ~ ~ 0 0");
                String[] ids = emissiveItemIds();
                for (int i = 0; i < ids.length; i++) {
                    if (i < 9) mc.player.connection.sendCommand("item replace entity @s hotbar." + i + " with echopickaxe:" + ids[i]);
                    else mc.player.connection.sendCommand("give @s echopickaxe:" + ids[i]);
                    int x = (i % 6) - 3;
                    int z = 3 + (i / 6) * 2;
                    mc.player.connection.sendCommand("summon minecraft:item ~" + x + " ~-1 ~" + z
                            + " {Item:{id:\"echopickaxe:" + ids[i] + "\",Count:1b},PickupDelay:32767}");
                }
                mc.player.connection.sendCommand("item replace entity @s weapon.offhand with echopickaxe:echo_crystal");
                mc.options.mainHand().set(HumanoidArm.RIGHT);
                restoreSmokeWindow(mc);
                emissiveSmokeStage = 1;
                emissiveSmokeNextTick = now + 120;
            }
            case 1 -> {
                if (!ensureSmokeFramebuffer(mc, "night")) {
                    emissiveSmokeNextTick = now + 20;
                    return;
                }
                inspectEmissiveModels(mc, "night");
                mc.player.getInventory().selected = 0;
                emissiveSmokeStage = 15;
                emissiveSmokeNextTick = now + 20;
            }
            case 15 -> {
                requestEmissiveScreenshot(mc, "echo-emissive-night-hands.png", now);
                emissiveSmokeStage = 11;
                emissiveSmokeNextTick = now + 5;
            }
            case 11 -> {
                var screen = new CreativeModeInventoryScreen(mc.player, mc.level.enabledFeatures(), mc.player.hasPermissions(2));
                mc.setScreen(screen);
                try {
                    var pagesField = CreativeModeInventoryScreen.class.getDeclaredField("pages");
                    pagesField.setAccessible(true);
                    var pages = (List<?>) pagesField.get(screen);
                    var targetPage = pages.stream().map(net.minecraftforge.client.gui.CreativeTabsScreenPage.class::cast)
                            .filter(page -> page.getVisibleTabs().contains(EchoMod.ECHO_TOOLS_TAB.get())).findFirst().orElseThrow();
                    screen.setCurrentPage(targetPage);
                    var selector = CreativeModeInventoryScreen.class.getDeclaredMethod("selectTab", CreativeModeTab.class);
                    selector.setAccessible(true);
                    selector.invoke(screen, EchoMod.ECHO_TOOLS_TAB.get());
                    System.out.println("[EchoEmissiveSmoke] Custom tab visible=" + screen.getCurrentPage().getVisibleTabs().contains(EchoMod.ECHO_TOOLS_TAB.get()));
                } catch (ReflectiveOperationException error) {
                    throw new IllegalStateException("Cannot select Echo Tools creative page", error);
                }
                emissiveSmokeStage = 2;
                emissiveSmokeNextTick = now + 30;
            }
            case 2 -> {
                requestEmissiveScreenshot(mc, "echo-emissive-night-gui-a.png", now);
                emissiveSmokeStage = 3;
                emissiveSmokeNextTick = now + 30;
            }
            case 3 -> {
                requestEmissiveScreenshot(mc, "echo-emissive-night-gui-b.png", now);
                emissiveSmokeStage = 12;
                emissiveSmokeNextTick = now + 5;
            }
            case 12 -> {
                mc.setScreen(null);
                mc.player.getInventory().selected = 0;
                mc.options.mainHand().set(HumanoidArm.LEFT);
                mc.player.connection.sendCommand("item replace entity @s weapon.offhand with echopickaxe:echo_upgrade_smithing_template");
                mc.player.connection.sendCommand("tp @s ~ ~ ~ 0 20");
                emissiveSmokeStage = 4;
                emissiveSmokeNextTick = now + 40;
            }
            case 4 -> {
                requestEmissiveScreenshot(mc, "echo-emissive-left-hand-and-drops.png", now);
                emissiveSmokeStage = 13;
                emissiveSmokeNextTick = now + 5;
            }
            case 13 -> {
                mc.player.connection.sendCommand("time set day");
                mc.player.connection.sendCommand("weather clear 1000000");
                mc.player.connection.sendCommand("fill ~-6 ~1 ~-6 ~6 ~10 ~10 air replace minecraft:black_concrete");
                mc.player.connection.sendCommand("fill ~-5 ~-1 ~6 ~5 ~5 ~6 minecraft:snow_block");
                mc.player.connection.sendCommand("tp @s ~ ~ ~ 0 0");
                mc.player.connection.sendCommand("item replace entity @s hotbar.0 with echopickaxe:enhanced_extension_crystal_2");
                mc.options.mainHand().set(HumanoidArm.RIGHT);
                mc.player.getInventory().selected = 0;
                emissiveSmokeStage = 5;
                emissiveSmokeNextTick = now + 40;
            }
            case 5 -> {
                requestEmissiveScreenshot(mc, "echo-emissive-white-enhanced-extension-crystal-2.png", now);
                emissiveSmokeStage = 16;
                emissiveSmokeNextTick = now + 5;
            }
            case 16 -> {
                mc.player.connection.sendCommand("item replace entity @s hotbar.0 with echopickaxe:echo_pickaxe");
                mc.player.connection.sendCommand("item replace entity @s hotbar.1 with echopickaxe:echo_pickaxe{EchoUpgrades:{resonance:1,frequency:0,tuning:0,extension:0}}");
                mc.player.connection.sendCommand("item replace entity @s hotbar.2 with echopickaxe:echo_pickaxe{EchoUpgrades:{resonance:2,frequency:2,tuning:1,extension:1}}");
                mc.player.connection.sendCommand("item replace entity @s hotbar.3 with echopickaxe:echo_pickaxe{EchoUpgrades:{resonance:2,frequency:3,tuning:1,extension:3}}");
                mc.player.connection.sendCommand("item replace entity @s weapon.offhand with minecraft:air");
                mc.player.connection.sendCommand("tp @s ~ ~ ~ 0 0");
                mc.options.setCameraType(CameraType.FIRST_PERSON);
                mc.options.mainHand().set(HumanoidArm.RIGHT);
                mc.player.getInventory().selected = 0;
                emissiveSmokeStage = 27;
                emissiveSmokeNextTick = now + 30;
            }
            case 27 -> {
                requestEmissiveScreenshot(mc, "echo-emissive-hand-first-right-ordinary.png", now);
                emissiveSmokeStage = 28;
                emissiveSmokeNextTick = now + 5;
            }
            case 28 -> {
                mc.options.mainHand().set(HumanoidArm.LEFT);
                requestEmissiveScreenshot(mc, "echo-emissive-hand-first-left-ordinary.png", now);
                emissiveSmokeStage = 29;
                emissiveSmokeNextTick = now + 5;
            }
            case 29 -> {
                mc.player.getInventory().selected = 3;
                mc.options.mainHand().set(HumanoidArm.RIGHT);
                emissiveSmokeStage = 37;
                emissiveSmokeNextTick = now + 15;
            }
            case 37 -> {
                requestEmissiveScreenshot(mc, "echo-emissive-hand-first-right-max.png", now);
                emissiveSmokeStage = 30;
                emissiveSmokeNextTick = now + 5;
            }
            case 30 -> {
                mc.options.mainHand().set(HumanoidArm.LEFT);
                requestEmissiveScreenshot(mc, "echo-emissive-hand-first-left-max.png", now);
                emissiveSmokeStage = 31;
                emissiveSmokeNextTick = now + 5;
            }
            case 31 -> {
                mc.player.getInventory().selected = 0;
                mc.options.mainHand().set(HumanoidArm.RIGHT);
                mc.player.connection.sendCommand("fill ~-5 ~-1 ~6 ~5 ~5 ~6 air replace minecraft:snow_block");
                mc.player.connection.sendCommand("item replace entity @s weapon.offhand with minecraft:diamond_pickaxe");
                mc.options.setCameraType(CameraType.THIRD_PERSON_FRONT);
                emissiveThirdPersonComparison = true;
                emissiveSmokeStage = 32;
                emissiveSmokeNextTick = now + 30;
            }
            case 32 -> {
                requestEmissiveScreenshot(mc, "echo-emissive-hand-third-front-45-dual-ordinary.png", now);
                emissiveSmokeStage = 34;
                emissiveSmokeNextTick = now + 5;
            }
            case 34 -> {
                mc.player.getInventory().selected = 3;
                emissiveSmokeStage = 35;
                emissiveSmokeNextTick = now + 30;
            }
            case 35 -> {
                requestEmissiveScreenshot(mc, "echo-emissive-hand-third-front-45-dual-max.png", now);
                emissiveSmokeStage = 36;
                emissiveSmokeNextTick = now + 5;
            }
            case 36 -> {
                emissiveThirdPersonComparison = false;
                mc.options.setCameraType(emissiveOriginalCameraType == null ? CameraType.FIRST_PERSON : emissiveOriginalCameraType);
                mc.options.mainHand().set(emissiveOriginalMainArm == null ? HumanoidArm.RIGHT : emissiveOriginalMainArm);
                mc.player.connection.sendCommand("item replace entity @s weapon.offhand with echopickaxe:echo_upgrade_smithing_template");
                mc.player.getInventory().selected = 0;
                emissiveSmokeStage = 23;
                emissiveSmokeNextTick = now + 20;
            }
            case 23 -> {
                EchoItemVisuals.verifyUpgradeShowcaseInventory(mc);
                mc.setScreen(new InventoryScreen(mc.player));
                emissiveSmokeStage = 19;
                emissiveSmokeNextTick = now + 30;
            }
            case 19 -> {
                requestEmissiveScreenshot(mc, "echo-emissive-upgrade-gui-comparison.png", now);
                emissiveSmokeStage = 20;
                emissiveSmokeNextTick = now + 5;
            }
            case 20 -> {
                mc.setScreen(null);
                mc.player.getInventory().selected = 3;
                emissiveSmokeStage = 21;
                emissiveSmokeNextTick = now + 40;
            }
            case 21 -> {
                requestEmissiveScreenshot(mc, "echo-emissive-upgrade-max-held-context.png", now);
                emissiveSmokeStage = 22;
                emissiveSmokeNextTick = now + 5;
            }
            case 22 -> {
                emissiveOriginalGuiScale = mc.options.guiScale().get();
                mc.options.guiScale().set(1);
                mc.resizeDisplay();
                mc.setScreen(EchoItemVisuals.createWhiteShowcaseScreen());
                emissiveSmokeStage = 25;
                emissiveSmokeNextTick = now + 30;
            }
            case 25 -> {
                requestEmissiveScreenshot(mc, "echo-emissive-upgrade-white-showcase.png", now);
                emissiveSmokeStage = 26;
                emissiveSmokeNextTick = now + 5;
            }
            case 26 -> {
                mc.setScreen(null);
                if (emissiveOriginalGuiScale >= 0) {
                    mc.options.guiScale().set(emissiveOriginalGuiScale);
                    mc.resizeDisplay();
                    emissiveOriginalGuiScale = -1;
                }
                emissiveSmokeStage = 14;
                emissiveSmokeNextTick = now + 5;
            }
            case 14 -> {
                emissiveReload = mc.reloadResourcePacks();
                emissiveReload.whenComplete((unused, error) -> {
                    if (error != null) System.out.println("[EchoEmissiveSmoke] Resource reload failed: " + error);
                    else System.out.println("[EchoEmissiveSmoke] Client resource reload completed.");
                });
                emissiveSmokeStage = 6;
                emissiveSmokeNextTick = now + 80;
            }
            case 6 -> {
                if (emissiveReload == null || !emissiveReload.isDone()) return;
                emissiveReload.join();
                restoreSmokeWindow(mc);
                if (!ensureSmokeFramebuffer(mc, "after-resource-reload")) { emissiveSmokeNextTick = now + 20; return; }
                inspectEmissiveModels(mc, "after-resource-reload");
                EchoItemVisuals.verifyResolvedVariants(mc, "after-resource-reload");
                requestEmissiveScreenshot(mc, "echo-emissive-after-resource-reload.png", now);
                emissiveSmokeStage = 7;
                emissiveSmokeNextTick = now + 5;
            }
            case 7 -> {
                System.out.println("[EchoEmissiveSmoke] PASS: all item models baked, emissive and ordinary faces present, animated sprites loaded; screenshots captured before/after resource reload.");
                emissiveSmokeStage = 10;
                mc.stop();
            }
            default -> { }
        }
    }

    @SubscribeEvent
    public static void adjustEmissiveComparisonCamera(ViewportEvent.ComputeCameraAngles event) {
        if (!FMLEnvironment.production && Boolean.getBoolean("echopickaxe.emissiveSmoke")
                && emissiveThirdPersonComparison) {
            Minecraft mc = Minecraft.getInstance();
            if (mc.player == null) return;
            try {
                if (emissiveCameraPositionSetter == null) {
                    emissiveCameraPositionSetter = Camera.class.getDeclaredMethod("setPosition", Vec3.class);
                    emissiveCameraPositionSetter.setAccessible(true);
                }
                Vec3 pivot = mc.player.getEyePosition((float) event.getPartialTick());
                Vec3 offset = event.getCamera().getPosition().subtract(pivot);
                Vec3 rotatedOffset = offset.yRot((float) Math.toRadians(-35.0));
                emissiveCameraPositionSetter.invoke(event.getCamera(), pivot.add(rotatedOffset));
            } catch (ReflectiveOperationException error) {
                throw new IllegalStateException("Cannot orbit camera for isolated held-item comparison", error);
            }
            event.setYaw(event.getYaw() + 35.0F);
        }
    }

    private static void requestEmissiveScreenshot(Minecraft mc, String name, long now) {
        mc.gui.getChat().clearMessages(false);
        emissivePendingScreenshot = name;
        emissiveCaptureAt = now + 2;
    }

    private static void restoreSmokeWindow(Minecraft mc) {
        var window = mc.getWindow();
        window.setWindowed(1280, 720);
        long handle = window.getWindow();
        GLFW.glfwRestoreWindow(handle);
        GLFW.glfwSetWindowSize(handle, 1280, 720);
        GLFW.glfwShowWindow(handle);
        GLFW.glfwFocusWindow(handle);
        GLFW.glfwPollEvents();
        window.updateDisplay();
        System.out.println("[EchoEmissiveSmoke] Restored dev window: framebuffer="
                + mc.getMainRenderTarget().width + "x" + mc.getMainRenderTarget().height);
    }

    private static boolean ensureSmokeFramebuffer(Minecraft mc, String phase) {
        int width = mc.getMainRenderTarget().width;
        int height = mc.getMainRenderTarget().height;
        if (width >= 640 && height >= 360) return true;
        System.out.println("[EchoEmissiveSmoke] Waiting for visible framebuffer during " + phase + ": " + width + "x" + height);
        restoreSmokeWindow(mc);
        return mc.getMainRenderTarget().width >= 640 && mc.getMainRenderTarget().height >= 360;
    }

    private static String[] emissiveItemIds() {
        return new String[]{"echo_pickaxe", "echo_upgrade_smithing_template", "echo_crystal", "resonance_crystal",
                "enhanced_resonance_crystal", "frequency_crystal", "enhanced_frequency_crystal",
                "enhanced_frequency_crystal_2", "tuning_crystal", "extension_crystal", "enhanced_extension_crystal",
                "enhanced_extension_crystal_2"};
    }

    private static void inspectEmissiveModels(Minecraft mc, String phase) {
        TextureAtlas atlas = mc.getModelManager().getAtlas(InventoryMenu.BLOCK_ATLAS);
        boolean passed = true;
        for (String id : emissiveItemIds()) {
            ItemStack stack = new ItemStack(BuiltInRegistries.ITEM.get(new ResourceLocation(EchoMod.MOD_ID, id)));
            BakedModel model = mc.getItemRenderer().getItemModelShaper().getItemModel(stack.getItem());
            int faces = 0;
            int emissiveFaces = 0;
            int ordinaryFaces = 0;
            for (BakedQuad quad : model.getQuads(null, null, RandomSource.create())) {
                Direction direction = quad.getDirection();
                if (direction != Direction.NORTH && direction != Direction.SOUTH) continue;
                faces++;
                int light = quad.getVertices()[IQuadTransformer.UV2];
                if (light == 0x00F000F0) emissiveFaces++;
                else ordinaryFaces++;
            }
            ResourceLocation glowId = new ResourceLocation(EchoMod.MOD_ID, "item/" + id + "_glow");
            TextureAtlasSprite sprite = atlas.getSprite(glowId);
            long atlasFrames = sprite.contents().getUniqueFrames().count();
            long metadataFrames = metadataUniqueFrames(mc, id);
            boolean itemPassed = faces > 0 && emissiveFaces > 0 && ordinaryFaces > 0 && atlasFrames > 1
                    && atlasFrames == metadataFrames
                    && sprite.contents().width() == ("echo_pickaxe".equals(id) ? 64 : id.matches("echo_pickaxe_v\\d{3}") ? 128 : 32) && sprite.contents().height() == ("echo_pickaxe".equals(id) ? 64 : id.matches("echo_pickaxe_v\\d{3}") ? 128 : 32);
            passed &= itemPassed;
            System.out.println("[EchoEmissiveSmoke] " + phase + " " + id + " faces=" + faces + " fullbright="
                    + emissiveFaces + " ordinary=" + ordinaryFaces + " atlasFrames=" + atlasFrames + " metadataFrames=" + metadataFrames + " frameSize="
                    + sprite.contents().width() + "x" + sprite.contents().height() + " PASS=" + itemPassed);
        }
        if (!passed) throw new IllegalStateException("One or more Echo item emissive resources/models failed validation during " + phase);
    }

    private static long metadataUniqueFrames(Minecraft mc, String id) {
        ResourceLocation metadataId = new ResourceLocation(EchoMod.MOD_ID, "textures/item/" + id + "_glow.png.mcmeta");
        var resource = mc.getResourceManager().getResource(metadataId)
                .orElseThrow(() -> new IllegalStateException("Missing animation metadata " + metadataId));
        try (var reader = new InputStreamReader(resource.open(), StandardCharsets.UTF_8)) {
            JsonObject root = JsonParser.parseReader(reader).getAsJsonObject();
            JsonObject animation = root.getAsJsonObject("animation");
            if (animation.get("width").getAsInt() != ("echo_pickaxe".equals(id) ? 64 : id.matches("echo_pickaxe_v\\d{3}") ? 128 : 32) || animation.get("height").getAsInt() != ("echo_pickaxe".equals(id) ? 64 : id.matches("echo_pickaxe_v\\d{3}") ? 128 : 32) || mc.getModelManager().getAtlas(InventoryMenu.BLOCK_ATLAS).getSprite(new ResourceLocation(EchoMod.MOD_ID, "item/" + id + "_glow")).contents().width() != animation.get("width").getAsInt() || mc.getModelManager().getAtlas(InventoryMenu.BLOCK_ATLAS).getSprite(new ResourceLocation(EchoMod.MOD_ID, "item/" + id + "_glow")).contents().height() != animation.get("height").getAsInt())
                throw new IllegalStateException("Unexpected animation frame size in " + metadataId);
            JsonArray frames = animation.getAsJsonArray("frames");
            if (frames == null) throw new IllegalStateException("Expected explicit animation frame sequence in " + metadataId);
            Set<Integer> unique = new HashSet<>();
            for (JsonElement frame : frames) {
                int index = frame.isJsonObject() ? frame.getAsJsonObject().get("index").getAsInt() : frame.getAsInt();
                unique.add(index);
            }
            return unique.size();
        } catch (java.io.IOException error) {
            throw new IllegalStateException("Cannot read animation metadata " + metadataId, error);
        }
    }

    private static void logBakedPickaxeQuads(Minecraft mc) {
        BakedModel model = mc.getItemRenderer().getItemModelShaper()
                .getItemModel(EchoMod.ECHO_PICKAXE.get());
        int quads = model.getQuads(null, null, RandomSource.create()).size();
        for (Direction direction : Direction.values()) {
            quads += model.getQuads(null, direction, RandomSource.create()).size();
        }
        System.out.println("[EchoWhiteItemSmoke] Baked echo_pickaxe quad count=" + quads
                + "; attackDown=" + mc.options.keyAttack.isDown()
                + "; attackStrength=" + mc.player.getAttackStrengthScale(0.0F));
    }

    private static int findPickaxeSlot(Minecraft mc) {
        var inventory = mc.player.getInventory();
        for (int slot = 0; slot < 36; slot++) {
            ItemStack stack = inventory.getItem(slot);
            if (!stack.is(com.jaysay.echotools.EchoMod.ECHO_PICKAXE.get())) continue;
            return slot;
        }
        return -1;
    }

    private static void selectPickaxe(Minecraft mc) {
        int slot = findPickaxeSlot(mc);
        if (slot >= 0 && slot < 9) mc.player.getInventory().selected = slot;
    }

    private static void saveSmokeScreenshot(Minecraft mc, String name) {
        mc.gui.getChat().clearMessages(false);
        Screenshot.grab(mc.gameDirectory, name,
                mc.getMainRenderTarget(), result -> System.out.println("[EchoSmoke] " + result.getString()));
    }

    @SubscribeEvent
    public static void renderEchoGuide(RenderLevelStageEvent event) {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_PARTICLES || target == null) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null || !mc.level.dimension().location().equals(dimension)) {
            clear();
            return;
        }

        double age = mc.level.getGameTime() - receivedAtTick + event.getPartialTick();
        if (age >= displayTicks) {
            clear();
            return;
        }
        float fadeIn = (float) Math.min(1.0, age / 5.0);
        float fadeOut = (float) Math.min(1.0, (displayTicks - age) / 14.0);
        float fade = Math.max(0.0F, Math.min(fadeIn, fadeOut));
        if (fade <= 0.0F) return;

        Player player = mc.player;
        Camera camera = event.getCamera();
        Vec3 view = toVec3(camera.getLookVector()).normalize();
        Vec3 from = player.getEyePosition(event.getPartialTick()).add(view.scale(0.55)).add(0.0, -0.36, 0.0);
        Vec3 to = Vec3.atCenterOf(target);
        Vec3 delta = to.subtract(from);
        double distance = delta.length();
        if (distance < 0.25) return;
        Vec3 direction = delta.scale(1.0 / distance);
        Vec3 side = direction.cross(view);
        if (side.lengthSqr() < 1.0e-5) side = direction.cross(new Vec3(0, 1, 0));
        if (side.lengthSqr() < 1.0e-5) side = direction.cross(new Vec3(1, 0, 0));
        side = side.normalize();
        boolean occluded = isOccluded(player, player.getEyePosition(event.getPartialTick()), to);
        float visibility = occluded ? 0.62F : 1.0F;

        PoseStack pose = event.getPoseStack();
        MultiBufferSource.BufferSource buffers = mc.renderBuffers().bufferSource();
        pose.pushPose();
        try {
            Vec3 cameraPos = camera.getPosition();
            pose.translate(-cameraPos.x, -cameraPos.y, -cameraPos.z);
            VertexConsumer out = buffers.getBuffer(EchoRenderTypes.XRAY_QUADS);
            var matrix = pose.last().pose();

            float pathAlpha = fade * visibility * (occluded ? 0.28F : 0.42F);
            for (int i = 0; i < 24; i++) {
                double start = i / 24.0;
                double end = (i + 1) / 24.0;
                drawRibbon(out, matrix, pathPoint(from, delta, side, start),
                        pathPoint(from, delta, side, end), side, 0.032, PATH_CYAN, pathAlpha);
            }
            // Bone-white dashes make the full direction legible even when the cyan trail crosses stone.
            for (int i = 0; i < 11; i++) {
                double start = i / 11.0;
                double end = Math.min(1.0, start + 0.035);
                Vec3 a = pathPoint(from, delta, side, start);
                Vec3 b = pathPoint(from, delta, side, end);
                drawRibbon(out, matrix, a, b, side, 0.048,
                        (i % 2 == 0 ? BONE_WHITE : PATH_CYAN), fade * visibility * (occluded ? 0.48F : 0.82F));
            }

            // Several camera-facing chevrons travel from the player's eye toward the found block.
            double travel = age * 0.018;
            for (int i = 0; i < 3; i++) {
                double progress = 0.10 + ((travel + i * 0.245) % 0.76);
                Vec3 center = pathPoint(from, delta, side, progress);
                double size = Math.min(0.42, Math.max(0.24, distance * 0.035));
                drawArrow(out, matrix, center, direction, side, size,
                        fade * visibility * (occluded ? 0.72F : 1.0F));
            }

            for (int i = 0; i < targets.size(); i++) {
                if (i == selectedTarget) continue;
                drawOreMarker(out, matrix, targets.get(i), view,
                        toVec3(camera.getLeftVector()).scale(-1.0).normalize(),
                        toVec3(camera.getUpVector()).normalize(), fade * 0.24F);
                drawTargetNumber(out,matrix,targets.get(i),
                        toVec3(camera.getLeftVector()).scale(-1.0).normalize(),
                        toVec3(camera.getUpVector()).normalize(),i+1,fade*0.85F);
            }
            drawOreMarker(out, matrix, target, view,
                    toVec3(camera.getLeftVector()).scale(-1.0).normalize(),
                    toVec3(camera.getUpVector()).normalize(), fade * visibility);
            drawTargetNumber(out,matrix,target,toVec3(camera.getLeftVector()).scale(-1.0).normalize(),
                    toVec3(camera.getUpVector()).normalize(),selectedTarget+1,fade*visibility);
            boolean depthWasEnabled = GL11.glIsEnabled(GL11.GL_DEPTH_TEST);
            try {
                // In this MC version NO_DEPTH_TEST uses GL_ALWAYS but its setup is a no-op.
                // Explicitly scope the GL state around this one batch so walls cannot occlude the guide.
                RenderSystem.disableDepthTest();
                buffers.endBatch(EchoRenderTypes.XRAY_QUADS);
            } finally {
                if (depthWasEnabled) RenderSystem.enableDepthTest();
                else RenderSystem.disableDepthTest();
            }
        } finally {
            pose.popPose();
        }
    }

    private static boolean isOccluded(Player player, Vec3 from, Vec3 to) {
        HitResult hit = player.level().clip(new ClipContext(from, to,
                ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, player));
        return hit.getType() == HitResult.Type.BLOCK
                && hit instanceof BlockHitResult blockHit && !blockHit.getBlockPos().equals(target);
    }

    private static Vec3 pathPoint(Vec3 start, Vec3 delta, Vec3 side, double t) {
        return start.add(delta.scale(t)).add(side.scale(Math.sin(Math.PI * t) * 0.22));
    }

    private static Vec3 toVec3(org.joml.Vector3f vector) {
        return new Vec3(vector.x(), vector.y(), vector.z());
    }

    private static void drawArrow(VertexConsumer out, org.joml.Matrix4f matrix, Vec3 center,
                                  Vec3 direction, Vec3 side, double size, float alpha) {
        Vec3 tip = center.add(direction.scale(size * 0.55));
        Vec3 tailCenter = center.subtract(direction.scale(size * 0.40));
        Vec3 left = tailCenter.add(side.scale(size * 0.38));
        Vec3 right = tailCenter.subtract(side.scale(size * 0.38));
        drawRibbon(out, matrix, left, tip, side, size * 0.09, BONE_WHITE, alpha);
        drawRibbon(out, matrix, tip, right, side, size * 0.09, BONE_WHITE, alpha);
        // A cyan core keeps the silhouette vivid against both bright and dark blocks.
        drawRibbon(out, matrix, left, tip, side, size * 0.035, PATH_CYAN, Math.min(1.0F, alpha * 1.15F));
        drawRibbon(out, matrix, tip, right, side, size * 0.035, PATH_CYAN, Math.min(1.0F, alpha * 1.15F));
    }

    private static void drawOreMarker(VertexConsumer out, org.joml.Matrix4f matrix,
                                      BlockPos block, Vec3 cameraLook, Vec3 cameraRight,
                                      Vec3 cameraUp, float fade) {
        double minX = block.getX() - 0.055, minY = block.getY() - 0.055, minZ = block.getZ() - 0.055;
        double maxX = block.getX() + 1.055, maxY = block.getY() + 1.055, maxZ = block.getZ() + 1.055;
        Vec3[] corners = {
                new Vec3(minX, minY, minZ), new Vec3(maxX, minY, minZ),
                new Vec3(maxX, minY, maxZ), new Vec3(minX, minY, maxZ),
                new Vec3(minX, maxY, minZ), new Vec3(maxX, maxY, minZ),
                new Vec3(maxX, maxY, maxZ), new Vec3(minX, maxY, maxZ)
        };
        int[][] edges = {{0,1},{1,2},{2,3},{3,0},{4,5},{5,6},{6,7},{7,4},{0,4},{1,5},{2,6},{3,7}};
        for (int i = 0; i < edges.length; i++) {
            Vec3 a = corners[edges[i][0]], b = corners[edges[i][1]];
            Vec3 edge = b.subtract(a).normalize();
            Vec3 width = edge.cross(cameraLook);
            if (width.lengthSqr() < 1.0e-5) width = edge.cross(new Vec3(0, 1, 0));
            if (width.lengthSqr() < 1.0e-5) width = edge.cross(new Vec3(1, 0, 0));
            drawRibbon(out, matrix, a, b, width.normalize(), 0.027,
                    (i % 3 == 0 ? BONE_WHITE : PATH_CYAN), fade * 0.94F);
        }
        // Four short corner ticks project outward from the target cube as a clear lock-on reticle.
        Vec3 top = Vec3.atCenterOf(block).add(cameraUp.scale(0.68));
        drawRibbon(out, matrix, top.subtract(cameraRight.scale(0.19)), top.subtract(cameraRight.scale(0.045)), cameraUp, 0.035, BONE_WHITE, fade);
        drawRibbon(out, matrix, top.add(cameraRight.scale(0.045)), top.add(cameraRight.scale(0.19)), cameraUp, 0.035, BONE_WHITE, fade);
        drawRibbon(out, matrix, top.subtract(cameraUp.scale(0.19)), top.subtract(cameraUp.scale(0.045)), cameraRight, 0.035, PATH_CYAN, fade);
        drawRibbon(out, matrix, top.add(cameraUp.scale(0.045)), top.add(cameraUp.scale(0.19)), cameraRight, 0.035, PATH_CYAN, fade);
    }

    private static void drawTargetNumber(VertexConsumer out, org.joml.Matrix4f matrix, BlockPos block,
                                         Vec3 right, Vec3 up, int number, float alpha) {
        String[] digits={"010110010010111","111001111100111","111001111001111","101101111001001",
                "111100111001111","111100111101111","111001001001001","111101111101111"};
        String bits=digits[Math.max(0,Math.min(7,number-1))];
        Vec3 center=Vec3.atCenterOf(block).add(up.scale(0.82)).add(right.scale(-0.09));
        double pixel=0.075;
        for(int i=0;i<15;i++) if(bits.charAt(i)=='1') {
            int row=i/3,col=i%3;
            Vec3 c=center.add(right.scale((col-1)*pixel)).add(up.scale((2-row)*pixel));
            Vec3 r=right.scale(pixel*0.42),v=up.scale(pixel*0.42);
            vertex(out,matrix,c.subtract(r).subtract(v),BONE_WHITE,alpha);
            vertex(out,matrix,c.add(r).subtract(v),BONE_WHITE,alpha);
            vertex(out,matrix,c.add(r).add(v),BONE_WHITE,alpha);
            vertex(out,matrix,c.subtract(r).add(v),BONE_WHITE,alpha);
        }
    }

    private static void drawRibbon(VertexConsumer out, org.joml.Matrix4f matrix, Vec3 start, Vec3 end,
                                   Vec3 side, double halfWidth, int rgb, float alpha) {
        if (alpha <= 0.0F) return;
        Vec3 width = side.scale(halfWidth);
        vertex(out, matrix, start.add(width), rgb, alpha);
        vertex(out, matrix, end.add(width), rgb, alpha);
        vertex(out, matrix, end.subtract(width), rgb, alpha);
        vertex(out, matrix, start.subtract(width), rgb, alpha);
    }

    private static void vertex(VertexConsumer out, org.joml.Matrix4f matrix, Vec3 pos, int rgb, float alpha) {
        out.vertex(matrix, (float) pos.x, (float) pos.y, (float) pos.z)
                .color((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255,
                        Math.max(0, Math.min(255, (int) (alpha * 255.0F))))
                .endVertex();
    }

    /** RenderType state setup/clear is paired by BufferSource, so x-ray blending is scoped to this batch. */
    private abstract static class EchoRenderTypes extends RenderType {
        private static final RenderType XRAY_QUADS = create("echopickaxe_echo_guide",
                DefaultVertexFormat.POSITION_COLOR, VertexFormat.Mode.QUADS, 4096, false, false,
                CompositeState.builder()
                        .setShaderState(POSITION_COLOR_SHADER)
                        .setTransparencyState(TRANSLUCENT_TRANSPARENCY)
                        .setDepthTestState(NO_DEPTH_TEST)
                        .setCullState(NO_CULL)
                        .setWriteMaskState(COLOR_WRITE)
                        .createCompositeState(false));

        private EchoRenderTypes() {
            super("echopickaxe_echo_guide", DefaultVertexFormat.POSITION_COLOR,
                    VertexFormat.Mode.QUADS, 4096, false, false, () -> {}, () -> {});
        }
    }
}

@Mod.EventBusSubscriber(modid = EchoMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.MOD)
final class EchoClientModEvents {
    private EchoClientModEvents() {}
    @SubscribeEvent static void registerKeys(RegisterKeyMappingsEvent event) { event.register(EchoClient.targetKey()); }
}
