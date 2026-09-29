# Your work stays on the host

Overtura keeps a shell or agent running on your Debian machine while your Pixel comes and goes.

## Three pieces, one workflow

OverturaApp is your guide and command launcher. Termux handles SSH and the terminal. Overtura on the host manages durable tmux sessions.

## Start once. Return later.

Create a named session, do your work, then press Ctrl+b followed by d to detach. Reconnect and attach to the same name when you return.

## What survives?

Closing the phone terminal or losing the SSH connection leaves the host session running. Rebooting the host or exiting the session's command ends it.

## You are in control

This first app previews commands, copies them, and opens Termux. Paste and press Enter there. Passwords, keys and terminal output stay in Termux.
