# OverturaApp 0.2.1 — Pixel preview

Live host diagnostics and session lists now work through optional Termux
queries. The beginner guide starts with downloading Termux, opening it for the
first time, and preparing SSH. Pages keep their scroll positions when you
return from Termux, switch tabs or refresh results.

## Install

Download `Overtura-0.2.1-debug.apk` and open it on Android 15 or newer. This is a
debug-signed preview for testing. Existing previews signed with the same key can
be updated without uninstalling. The matching `.sha256` file checks the download.

Termux handles SSH and credentials. Use host CLI 0.2.0 for live JSON queries;
the CLI and protocol-v1 format have not changed in this app release. Manual
copy/open-Termux commands remain available. Live checks need Termux's command
permission, `allow-external-apps=true`, OpenSSH and coreutils. Create and attach
continue through the interactive Termux terminal.

## Verification

- 23 Android JVM tests, Android lint and debug APK assembly passed.
- An assisted setup on a second Pixel passed SSH authorization/login, manual
  Doctor, session creation, detach/reattach, live Doctor and live session listing.
- The ADB reliability runner passed on a Pixel running Android 17. It checked
  permission denial, failed Doctor data, an older CLI's empty exit-2 reply,
  transport timeout and recovery, background cancellation and late callbacks,
  and restoration after Android process death.
- Scroll position survived app resume, tab switching and live refreshes. Process
  recreation restored navigation and scroll without claiming fresh host results.

Failure cases used a temporary localhost SSH server and controlled responses
through the real Termux transport. They did not alter a production host or
install historical CLI releases. The runner restored the phone's saved alias,
Termux permission and SSH configuration afterward.

## Remaining checks

F-Droid installation, an unaided beginner setup, access away from the local
network, screen rotation, permission revocation during a request, and other
Android versions are not covered by this device pass. The app provides no
embedded terminal or automatic session creation.

The repeatable commands and boundaries are in `android/README.md` and
`docs/protocol-v1.md` in the source repository.
