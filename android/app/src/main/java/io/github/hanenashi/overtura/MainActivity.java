package io.github.hanenashi.overtura;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

public class MainActivity extends Activity {
    private static final int BG = Color.rgb(17, 27, 33);
    private static final int CARD = Color.rgb(28, 41, 48);
    private static final int INK = Color.rgb(242, 241, 231);
    private static final int MUTED = Color.rgb(169, 184, 190);
    private static final int GREEN = Color.rgb(168, 217, 197);
    private static final int LINE = Color.rgb(48, 65, 72);
    private LinearLayout root;
    private LinearLayout page;
    private SharedPreferences preferences;
    private int tab;
    private final QueryState doctorState = new QueryState();
    private final QueryState sessionsState = new QueryState();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private static final String RUN_COMMAND = "com.termux.permission.RUN_COMMAND";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        preferences = getSharedPreferences("local_host", MODE_PRIVATE);
        tab = state == null ? 0 : state.getInt("tab", 0);
        getWindow().setDecorFitsSystemWindows(false);
        render();
    }

    @Override protected void onSaveInstanceState(Bundle state) {
        state.putInt("tab", tab);
        super.onSaveInstanceState(state);
    }

    @Override protected void onStop() {
        handler.removeCallbacksAndMessages(null);
        TermuxBridge.forget(this);
        doctorState.cancel();
        sessionsState.cancel();
        super.onStop();
    }

    @Override protected void onResume() {
        super.onResume();
        if (root != null) render();
    }

    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private GradientDrawable background(int color, int radius) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(color);
        shape.setCornerRadius(dp(radius));
        return shape;
    }

    private LinearLayout column() {
        LinearLayout view = new LinearLayout(this);
        view.setOrientation(LinearLayout.VERTICAL);
        return view;
    }

    private TextView text(String value, int size, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        view.setLineSpacing(dp(3), 1);
        if (bold) view.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        return view;
    }

    private void add(LinearLayout parent, View view, int bottom) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.bottomMargin = dp(bottom);
        parent.addView(view, params);
    }

    private void label(LinearLayout parent, String value) {
        TextView view = text(value, 11, GREEN, true);
        view.setLetterSpacing(0.15f);
        add(parent, view, 12);
    }

    private Button button(String title, boolean primary, Runnable action) {
        Button view = new Button(this);
        view.setText(title);
        view.setAllCaps(false);
        view.setTextSize(15);
        view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        view.setTextColor(primary ? BG : INK);
        view.setBackground(background(primary ? GREEN : LINE, 14));
        view.setMinHeight(dp(52));
        view.setPadding(dp(14), dp(10), dp(14), dp(10));
        view.setOnClickListener(v -> action.run());
        return view;
    }

    private LinearLayout card() {
        LinearLayout box = column();
        box.setPadding(dp(20), dp(20), dp(20), dp(20));
        box.setBackground(background(CARD, 22));
        add(page, box, 18);
        return box;
    }

    private void heading(String eyebrow, String title, String subtitle) {
        label(page, eyebrow);
        add(page, text(title, 32, INK, true), 12);
        add(page, text(subtitle, 16, MUTED, false), 26);
    }

    private void render() {
        root = column();
        root.setBackgroundColor(BG);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            android.graphics.Insets safe = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
            view.setPadding(safe.left, safe.top, safe.right, safe.bottom);
            return WindowInsets.CONSUMED;
        });
        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(24), dp(18), dp(24), dp(16));
        TextView brand = text("◉  OVERTURA", 15, INK, true);
        brand.setLetterSpacing(0.12f);
        header.addView(brand, new LinearLayout.LayoutParams(0, -2, 1));
        TextView edition = text("PIXEL / 0.2", 10, GREEN, true);
        edition.setLetterSpacing(0.08f);
        header.addView(edition);
        root.addView(header);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        page = column();
        page.setPadding(dp(24), dp(20), dp(24), dp(24));
        page.setFocusableInTouchMode(true);
        scroll.addView(page);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        switch (tab) {
            case 1: installPage(); break;
            case 2: sessionsPage(); break;
            case 3: faqPage(); break;
            default: homePage();
        }

        View divider = new View(this);
        divider.setBackgroundColor(LINE);
        root.addView(divider, new LinearLayout.LayoutParams(-1, dp(1)));
        LinearLayout nav = new LinearLayout(this);
        nav.setPadding(dp(12), dp(10), dp(12), dp(10));
        String[] titles = {"Start", "Install", "Sessions", "FAQ"};
        for (int i = 0; i < titles.length; i++) {
            final int destination = i;
            Button item = button(titles[i], i == tab, () -> navigate(destination));
            item.setTextSize(12);
            item.setPadding(dp(4), dp(8), dp(4), dp(8));
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, -2, 1);
            params.setMargins(dp(3), 0, dp(3), 0);
            nav.addView(item, params);
        }
        root.addView(nav);
        setContentView(root);
        root.requestApplyInsets();
    }

    private void navigate(int destination) {
        ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(root.getWindowToken(), 0);
        tab = destination;
        render();
    }

    private void homePage() {
        heading("WORK FROM YOUR POCKET", "Your work,\nwithin reach.", "Leave the heavy lifting on your host. Pick up where you left off from your Pixel.");
        LinearLayout box = card();
        label(box, "THE SHORT VERSION");
        add(box, text("Start. Detach. Return.", 23, INK, true), 12);
        add(box, text("A durable session keeps running when your phone disconnects. Termux gets you back in.", 16, MUTED, false), 20);
        add(box, button("Set up your host  →", true, () -> navigate(1)), 10);
        add(box, button("Open sessions", false, () -> navigate(2)), 0);
        renderDocument("tldr.md", true);
    }

    private void field(LinearLayout box, String title, String key, String hint, String fallback) {
        add(box, text(title, 13, MUTED, true), 6);
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setTextSize(17);
        input.setTextColor(INK);
        input.setHintTextColor(MUTED);
        input.setHint(hint);
        input.setContentDescription(title);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD);
        input.setText(preferences.getString(key, fallback));
        input.setSelectAllOnFocus(true);
        input.setBackground(background(BG, 12));
        input.setPadding(dp(14), dp(14), dp(14), dp(14));
        input.setMinHeight(dp(52));
        input.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) {
                preferences.edit().putString(key, s.toString()).apply();
                if (key.equals("host")) {
                    TermuxBridge.forget(MainActivity.this);
                    doctorState.reset();
                    sessionsState.reset();
                }
            }
            @Override public void afterTextChanged(Editable s) {}
        });
        add(box, input, 16);
    }

    private String host() { return preferences.getString("host", ""); }
    private String session() { return preferences.getString("session", "work"); }

    private void action(String title, String action) {
        try { preview(title, Commands.remote(host(), action, session())); }
        catch (IllegalArgumentException error) { message("Check your details", error.getMessage()); }
    }

    private void installPage() {
        heading("GET CONNECTED", "One host.\nA few small steps.", "Set up Termux on your Pixel and Overtura on your Debian machine.");
        LinearLayout phone = card();
        label(phone, "ON THIS PIXEL · TERMUX");
        add(phone, text("Prepare your SSH connection", 21, INK, true), 10);
        add(phone, text("Install Termux from its official sources. Then run these in a local Termux shell. Keep any existing SSH key.", 14, MUTED, false), 14);
        add(phone, button("1 · Install SSH tools", false, () -> preview("In local Termux", "pkg update && pkg install openssh coreutils")), 10);
        add(phone, button("2 · Create an SSH key", false, () -> preview("In local Termux", "mkdir -p ~/.ssh && chmod 700 ~/.ssh && ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519",
            "Only do this if ~/.ssh/id_ed25519 does not exist. Keep the private key on this phone. Press Enter for a default location and choose a passphrase if you want one.")), 10);
        add(phone, button("3 · Set an SSH alias", false, () -> preview("Example ~/.ssh/config", "Host my-node\n    HostName HOST_ADDRESS\n    User HOST_USER\n    IdentityFile ~/.ssh/id_ed25519\n    IdentitiesOnly yes",
            "Edit ~/.ssh/config in Termux. Replace HOST_ADDRESS and HOST_USER with your own host details. Use an address reachable from this phone. Verify the host key fingerprint with the host owner before accepting it.")), 10);
        add(phone, button("4 · Authorize the public key", false, () -> preview("In local Termux", "ssh-copy-id my-node && ssh my-node",
            "Use your real SSH alias in place of my-node. This requires an existing password login or help from the host owner. Only the public key goes to the host. Never copy the private key.")), 0);
        LinearLayout hostCard = card();
        label(hostCard, "YOUR CONNECTION");
        field(hostCard, "SSH alias in Termux", "host", "my-node", "");
        add(hostCard, text("Use an alias you already connect to in Termux. Keys and addresses stay there.", 14, MUTED, false), 18);
        add(hostCard, button("Connect in Termux", true, () -> {
            try { preview("Connect to your host", Commands.login(host())); }
            catch (IllegalArgumentException error) { message("Check your alias", error.getMessage()); }
        }), 10);
        add(hostCard, button("Run doctor", false, () -> action("Check the host", "doctor")), 0);

        LinearLayout live = card();
        label(live, "OPTIONAL LIVE CHECK");
        add(live, text("Read host diagnostics here", 20, INK, true), 10);
        add(live, text("Runs a read-only SSH query in Termux when you tap. Termux keeps your SSH keys.", 14, MUTED, false), 14);
        add(live, button("Check host now", false, () -> query("doctor")), 12);
        renderQuery(live, doctorState, "doctor");

        LinearLayout install = card();
        label(install, "ON THE DEBIAN HOST");
        add(install, text("Install the base CLI", 23, INK, true), 12);
        add(install, text("Run these on the Debian host, at its console if SSH is not ready yet. The installer uses your regular account; only distribution packages and SSH service setup need sudo.", 15, MUTED, false), 18);
        add(install, button("1 · Dependency command", false, () -> previewHost("Install dependencies", "sudo apt-get install python3 tmux git openssh-server")), 10);
        add(install, button("Optional · Start host SSH", false, () -> previewHost("Start SSH server", "sudo systemctl enable --now ssh")), 10);
        add(install, button("2 · Clone the source", false, () -> previewHost("Clone Overtura", "git clone https://github.com/hanenashi/overtura.git")), 10);
        add(install, button("3 · Install and check", true, () -> previewHost("Install Overtura", "cd overtura && python3 install.py && \"$HOME/.local/bin/overtura\" setup && \"$HOME/.local/bin/overtura\" doctor")), 0);
        renderDocument("install.md", true);
        LinearLayout automation = card();
        label(automation, "OPTIONAL LIVE CHECKS");
        add(automation, text("Enable Termux queries", 20, INK, true), 10);
        add(automation, text("For live Doctor and Sessions, allow “Run commands in Termux” in Android app permissions. In Termux, edit ~/.termux/termux.properties and set allow-external-apps=true. Restart Termux. Use a current Termux release. This also allows other apps you grant that permission to run Termux commands.", 14, MUTED, false), 0);
        add(page, button("Termux project ↗", false, () -> browse("https://github.com/termux/termux-app#installation")), 10);
        add(page, button("Overtura APK releases ↗", false, () -> browse("https://github.com/hanenashi/overtura/releases")), 10);
        add(page, button("Overtura source ↗", false, () -> browse("https://github.com/hanenashi/overtura")), 0);
    }

    private void sessionsPage() {
        heading("PICK UP YOUR WORK", "Your sessions.", "Prepare a command here. Run it in Termux, where your live terminal belongs.");
        LinearLayout box = card();
        field(box, "SSH alias in Termux", "host", "my-node", "");
        field(box, "Session name", "session", "work", "work");
        add(box, button("Reattach  →", true, () -> action("Return to your session", "attach")), 10);
        add(box, button("Create a shell session", false, () -> action("Create a new session", "create")), 10);
        add(box, button("List sessions", false, () -> action("List host sessions", "list")), 0);
        LinearLayout live = card();
        label(live, "OPTIONAL LIVE LIST");
        add(live, text("See sessions on your host", 20, INK, true), 10);
        add(live, button("Refresh live list", false, () -> query("session.list")), 12);
        renderQuery(live, sessionsState, "session.list");
        LinearLayout tip = card();
        label(tip, "LEAVE IT RUNNING");
        add(tip, text("Ctrl+b  then  d", 23, INK, true), 12);
        add(tip, text("Detach before closing Termux. If the connection drops, the host session still continues. Reattach using the same name.", 15, MUTED, false), 0);
        add(page, text("Create and attach still open your terminal in Termux.", 13, MUTED, false), 0);
    }

    private QueryState stateFor(String operation) {
        return operation.equals("doctor") ? doctorState : sessionsState;
    }

    private void query(String operation) {
        String alias;
        try { alias = Commands.alias(host()); }
        catch (IllegalArgumentException error) { message("Check your alias", error.getMessage()); return; }
        if (getPackageManager().getLaunchIntentForPackage("com.termux") == null) {
            message("Install Termux first", "Use the Install page to set up Termux and OpenSSH, then try again.");
            return;
        }
        if (checkSelfPermission(RUN_COMMAND) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{RUN_COMMAND}, 43);
            return;
        }
        QueryState state = stateFor(operation);
        long token = state.begin(alias, operation, SystemClock.elapsedRealtime());
        try { TermuxBridge.start(this, alias, operation, token); }
        catch (RuntimeException error) {
            state.fail(token, ApiReply.FailureKind.TERMUX_SETUP, SystemClock.elapsedRealtime());
        }
        render();
        handler.postDelayed(() -> {
            QueryState current = stateFor(operation);
            current.expire(SystemClock.elapsedRealtime());
            TermuxBridge.forget(this, operation, token);
            if (tab == (operation.equals("doctor") ? 1 : 2)) render();
        }, QueryState.TIMEOUT_MS);
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grants) {
        super.onRequestPermissionsResult(requestCode, permissions, grants);
        if (requestCode == 43) {
            message(grants.length > 0 && grants[0] == PackageManager.PERMISSION_GRANTED
                    ? "Permission ready" : "Permission needed",
                "Run commands in Termux permission is needed for live checks. You can always use Copy + Termux. See the Install page for Termux's allow-external-apps setting.");
        }
    }

    void onTermuxResult(String operation, long token, Intent intent) {
        QueryState state = stateFor(operation);
        long now = SystemClock.elapsedRealtime();
        try {
            Bundle result = intent.getBundleExtra("result");
            TermuxReply reply = result == null ? TermuxReply.from(false, 0, false, 0, null, null)
                : TermuxReply.from(result.containsKey("err"), result.getInt("err"),
                    result.containsKey("exitCode"), result.getInt("exitCode"),
                    result.getString("stdout"), result.get("stdout_original_length"));
            if (reply.failure == null) state.complete(token, reply.exitCode, reply.stdout, now);
            else state.fail(token, reply.failure, now);
        } catch (RuntimeException error) {
            state.fail(token, ApiReply.FailureKind.MALFORMED, now);
        }
        if (tab == (operation.equals("doctor") ? 1 : 2)) render();
        if (state.snapshot() != null && !state.isStale(SystemClock.elapsedRealtime())) {
            handler.postDelayed(() -> {
                if (tab == (operation.equals("doctor") ? 1 : 2)) render();
            }, QueryState.FRESH_MS);
        }
    }

    private void renderQuery(LinearLayout box, QueryState state, String operation) {
        long now = SystemClock.elapsedRealtime();
        boolean stale = state.isStale(now);
        switch (state.status()) {
            case IDLE: add(box, text(stale ? "Previous result · out of date" : "Tap to check the host.", 14, MUTED, false), 10); break;
            case LOADING: add(box, text("Checking…", 14, GREEN, true), 10); break;
            case READY: add(box, text(stale ? "Last result · out of date" : "Updated just now", 14, GREEN, true), 10); break;
            case NEEDS_ATTENTION: add(box, text(stale ? "Previous check · out of date" : "Host needs attention", 14, INK, true), 10); break;
            case ERROR:
                String problem = state.failure() != null ? state.failure().getMessage()
                    : "The host query failed (" + state.remoteError() + "). Check setup in Termux.";
                add(box, text(problem, 14, INK, false), 10);
                if (stale) add(box, text("Previous result below · out of date", 13, MUTED, false), 10);
                break;
        }
        ApiReply reply = state.snapshot();
        if (reply == null) return;
        if (operation.equals("doctor")) {
            for (ApiReply.Check check : reply.checks) {
                add(box, text(check.status.toUpperCase(Locale.ROOT) + " · " + check.message, 14,
                    check.status.equals("fail") ? INK : MUTED, false), 7);
            }
        } else if (reply.sessions.isEmpty()) {
            add(box, text("No sessions on this host.", 14, MUTED, false), 0);
        } else {
            for (ApiReply.Session session : reply.sessions) {
                String description = session.name + " · " + session.windows + " window(s) · "
                    + session.attachedClients + " attached";
                if (!session.attachable) description += " · use tmux for this name";
                add(box, text(description, 14, INK, false), 9);
            }
        }
    }

    private void faqPage() {
        heading("GOOD TO KNOW", "Small answers.\nLess guesswork.", "The essentials, saved on your phone and available offline.");
        renderDocument("faq.md", true);
    }

    private void renderDocument(String filename, boolean skipTitle) {
        try (InputStream stream = getAssets().open(filename)) {
            String source = new String(stream.readAllBytes(), StandardCharsets.UTF_8);
            for (String block : source.split("\\n\\s*\\n")) {
                block = block.trim();
                if (block.isEmpty() || (skipTitle && block.startsWith("# "))) continue;
                if (block.startsWith("## ")) {
                    TextView title = text(block.substring(3), 19, INK, true);
                    title.setPadding(0, dp(8), 0, 0);
                    add(page, title, 8);
                } else {
                    add(page, text(block, 15, MUTED, false), 18);
                }
            }
        } catch (IOException error) {
            add(page, text("This guide could not be loaded. Reinstall the app or read the repository documentation.", 15, MUTED, false), 12);
        }
    }

    private void previewHost(String title, String command) {
        preview(title + " · on the host", command, "Run this in a Debian host shell: at its console, or in Termux AFTER logging in to that host. It is not a phone-side command.");
    }

    private void preview(String title, String command) {
        preview(title, command, "Paste into a local Termux shell and press Enter. If you are already SSH'd into a host, open another Termux session first.");
    }

    private void preview(String title, String command, String explanation) {
        LinearLayout content = column();
        content.setPadding(dp(24), dp(12), dp(24), dp(8));
        add(content, text(explanation, 15, MUTED, false), 18);
        TextView code = text(command, 14, INK, false);
        code.setTypeface(Typeface.MONOSPACE);
        code.setTextIsSelectable(true);
        code.setPadding(dp(14), dp(14), dp(14), dp(14));
        code.setBackground(background(BG, 12));
        add(content, code, 12);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(content);
        new AlertDialog.Builder(this).setTitle(title).setView(scroll)
            .setPositiveButton("Copy + Termux", (dialog, which) -> { copy(command); openTermux(); })
            .setNeutralButton("Copy", (dialog, which) -> copy(command))
            .setNegativeButton("Cancel", null).show();
    }

    private void copy(String command) {
        ClipboardManager clipboard = (ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
        clipboard.setPrimaryClip(ClipData.newPlainText("Overtura command", command));
        Toast.makeText(this, "Copied. Paste in Termux to run.", Toast.LENGTH_SHORT).show();
    }

    private void openTermux() {
        Intent launch = getPackageManager().getLaunchIntentForPackage("com.termux");
        if (launch == null) {
            message("Termux is needed", "Your command was copied. Install Termux using the project link on the Install page, then paste the command there.");
            return;
        }
        try { startActivity(launch); }
        catch (ActivityNotFoundException error) { message("Could not open Termux", "Your command was copied. Open Termux yourself and paste it."); }
    }

    private void browse(String url) {
        try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); }
        catch (ActivityNotFoundException error) { message("No browser available", "Open the project documentation from a device with a browser."); }
    }

    private void message(String title, String body) {
        new AlertDialog.Builder(this).setTitle(title).setMessage(body).setPositiveButton("OK", null).show();
    }
}
