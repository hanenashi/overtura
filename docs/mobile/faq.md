# A few useful answers

## Where does my work run?

On your Debian host. The Pixel is the control surface. You need a reachable host and working SSH access from Termux.

## Is this app an SSH client?

Not yet. It prepares commands and opens Termux. Review the command, paste it into Termux and press Enter. No command runs just because you open this app.

## Where are my SSH keys?

In Termux. This app stores only your chosen SSH alias and session name locally. It does not read keys, passwords, interactive terminal output or SSH configuration. If you tap a live check, it receives that read-only command's result.

## Do I need Tailscale?

No. Any working SSH route is enough. Tailscale is one option for reaching a host away from home. Configure networking and SSH in Termux first.

## How do I detach?

In tmux, press Ctrl+b, release, then press d. The session continues on the host. Use Reattach in the Sessions page to return.

## Does a session survive a reboot?

No. It survives terminal and SSH disconnection, not host reboot or workload exit. Automatic boot and agent transcript resume are future features.

## Can I use my preferred agent?

Yes. Install and authenticate it on the host, then add a workload command array to your private Overtura configuration. The CLI supports named workloads; this app's first session builder starts a shell.

## What if the app or CLI breaks?

Use Termux and ordinary SSH. On the host, run tmux -L overtura list-sessions, then tmux -L overtura attach-session -t '=work' for a session named work.

## Where is configuration kept?

The host configuration is ~/.config/overtura/config.toml, or under XDG_CONFIG_HOME. It stays outside the public repository. Setup refuses to overwrite an existing file.

## How do I try this without changing my usual setup?

Use the disposable Debian lab described in the repository. It has its own test user, filesystem and local SSH endpoint. Enter it through your host; its port is not exposed to the network.
