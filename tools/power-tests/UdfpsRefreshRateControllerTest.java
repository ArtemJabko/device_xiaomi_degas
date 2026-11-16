package com.android.systemui.biometrics;

import java.util.ArrayList;
import java.util.List;

/** Standalone deterministic tests of the exact class added by platform patch 0005. */
public final class UdfpsRefreshRateControllerTest {
    static final class Task {
        long due;
        Runnable action;
        boolean cancelled;
        Task(long due, Runnable action) { this.due = due; this.action = action; }
    }
    static final class Fixture {
        long now;
        boolean ready;
        final List<Task> tasks = new ArrayList<>();
        final List<String> events = new ArrayList<>();
        final UdfpsRefreshRateController controller = new UdfpsRefreshRateController(
                (action, delay) -> {
                    Task task = new Task(now + delay, action);
                    tasks.add(task);
                    return () -> task.cancelled = true;
                }, () -> ready, () -> events.add("enable"), () -> events.add("disable"));
        void aod() { controller.setDozing(true); controller.setOverlayVisible(true); }
        void scan() { controller.startScan(() -> events.add("scan"), () -> events.add("timeout")); }
        void advance(long delta) {
            long target = now + delta;
            while (true) {
                Task next = null;
                for (Task t : tasks) {
                    if (t.due <= target && (next == null || t.due < next.due)) next = t;
                }
                if (next == null) break;
                tasks.remove(next);
                now = next.due;
                if (!next.cancelled) next.action.run();
            }
            now = target;
        }
        void expect(String... expected) {
            if (!events.equals(List.of(expected))) throw new AssertionError(events + " != " + List.of(expected));
        }
    }
    public static void main(String[] args) {
        Fixture f = new Fixture();
        f.aod(); f.advance(2000); f.expect();

        f = new Fixture();
        f.controller.setOverlayVisible(true); f.expect("enable");
        f.controller.setDozing(true); f.advance(199); f.expect("enable");
        f.advance(1); f.expect("enable", "disable");

        f = new Fixture(); f.aod(); f.scan(); f.advance(100); f.expect("enable");
        f.ready = true; f.controller.onDisplayChanged(); f.advance(19); f.expect("enable");
        f.advance(1); f.expect("enable", "scan");
        f.controller.endScan(); f.advance(199); f.expect("enable", "scan");
        f.advance(1); f.expect("enable", "scan", "disable");

        f = new Fixture(); f.aod(); f.ready = true; f.scan();
        Task oldSettlement = f.tasks.get(1);
        f.controller.endScan(); oldSettlement.action.run(); f.advance(1000);
        f.expect("enable", "disable");

        f = new Fixture(); f.aod(); f.scan(); f.controller.setOverlayVisible(false);
        f.ready = true; f.controller.onDisplayChanged(); f.advance(1000);
        f.expect("enable", "disable");

        f = new Fixture(); f.aod(); f.scan(); f.advance(800); f.expect("enable", "timeout");
        f.ready = true; f.controller.onDisplayChanged(); f.advance(200);
        f.expect("enable", "timeout", "disable");

        f = new Fixture(); f.aod(); f.ready = true; f.scan();
        oldSettlement = f.tasks.get(1);
        f.ready = false; f.controller.onDisplayChanged();
        f.ready = true; f.controller.onDisplayChanged();
        oldSettlement.action.run(); f.expect("enable");
        f.advance(20); f.expect("enable", "scan");

        f = new Fixture(); f.aod(); f.ready = true; f.scan(); f.advance(20);
        f.controller.endScan(); Task oldRelease = f.tasks.get(f.tasks.size() - 1);
        f.advance(100); f.scan(); oldRelease.action.run(); f.advance(20);
        f.expect("enable", "scan", "scan");
        f.controller.setDozing(false); f.controller.endScan(); f.advance(1000);
        f.expect("enable", "scan", "scan");
        f.controller.setOverlayVisible(false); f.advance(200);
        f.expect("enable", "scan", "scan", "disable");

        System.out.println("PASS: 8 scenarios (idle AOD, interactive hold, mode confirmation, finger-up, teardown, timeout, stale settlement, scan reentry)");
    }
}
