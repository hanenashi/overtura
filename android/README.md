# OverturaApp

A native Android companion for Pixel, supporting Android 15 and newer. It uses
platform views and no runtime libraries. Offline guides come from `docs/mobile`.

The app has Start, Install, Sessions and FAQ pages. An SSH alias and session
name are stored in app-private preferences with backups disabled. Manual actions
preview a command, copy it, and optionally open Termux for the user to run it.
The Install page guides a fresh Pixel through dependencies, SSH keys, aliases,
host setup and the optional live query permission.

Live Doctor and Sessions queries use Termux's RUN_COMMAND interface only when
tapped. They run SSH in the background and show validated JSON results with
freshness and failure states. The Android app never reads SSH keys or takes
ownership of host verification. Termux's `com.termux.permission.RUN_COMMAND`
permission and `allow-external-apps=true` setting are both required; manual
copy/open actions remain available. The current source has not yet passed
on-device validation of this new transport.

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
the Pixel covered the real app handoff. The new live-query build has not yet
been installed or tested on a device.

## Live query transport

`ApiReply`, `QueryState`, and `TermuxBridge` power read-only host queries.
Termux version 0.109 or newer is needed for result callbacks. The query runs
under an 18-second Termux `timeout` (provided by `coreutils`), with a 20-second
app deadline. Results over 256 KiB or truncated by Termux are rejected.
The [v1 protocol boundary](../docs/protocol-v1.md) documents response validation.
Shared fixtures in `tests/fixtures/protocol-v1` run in both Python and JVM tests.
The JVM org.json dependency is test-only; runtime uses Android's platform decoder.
Run the build command above for unit tests, lint and APK assembly. Permission,
callback and lifecycle behavior still need Pixel verification before releasing
this app build.
