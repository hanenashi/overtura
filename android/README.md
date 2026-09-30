# OverturaApp

A native Android companion for Pixel, supporting Android 15 and newer. It uses
platform views and no runtime libraries. Offline guides come from `docs/mobile`.

The app has Start, Install, Sessions and FAQ pages. An SSH alias and session
name are stored in app-private preferences with backups disabled. Manual actions
preview a command, copy it, and optionally open Termux for the user to run it.
The Install page starts with getting Termux through F-Droid, opening it once,
and trying a harmless first command. It then explains phone tools, SSH keys,
editing aliases in Nano, host setup and the optional live query permission.
Commands identify whether they belong on the phone or the Debian host.
Each tab keeps its scroll position while the app stays open, including when
live results refresh or the user returns from Termux. Android also restores
the positions when recreating the Activity from saved state.

Live Doctor and Sessions queries use Termux's RUN_COMMAND interface only when
tapped. They run SSH in the background and show validated JSON results with
freshness and failure states. The Android app never reads SSH keys or takes
ownership of host verification. Termux's `com.termux.permission.RUN_COMMAND`
permission and `allow-external-apps=true` setting are both required; manual
copy/open actions remain available. Live Doctor and Sessions refreshes have
passed an initial Pixel smoke test; see the coverage and gaps below.

The current 0.3.0-dev source lets users tap a fresh, attachable session in the
live list to preview its exact reattach command, then copy it into Termux.
Stale rows require a refresh, and names outside the CLI's attachable name rules
are displayed without a reattach action. The typed session-name field and
manual command preview remain available. Local JVM tests, lint, and build pass;
on-device use of the new row control is pending.

The Install page also has an explicit, read-only phone-tool check. When tapped,
it asks Termux whether `ssh`, `timeout`, and `nano` are available and shows any
missing tool beside the existing manual install command. It needs Termux's
RUN_COMMAND permission and external-app setting; it does not inspect SSH keys
or connect to a host. Manual setup remains available. Device verification of
this new check is pending.

## Build

Install JDK 17 or newer, Android SDK platform 36 and build tools. Set ANDROID_HOME
to your SDK location, then from this directory:

```sh
./gradlew testDebugUnitTest lintDebug assembleDebug
```

The debug APK is `app/build/outputs/apk/debug/app-debug.apk`. The Gradle wrapper
pins Gradle 8.11.1; Android Gradle Plugin is pinned to 8.9.2. Debug signing uses the
local Android debug keystore, which must never be committed.

Install on a connected, authorized Pixel:

```sh
adb -s DEVICE install -r app/build/outputs/apk/debug/app-debug.apk
adb -s DEVICE shell am start -n io.github.hanenashi.overtura/.MainActivity
```

Keep actual device IDs, SDK paths, APKs, screenshots and signing keys out of Git.
See `docs/android-app.md` for the implementation boundary and next milestones.

## Device smoke test

With the app already installed on a dedicated or available test device:

```sh
python3 smoke.py --serial DEVICE
```

This navigates the app, checks input validation and command previews, verifies
settings survive a restart, and tests either the Termux handoff or its missing-app
fallback. It temporarily edits the app fields and restores them, leaves a sample
command in the clipboard, and returns to Start. It never executes that command
or reads Termux terminal contents. Screenshots stay in a temporary directory
outside the repository.

The original manual-command preview was verified on an Android 15 emulator and
a Pixel running Android 17. The emulator covered the missing-Termux fallback;
the Pixel covered the real app handoff. The 0.2.0 debug APK was then installed
on the Pixel running Android 17. After granting Termux's command permission and
enabling `allow-external-apps=true`, live Doctor showed a ready host and live
Sessions listed an existing session. Changing the SSH alias to a deliberately
unreachable one showed the connection error; restoring the working alias and
refreshing showed the session again. The host CLI was upgraded to 0.2.0 and
its JSON Doctor output was checked separately in Termux.

## Live query transport

`ApiReply`, `QueryState`, and `TermuxBridge` power read-only host queries.
Termux version 0.109 or newer is needed for result callbacks. The query runs
under an 18-second Termux `timeout` (provided by `coreutils`), with a 20-second
app deadline. Results over 256 KiB or truncated by Termux are rejected.
The [v1 protocol boundary](../docs/protocol-v1.md) documents response validation.
Shared fixtures in `tests/fixtures/protocol-v1` run in both Python and JVM tests.
The JVM org.json dependency is test-only; runtime uses Android's platform decoder.
Run the build command above for unit tests, lint and APK assembly. The Pixel
smoke test confirms permission grant and successful/error callback delivery.
The additional reliability checks below cover denied permission, failed Doctor
and older-CLI response fixtures, timeouts, cancellation, and process recreation.

On 2026-09-30, the expanded beginner guide was used in an assisted fresh-phone
walkthrough on a second Pixel. Overtura was installed through ADB; Termux was
obtained through its GitHub release route. SSH key authorization, manual login,
Doctor, session creation, detach/reattach, live Doctor and live session listing
all passed over local Wi-Fi to an existing configured Debian host. The user
received help choosing the Termux APK and filling in the SSH alias.

This verifies the assisted setup path, not an unaided beginner walkthrough,
the F-Droid installation route, a fresh Debian host, or access away from the
local network. The updated automated smoke script has not been rerun on a
device. Local validation passed 23 JVM tests, lint and debug APK assembly.

The scroll-position fix was installed on a Pixel and checked after a current-tab
tap, app resume, tab switch, and live session-list refresh. JVM tests, lint and
debug APK assembly passed for the fix.

## ADB reliability checks

With the debug app already configured on an authorized test Pixel, Termux SSH
access available from this computer, and Termux live queries enabled:

```sh
python3 reliability.py --serial DEVICE --phone-ssh PHONE_SSH_ALIAS
```

Run this on Linux with Python 3, ADB, OpenSSH client tools and `/usr/sbin/sshd`.
Both arguments must identify the same phone. The runner starts an unprivileged
SSH server bound to localhost, with throwaway keys and a forced fixture command.
An ADB reverse forward makes it reachable from Termux. It temporarily changes
the app's saved alias and command permission, and prepends a test SSH alias to
Termux's configuration. Cleanup restores app preferences, permission flags and
the original SSH configuration, removes the forward and keys, and stops the
test server. If cleanup fails, it reports the remaining recovery backups.
Terminal contents and production SSH keys are never read.

The 0.2.1 candidate passed on a Pixel running Android 17:

- Denied permission prevented SSH; manual command preview remained available.
- Failed Doctor data was displayed as needing attention.
- An empty exit-2 reply displayed the older-CLI/update message.
- A sleeping fixture reached the transport timeout; the next request recovered.
- Leaving the app invalidated the pending result and ignored a late callback.
- Background process death and recreation restored the tab and scroll position
  while clearing transient host results.
- Query refreshes preserved the visible scroll position.

These are real Termux/SSH/callback checks with controlled response fixtures,
not installations of old CLI releases or failures on a production host. Rotation,
permission revocation during a query and other Android versions are not covered.
