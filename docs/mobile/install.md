# From a new Pixel to a running session

## 1. Install the phone apps

Get OverturaApp from this project's GitHub releases when a tested APK is
published. OverturaApp currently requires Android 15 or newer. Install Termux
from its official F-Droid or GitHub source. Use one
source for Termux and any Termux plugins; their signing keys differ. A recent
Termux release is needed for live checks. Termux:API is not needed.

## 2. Prepare Termux SSH

In a local Termux shell run `pkg update && pkg install openssh coreutils`.
If you have no SSH key yet, use `ssh-keygen -t ed25519` and keep the private
key on your phone. Add an alias such as `my-node` to `~/.ssh/config` with your
own HostName, User and IdentityFile. Never put those values in this project.
Use a host address reachable from this phone, such as on the same LAN or
through a private network you have already configured on both devices.
Verify the host fingerprint with its owner before accepting it.

Authorize the public key with `ssh-copy-id my-node` if your host allows a
password login. Otherwise, ask its owner to add the contents of
`~/.ssh/id_ed25519.pub` to the host user's `~/.ssh/authorized_keys`.
Do not share `~/.ssh/id_ed25519`. Confirm `ssh my-node` works before continuing.

## 3. Prepare the Debian host

The host needs Python 3.11 or newer, tmux, Git and SSH server access. The
Install page offers copyable commands to install Debian packages and Overtura.
Use the host's console if SSH is not running yet; Overtura does not configure
the SSH server or open a firewall. On a Debian host with systemd, you can
start its SSH service with `sudo systemctl enable --now ssh` after installing
`openssh-server`.

Clone the public repository on the host, inspect it, and run `python3
install.py` as your regular user. Then run `~/.local/bin/overtura setup` and
`~/.local/bin/overtura doctor`. Edit `~/.config/overtura/config.toml` and
point `host.workspace` to an existing directory. Setup never replaces it.

## 4. Start and return

In OverturaApp, enter the same SSH alias you use in Termux. The Doctor and
Sessions buttons can copy a command for you to paste manually. Create a shell
session, detach with Ctrl+b then d, and use Reattach to return.

Live read-only checks are optional. Grant OverturaApp "Run commands in Termux"
in Android app permissions. In Termux set `allow-external-apps=true` in
`~/.termux/termux.properties` and run `termux-reload-settings` (or restart
Termux). Then tap Check host now or Refresh live list. Only grant this
permission to apps you trust: enabled apps can run commands in Termux. SSH
keys remain in Termux.

If a live check fails, use the manual command to diagnose SSH or Termux setup.
Older host CLI releases do not provide JSON; upgrade the host CLI for live
results. A stale result is labelled as such and should not be taken as current.

## Updates

Update the checkout and run `python3 install.py --upgrade` on the host. The
CLI is replaced while private configuration and running sessions are preserved.
