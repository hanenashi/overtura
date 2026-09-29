# OverturaApp

A native Android companion for Pixel, supporting Android 15 and newer. It uses
platform views and no runtime libraries. Offline guides come from `docs/mobile`.

The initial build has Start, Install, Sessions and FAQ pages. An SSH alias and
session name are stored in app-private preferences with backups disabled. Actions
preview a command, copy it, and optionally open Termux. The user pastes and runs
the command; no background command execution is requested. Installation snippets
explicitly distinguish commands to run on the Debian host from local Termux SSH
commands. The app requires no Android permissions and never reads SSH keys or
terminal output.

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

The initial preview was verified on an Android 15 emulator and a Pixel running
Android 17. The emulator covered the missing-Termux fallback; the Pixel covered
the real app handoff. The build, three command unit tests and Android lint pass.
The Pixel's SSH route also passed a separate read-only host doctor check. The
app itself does not execute or capture that diagnostic.

## JSON consumer foundation

`ApiReply`, `QueryState`, and `Commands.readOnlyQuery` prepare read-only host
queries without changing the Activity or requesting execution permissions.
The [v1 protocol boundary](../docs/protocol-v1.md) documents validation, stale
results, deadlines, and responsibilities for the later Termux transport.
Shared fixtures in `tests/fixtures/protocol-v1` run in both Python and JVM tests.
The JVM org.json dependency is test-only; runtime uses Android's platform decoder.
Run the build command above for unit tests, lint and APK assembly without ADB.
