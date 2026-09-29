# From Pixel to a running session

## 1. Prepare Termux

Install Termux from its official project, then install its OpenSSH package. Configure your SSH key and host alias in Termux. Confirm you can log in normally before using OverturaApp.

## 2. Prepare the Debian host

The host needs Python 3.11 or newer, tmux and Git to clone the source. Use the distribution packages. Remote SSH access must already work; Overtura does not configure the SSH server.

## 3. Install Overtura

Clone the public repository on the host, inspect it, and run python3 install.py as your regular user. Then run ~/.local/bin/overtura setup and ~/.local/bin/overtura doctor. Add ~/.local/bin to PATH if needed.

## 4. Choose your workspace

Edit ~/.config/overtura/config.toml on the host. Point host.workspace to an existing directory. The default is your home directory. Setup never replaces an existing configuration.

## 5. Start and return

In the app, enter the same SSH alias you use in Termux. Run Doctor, then open Sessions and create a shell. Detach with Ctrl+b, then d. Use Reattach to return to it.

## Updates

Update the checkout and run python3 install.py --upgrade. The CLI is replaced while private configuration and running sessions are preserved.
