package com.jaysay.echotools.client;

import com.jaysay.echotools.EchoNetwork;
import com.jaysay.echotools.EchoOreKind;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.client.gui.components.Button;
import net.minecraft.world.InteractionHand;

public final class EchoFilterScreen extends Screen {
    private final String current;
    public EchoFilterScreen(String current) { super(Component.translatable("screen.echopickaxe.filter.title")); this.current=current; }
    @Override protected void init() {
        int gap=5, columns=this.width<330?2:3;
        int width=Math.max(70,Math.min(112,(this.width-24-(columns-1)*gap)/columns));
        int rows=(EchoOreKind.values().length+columns-1)/columns;
        int left=(this.width-(columns*width+(columns-1)*gap))/2;
        int top=(this.height-(rows*26+50))/2;
        for (EchoOreKind kind: EchoOreKind.values()) {
            int index=kind.ordinal(), x=left+(index%columns)*(width+gap), y=top+(index/columns)*26;
            Component label=kind==EchoOreKind.ALL ? Component.translatable("screen.echopickaxe.filter.all")
                    : Component.translatable("screen.echopickaxe.ore."+kind.id());
            if (kind.id().equals(current)) label=Component.literal("✓ ").append(label);
            addRenderableWidget(Button.builder(label, b->{ EchoNetwork.sendFilter(kind.id(),InteractionHand.MAIN_HAND); onClose(); })
                    .bounds(x,y,width,20).build());
        }
        addRenderableWidget(Button.builder(Component.translatable("screen.echopickaxe.filter.close"), b->onClose())
                .bounds(this.width/2-56,top+rows*26+4,112,20).build());
    }
    @Override public void render(GuiGraphics graphics,int mouseX,int mouseY,float partialTick) {
        renderBackground(graphics); int columns=width<330?2:3;
        int rows=(EchoOreKind.values().length+columns-1)/columns;
        int panelTop=(height-(rows*26+50))/2;
        graphics.drawCenteredString(font,title,width/2,Math.max(8,panelTop-14),0xFFFFFF);
        super.render(graphics,mouseX,mouseY,partialTick);
    }
    @Override public boolean isPauseScreen() { return false; }
}
