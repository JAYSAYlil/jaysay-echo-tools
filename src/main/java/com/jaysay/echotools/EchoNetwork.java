package com.jaysay.echotools;

import com.jaysay.echotools.client.EchoClient;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.PacketDistributor;
import net.minecraftforge.network.simple.SimpleChannel;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.function.Supplier;

/** Versioned private-session packets for scan guidance and tuning controls. */
public final class EchoNetwork {
    private static final String PROTOCOL = "4";
    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
            new ResourceLocation(EchoMod.MOD_ID, "main"), () -> PROTOCOL,
            PROTOCOL::equals, PROTOCOL::equals);
    private EchoNetwork() {}

    public static void register() {
        CHANNEL.registerMessage(0, ScanTargetsPacket.class, ScanTargetsPacket::encode,
                ScanTargetsPacket::decode, ScanTargetsPacket::handle, Optional.of(NetworkDirection.PLAY_TO_CLIENT));
        CHANNEL.registerMessage(1, CycleTargetRequest.class, CycleTargetRequest::encode,
                CycleTargetRequest::decode, CycleTargetRequest::handle, Optional.of(NetworkDirection.PLAY_TO_SERVER));
        CHANNEL.registerMessage(2, FilterRequest.class, FilterRequest::encode,
                FilterRequest::decode, FilterRequest::handle, Optional.of(NetworkDirection.PLAY_TO_SERVER));
        CHANNEL.registerMessage(3, OpenFilterPacket.class, OpenFilterPacket::encode,
                OpenFilterPacket::decode, OpenFilterPacket::handle, Optional.of(NetworkDirection.PLAY_TO_CLIENT));
    }

    public static void sendTargets(ServerPlayer player, List<BlockPos> targets, int selected, int durationTicks) {
        CHANNEL.send(PacketDistributor.PLAYER.with(() -> player), new ScanTargetsPacket(
                player.level().dimension().location(), targets, selected, false, durationTicks));
    }
    public static void startTargets(ServerPlayer player, List<BlockPos> targets, int selected, int durationTicks) {
        CHANNEL.send(PacketDistributor.PLAYER.with(() -> player), new ScanTargetsPacket(
                player.level().dimension().location(), targets, selected, true, durationTicks));
    }
    public static void clearTarget(ServerPlayer player) {
        CHANNEL.send(PacketDistributor.PLAYER.with(() -> player), ScanTargetsPacket.CLEAR);
    }
    public static void cycleTarget() { CHANNEL.sendToServer(new CycleTargetRequest()); }
    public static void sendFilter(String id, InteractionHand hand) { CHANNEL.sendToServer(new FilterRequest(id, hand)); }
    public static void openFilter(ServerPlayer player, String selected) {
        CHANNEL.send(PacketDistributor.PLAYER.with(() -> player), new OpenFilterPacket(selected));
    }

    public static final class ScanTargetsPacket {
        private static final int MAX_TARGETS = 8;
        private static final ScanTargetsPacket CLEAR = new ScanTargetsPacket(null, List.of(), 0, true, 0);
        final ResourceLocation dimension;
        final List<BlockPos> targets;
        final int selected;
        final boolean resetTimer;
        final int durationTicks;
        ScanTargetsPacket(ResourceLocation dimension, List<BlockPos> targets, int selected, boolean resetTimer, int durationTicks) {
            this.dimension = dimension;
            this.targets = targets.stream().limit(MAX_TARGETS).map(BlockPos::immutable).toList();
            this.selected = this.targets.isEmpty() ? 0 : Math.max(0, Math.min(selected, this.targets.size() - 1));
            this.resetTimer = resetTimer;
            this.durationTicks = durationTicks;
        }
        static void encode(ScanTargetsPacket p, FriendlyByteBuf b) {
            b.writeBoolean(p.dimension != null && !p.targets.isEmpty());
            if (p.dimension != null && !p.targets.isEmpty()) {
                b.writeResourceLocation(p.dimension); b.writeVarInt(p.targets.size());
                p.targets.forEach(b::writeBlockPos); b.writeVarInt(p.selected); b.writeBoolean(p.resetTimer); b.writeVarInt(p.durationTicks);
            }
        }
        static ScanTargetsPacket decode(FriendlyByteBuf b) {
            if (!b.readBoolean()) return CLEAR;
            ResourceLocation dim = b.readResourceLocation();
            int count = b.readVarInt();
            if (count < 1 || count > MAX_TARGETS) throw new IllegalArgumentException("Invalid Echo target count: " + count);
            List<BlockPos> positions = new ArrayList<>(count);
            for (int i=0;i<count;i++) positions.add(b.readBlockPos().immutable());
            int selected = b.readVarInt();
            if (selected < 0 || selected >= positions.size()) throw new IllegalArgumentException("Invalid selected Echo target");
            boolean resetTimer=b.readBoolean();
            int durationTicks=b.readVarInt();
            if (durationTicks!=140 && durationTicks!=280 && durationTicks!=420 && durationTicks!=560)
                throw new IllegalArgumentException("Invalid Echo guidance duration: " + durationTicks);
            return new ScanTargetsPacket(dim, positions, selected, resetTimer, durationTicks);
        }
        static void handle(ScanTargetsPacket p, Supplier<net.minecraftforge.network.NetworkEvent.Context> supplier) {
            var c=supplier.get(); c.enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                    () -> () -> EchoClient.receive(p.dimension, p.targets, p.selected, p.resetTimer, p.durationTicks))); c.setPacketHandled(true);
        }
    }

    public static final class CycleTargetRequest {
        static void encode(CycleTargetRequest p, FriendlyByteBuf b) {}
        static CycleTargetRequest decode(FriendlyByteBuf b) { return new CycleTargetRequest(); }
        static void handle(CycleTargetRequest p, Supplier<net.minecraftforge.network.NetworkEvent.Context> supplier) {
            var c=supplier.get(); c.enqueueWork(() -> { if (c.getSender()!=null) EchoMod.cycleTarget(c.getSender()); }); c.setPacketHandled(true);
        }
    }
    public static final class FilterRequest {
        final String id;
        final InteractionHand hand;
        FilterRequest(String id, InteractionHand hand) { this.id=id; this.hand=hand; }
        static void encode(FilterRequest p, FriendlyByteBuf b) { b.writeUtf(p.id, 24); b.writeEnum(p.hand); }
        static FilterRequest decode(FriendlyByteBuf b) { return new FilterRequest(b.readUtf(24),b.readEnum(InteractionHand.class)); }
        static void handle(FilterRequest p, Supplier<net.minecraftforge.network.NetworkEvent.Context> supplier) {
            var c=supplier.get(); c.enqueueWork(() -> { if (c.getSender()!=null) EchoMod.setOreFilter(c.getSender(), p.id,p.hand); }); c.setPacketHandled(true);
        }
    }
    public static final class OpenFilterPacket {
        final String id;
        OpenFilterPacket(String id) { this.id=id; }
        static void encode(OpenFilterPacket p, FriendlyByteBuf b) { b.writeUtf(p.id,24); }
        static OpenFilterPacket decode(FriendlyByteBuf b) { return new OpenFilterPacket(b.readUtf(24)); }
        static void handle(OpenFilterPacket p, Supplier<net.minecraftforge.network.NetworkEvent.Context> supplier) {
            var c=supplier.get(); c.enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                    () -> () -> EchoClient.openFilter(p.id))); c.setPacketHandled(true);
        }
    }
}
