package io.github.hanenashi.overtura;

import android.app.PendingIntent;
import android.content.Intent;
import android.net.Uri;

import java.lang.ref.WeakReference;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;

/** Termux RUN_COMMAND transport for explicit, read-only background queries. */
final class TermuxBridge {
    private static final String TERMUX = "com.termux";
    private static final String SERVICE = "com.termux.app.RunCommandService";
    private static final AtomicInteger REQUEST_CODE = new AtomicInteger();
    private static final Map<String, Delivery> ACTIVE = new HashMap<>();

    private TermuxBridge() {}

    private static final class Delivery {
        final WeakReference<MainActivity> owner;
        final String operation;
        final long token;
        Delivery(MainActivity activity, String operation, long token) {
            owner = new WeakReference<>(activity);
            this.operation = operation;
            this.token = token;
        }
    }

    static void start(MainActivity activity, String host, String operation, long token) {
        // Termux expands $PREFIX only in RUN_COMMAND_PATH. Its own shell then
        // resolves timeout and ssh from the Termux PATH on any Android user.
        String[] argv = {"-c", Commands.termuxShellQuery(host, operation)};

        String id = UUID.randomUUID().toString();
        Intent callback = new Intent(activity, TermuxResultReceiver.class)
            .setData(Uri.parse("overtura://query/" + id));
        PendingIntent result = PendingIntent.getBroadcast(activity, REQUEST_CODE.incrementAndGet(),
            callback, PendingIntent.FLAG_ONE_SHOT | PendingIntent.FLAG_MUTABLE);

        Intent command = new Intent("com.termux.RUN_COMMAND")
            .setClassName(TERMUX, SERVICE)
            .putExtra("com.termux.RUN_COMMAND_PATH", "$PREFIX/bin/sh")
            .putExtra("com.termux.RUN_COMMAND_ARGUMENTS", argv)
            .putExtra("com.termux.RUN_COMMAND_BACKGROUND", true)
            .putExtra("com.termux.RUN_COMMAND_PENDING_INTENT", result);
        synchronized (ACTIVE) { ACTIVE.put(id, new Delivery(activity, operation, token)); }
        try {
            if (activity.startService(command) == null) throw new IllegalStateException("Termux service unavailable");
        } catch (RuntimeException error) {
            synchronized (ACTIVE) { ACTIVE.remove(id); }
            result.cancel();
            throw error;
        }
    }

    static void deliver(Intent intent) {
        Uri data = intent == null ? null : intent.getData();
        if (data == null || !"overtura".equals(data.getScheme()) || !"query".equals(data.getHost())) return;
        Delivery delivery;
        synchronized (ACTIVE) { delivery = ACTIVE.remove(data.getLastPathSegment()); }
        if (delivery == null) return;
        MainActivity activity = delivery.owner.get();
        if (activity != null) activity.onTermuxResult(delivery.operation, delivery.token, intent);
    }

    static void forget(MainActivity activity) {
        synchronized (ACTIVE) {
            ACTIVE.entrySet().removeIf(row -> row.getValue().owner.get() == activity);
        }
    }

    static void forget(MainActivity activity, String operation, long token) {
        synchronized (ACTIVE) {
            ACTIVE.entrySet().removeIf(row -> row.getValue().owner.get() == activity
                && row.getValue().operation.equals(operation) && row.getValue().token == token);
        }
    }
}
