# Disposable Debian lab

This rootless Podman container provides a fresh Debian 13 userspace, a normal
test user, and an actual SSH server. It shares the host kernel; it is not a VM
and cannot validate boot services or host reboot behavior.

## Prerequisites

Install on the host once, using its normal administrator workflow:

```sh
sudo apt-get install --no-install-recommends podman uidmap passt fuse-overlayfs
```

The regular user needs subordinate ID ranges in `/etc/subuid` and `/etc/subgid`.
See [Podman's rootless setup documentation](https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md).
The lab runs with a 512 MiB memory limit, one CPU's quota, and a 128-process limit.

## Use

Run from the repository, as your regular user:

```sh
python3 tests/lab/lab.py up
python3 tests/lab/lab.py check
python3 tests/lab/lab.py shell
```

`up` builds the image if the container does not exist, creates fresh SSH host
keys at runtime, and configures dedicated public-key authentication. It publishes
SSH only at `127.0.0.1:22222`. No host workspace, home directory, SSH agent or
agent credentials are mounted or forwarded into the container. Build input is an
explicit allowlist of source and test files. The container has outbound network
access and is intended for trusted project tests, not hostile code.

`check` installs the CLI as the unprivileged test user, creates configuration,
runs doctor and the integration suite, and verifies session survival by abruptly
killing a real SSH client, reconnecting and checking the original shell PID.
It removes only its uniquely named probe session. Repeated checks preserve other
sessions and existing test-user configuration.

In the lab shell, Overtura is available after `check` at:

```sh
~/.local/bin/overtura session create work
```

To enter from a phone, SSH into your usual host first and run `lab.py shell`
there. The lab's SSH port is not exposed to the LAN or Tailscale.

```sh
python3 tests/lab/lab.py status
python3 tests/lab/lab.py down
python3 tests/lab/lab.py reset
```

`down` deletes the disposable container and its contents, but preserves the
cached image and dedicated lab key pair. `reset` does the same and rebuilds the
image from current source. Use reset after source changes; up preserves an
existing container. Lab state is outside the repository at
`$XDG_STATE_HOME/overtura/lab` (default `~/.local/state/overtura/lab`).

The image uses Debian's maintained `13-slim` tag and current distribution
packages, so rebuilds are fresh-environment checks rather than byte-identical
reproductions. The script refuses to alter a same-named container without its
ownership label. It never runs Podman as root or requests privileged containers.

Verified with rootless Podman 5.4.2 and cgroups v2: installation and doctor pass,
all 17 integration tests pass inside Debian 13, and the real SSH reconnection
probe preserves the original shell process. The running container was checked
for its loopback binding, resource limits, and absence of host mounts.
