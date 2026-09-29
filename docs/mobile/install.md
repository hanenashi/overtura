# From a new Pixel to a running session

## 1. Download Termux on your Pixel

Termux is a terminal app: a place to type commands on your phone. Overtura uses
it to connect to a Debian computer, called your host. You need internet access
for downloads and a reachable host for SSH.

For a first installation, open https://f-droid.org/packages/com.termux/ using
Get Termux through F-Droid in Overtura. Choose Download F-Droid, install and
open that app, and let its catalogue load. Search for Termux and install it.
F-Droid is the app store; Termux is the app you need from it. If Android asks,
allow installations from the browser or F-Droid you are using, then return to
the installer. Button names can vary.

Already have Termux? Keep it and update from the same source. Termux and its
plugins must come from the same source because their signing keys differ.
Do not uninstall it just to switch sources: uninstalling can remove its files
and keys. Other official options: https://github.com/termux/termux-app#installation.
Termux:API and shared-storage access are not required for this setup.

If using GitHub releases on a Pixel, expand Assets and choose the APK whose
name ends in arm64-v8a.apk. The universal APK also works but is a larger
download. Source code archives are not installable apps. Open the downloaded
APK and tap Install, then Open.

OverturaApp requires Android 15 or newer. Get its APK from the project's GitHub
releases when a tested build is published, or build it from source.

## 2. Open Termux for the first time

Open Termux and wait for its initial setup to finish. A welcome message and a
line ending in $ usually mean it is ready. This is the shell prompt: the cursor
marks where you type. Do not type the $ itself.

Type echo 'Termux is ready' and press Enter on the keyboard. You should see
Termux is ready and another prompt. Or use Try a first command in Overtura:
tap Copy + Termux, long-press by the cursor, tap Paste, and press Enter.
Return to Overtura through Android's recent apps. Copy + Termux only copies
text and opens the app; you run the command yourself.

Phone commands belong in a local Termux shell. If you are already connected
to a host over SSH, type exit to return to the phone, or swipe from Termux's
left edge and choose NEW SESSION. Commands labelled ON THE DEBIAN HOST belong
on the computer, at its console or after connecting through SSH.

## 3. Install the phone tools

In local Termux, run pkg update && pkg install openssh coreutils nano.
OpenSSH provides connection tools, coreutils provides a time limit for live
queries, and Nano is a text editor. When asked to continue, type y and press
Enter. Wait for the prompt to return without errors.

Run ssh -V. A line starting with OpenSSH confirms the client is installed;
it does not connect to a host yet. If downloads fail, check your internet
connection and try again. For persistent mirror errors, use termux-change-repo
to choose another offered main repository mirror, then retry.

## 4. Get the host ready

Ask the host owner for its reachable address, your username, its SSH host-key
fingerprint, and how to authorize your phone. These are the computer's details,
not your Android account. A password login or the owner's help is needed to
install your public key. Use an address reachable from the phone, on the same
LAN or through a private network already configured on both devices.

If the host is not ready, follow ON THE DEBIAN HOST in the Install page at the
computer's console. Its buttons install Python 3, tmux, Git and openssh-server,
start SSH on a Debian systemd host, and clone and install Overtura. Overtura
does not configure a firewall or SSH accounts.

Inspect the cloned source and run python3 install.py as your regular user,
then ~/.local/bin/overtura setup and ~/.local/bin/overtura doctor. Setup creates
private configuration and refuses to replace an existing file. If the workspace
is missing, edit ~/.config/overtura/config.toml and point host.workspace to an
existing directory. Only package installation and SSH service setup need sudo.

## 5. Create a key and an SSH nickname

Already have working SSH access in Termux? Keep it and skip to Connect.
Otherwise run ssh-keygen -t ed25519 in local Termux. Press Enter for the default
file location. If asked to overwrite an existing key, answer n and stop. Choose
a passphrase and repeat it, or press Enter twice to leave it empty. Password
and passphrase typing is invisible; no dots is normal.

The private key stays on this phone. Only the file ending in .pub may be sent
to the host owner. Never send the file without .pub.

Use Open the SSH alias file in Overtura to open Nano. Leave the editor open,
return to Overtura, and use Copy an alias example. Paste that text into Nano,
not at a shell prompt. Preserve existing entries. Replace HOST_ADDRESS and
HOST_USER with your host details. my-node is a nickname you choose; use the
same nickname in Overtura. Adjust IdentityFile if you use another key file.

You can keep my-node literally as the nickname. HostName is the Debian
computer's address, not the phone's address; User is your account on that
computer. A local Wi-Fi address works while both devices can reach each other
on that network. Access away from home needs a separately configured network
route, such as Tailscale. A local address may change unless reserved in the router.

Save in Nano with Ctrl+O followed by Enter, then exit with Ctrl+X. Termux's
extra keyboard row has a CTRL key: tap it, then the letter.

## 6. Authorize the key and connect

Run ssh-copy-id my-node in local Termux, replacing my-node if you chose another
nickname. Before answering yes to a new host-key prompt, compare its fingerprint
with the one supplied by the owner. Enter your account password on the host
when asked. If password login is unavailable, ask the owner to add your public
key to that account's ~/.ssh/authorized_keys.

In Overtura, enter the nickname under YOUR CONNECTION and tap Connect in Termux.
Paste and run the command. A host prompt means you have connected. Run whoami
to check the account you are using. Type exit to return to the phone. A host-key
mismatch needs investigation with the owner; do not remove the saved key simply
to make the warning disappear.

Permission denied usually means the username, key, or authorization needs
checking. Could not resolve hostname means check the nickname and HostName.
Connection refused or a timeout means check the address, network, and host SSH
service. Get this connection working before enabling live checks.

## 7. Start and return

In Sessions, enter your SSH nickname and a session name such as work. Choose
Create a shell session, review the command, then copy it to Termux and run it.
Detach with Ctrl+b followed by d, and use Reattach to return.

## Optional: show live results in Overtura

Manual Copy + Termux works without this step. Use Open Termux settings file
in the Install page. In Nano, set allow-external-apps=true on its own line in
~/.termux/termux.properties. Replace any existing value and remove a leading #
if present; preserve other settings. Save with Ctrl+O, Enter, then exit with
Ctrl+X. Run termux-reload-settings in local Termux.

Back in Overtura, tap Check host now and grant Run commands in Termux when
Android asks. Tap Check host now again. If needed, find this permission in
Android Settings, Apps, Overtura, Permissions; it may be under Additional
permissions. Enabled apps with this permission can run Termux commands.
SSH keys remain in Termux.

A healthy report is labelled Updated just now. Refresh live list should show
your sessions, or No sessions yet if none exist. If a check fails, diagnose it
in Termux. Host CLI 0.2.0 or newer is needed for JSON results. Stale results
are labelled and should not be taken as current. Passphrase-protected keys may
need unlocking in a Termux SSH agent; use manual commands if a prompt is needed.

## Updates

Update the checkout and run python3 install.py --upgrade on the host. Private
configuration and running sessions are preserved.
