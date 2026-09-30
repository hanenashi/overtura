# Reusable phone lab

The `lab` build installs as **Overtura Lab**, with package ID
`io.github.hanenashi.overtura.lab`. It has its own preferences and Termux command
permission and can be reset without clearing the normal Overtura app.

It uses the existing Termux installation in Android user 0. Phone packages,
Termux's `allow-external-apps` setting, terminal sessions and clipboard are
shared. This does **not** simulate downloading Termux or its first bootstrap.
Stock Termux requires the primary Android user because packages use fixed
paths; a secondary user or work profile cannot provide a fresh Termux lab.
Use an emulator or spare phone for that part of onboarding. See the official
[Termux execution environment](https://github.com/termux/termux-packages/wiki/Termux-execution-environment).

## Set up

Prerequisites: the Android build tools, ADB paired with the intended phone,
working SSH **into that same phone's Termux**, Python in Termux, and the
[rootless Debian lab](../tests/lab/README.md) prerequisites on the developer host.
Run from the repository root:

```sh
python3 android/phone_lab.py up --serial DEVICE --phone-ssh PHONE_SSH_ALIAS
```

This builds and installs the separate app, preserves or starts the existing
Debian lab, installs its CLI, and connects phone loopback port 22333 to the
host's loopback-only lab SSH port 22222 through ADB reverse forwarding. It
does not reset the Debian container or remove existing test sessions. An
existing container retains its copied source; rebuild it explicitly when host
source changes need testing.

The helper adds a marked `overtura-phone-lab` block to Termux's SSH config,
preserving unrelated text and existing config symlinks. Its files live under
`~/.ssh/overtura-phone-lab` with an ownership marker. It copies only the dedicated
Debian-lab test key, never a personal SSH key. The test host key is obtained
through Podman, not accepted from an unauthenticated network scan. The alias
disables agent forwarding, proxy routes and interactive host-key acceptance.

Open **Overtura Lab**, enter **overtura-phone-lab** as the SSH alias, and use
Doctor, session create and reattach against the container. Grant the lab app's
Run commands in Termux permission when you want live checks. Its permission is
separate from the normal app's; the helper does not grant it automatically.

Keep ADB connected for this route. After a disconnect or port change, run:

```sh
python3 android/phone_lab.py connect --serial DEVICE --phone-ssh PHONE_SSH_ALIAS
```

## Reset and cleanup

```sh
python3 android/phone_lab.py reset --serial DEVICE
python3 android/phone_lab.py status --serial DEVICE
```

`reset` clears only Overtura Lab's saved settings and command permission, then
opens its first screen. The Termux alias and Debian lab remain ready for reuse.
It does not erase Termux data or the normal Overtura app. `status` reports app
installation; `connect` verifies the actual SSH route and host Doctor result.

For a fresh host, inspect the Debian lab for test work first, then explicitly
use `tests/lab/lab.py reset` and reconnect the phone lab. Host reset destroys
that container's files and sessions, so it is not part of the phone app reset.

To remove the lab app, owned SSH files/config block and ADB forwarding:

```sh
python3 android/phone_lab.py remove --serial DEVICE --phone-ssh PHONE_SSH_ALIAS
```

The Debian container is managed independently and is retained. Do not edit the
managed SSH block; cleanup preserves edits elsewhere in the configuration.

## Repeatable tests

Both existing device runners can target the separate app explicitly:

```sh
python3 android/smoke.py --serial DEVICE --lab
python3 android/reliability.py --serial DEVICE --phone-ssh PHONE_SSH_ALIAS --lab
```

Without `--lab` they retain their original normal-app target. The smoke runner
uses the shared clipboard and opens Termux without executing its copied command.
Its lab-targeted navigation and cleanup still need a follow-up check. The
reliability runner requires saved app settings, temporarily adds its own fixture
SSH alias and restores it afterward. Run it after entering an alias or after
the smoke runner has populated preferences.

Local checks:

```sh
python3 -m unittest discover -s android -p 'test_phone_lab.py' -v
cd android
./gradlew testDebugUnitTest lintDebug assembleDebug testLabUnitTest lintLab assembleLab
```
