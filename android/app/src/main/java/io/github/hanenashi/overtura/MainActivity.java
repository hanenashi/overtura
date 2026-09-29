package io.github.hanenashi.overtura;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
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
        TextView edition = text("PIXEL / 0.1", 10, GREEN, true);
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
        LinearLayout hostCard = card();
        label(hostCard, "YOUR CONNECTION");
        field(hostCard, "SSH alias in Termux", "host", "my-node", "");
        add(hostCard, text("Use an alias you already connect to in Termux. Keys and addresses stay there.", 14, MUTED, false), 18);
        add(hostCard, button("Connect in Termux", true, () -> {
            try { preview("Connect to your host", Commands.login(host())); }
            catch (IllegalArgumentException error) { message("Check your alias", error.getMessage()); }
        }), 10);
        add(hostCard, button("Run doctor", false, () -> action("Check the host", "doctor")), 0);

        LinearLayout install = card();
        label(install, "ON THE DEBIAN HOST");
        add(install, text("Install the base CLI", 23, INK, true), 12);
        add(install, text("Run these on the host after SSH login. The installer uses your regular account; only distribution packages need sudo.", 15, MUTED, false), 18);
        add(install, button("1 · Dependency command", false, () -> previewHost("Install dependencies", "sudo apt-get install python3 tmux git")), 10);
        add(install, button("2 · Clone the source", false, () -> previewHost("Clone Overtura", "git clone https://github.com/hanenashi/overtura.git")), 10);
        add(install, button("3 · Install and check", true, () -> previewHost("Install Overtura", "cd overtura && python3 install.py && \"$HOME/.local/bin/overtura\" setup && \"$HOME/.local/bin/overtura\" doctor")), 0);
        renderDocument("install.md", true);
        add(page, button("Termux project ↗", false, () -> browse("https://github.com/termux/termux-app#installation")), 10);
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
        LinearLayout tip = card();
        label(tip, "LEAVE IT RUNNING");
        add(tip, text("Ctrl+b  then  d", 23, INK, true), 12);
        add(tip, text("Detach before closing Termux. If the connection drops, the host session still continues. Reattach using the same name.", 15, MUTED, false), 0);
        add(page, text("This app does not read session status. Your real list and diagnostics appear in Termux.", 13, MUTED, false), 0);
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
        preview(title + " · on the host", command, "Paste this into Termux only AFTER logging in to the Debian host. It is not a phone-side command.");
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
