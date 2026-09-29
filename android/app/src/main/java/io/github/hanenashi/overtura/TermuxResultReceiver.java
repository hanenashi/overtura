package io.github.hanenashi.overtura;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Receives Termux's one-shot result and forwards it only to the waiting Activity. */
public final class TermuxResultReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        TermuxBridge.deliver(intent);
    }
}
