# Overtura agent instructions

Overtura is a public, generic project derived from lessons learned in a
separate private deployment.

## Safety and privacy

- Never copy private Overture inventory, hostnames, addresses, usernames,
  Tailnet names, device IDs, keys, SSIDs, personal paths, credentials, or
  other deployment-specific data into this repository.
- Treat the private Overture repository as reference material for concepts,
  not source material to copy. Working on Overtura must not require access
  to that private repository.
- Do not modify the private Overture repository unless the task explicitly
  asks for it.
- Private/local configuration belongs outside Git. Generic examples and
  invented test fixtures are welcome; do not derive them from private data.
- Do not commit generated build artifacts, local SDK configuration, signing
  material, test-device identifiers, or captured private output.
- Inspect git status before editing and preserve unrelated work. Tests must
  use isolated resources and must not disrupt existing user tmux sessions.

## Architecture

- Preserve ordinary SSH and tmux as the recovery path.
- Prefer small, boring components and standard-library solutions.
- Do not introduce a daemon, framework, or dependency without a concrete need.
- Codex is one workload; do not design Overtura around a single agent.
- Human CLI behavior and the machine-readable JSON interface are separate
  public interfaces.
- Preserve protocol-v1 compatibility as documented in `docs/protocol-v1.md`.
  Incompatible protocol changes require an explicitly versioned successor
  rather than silently changing v1.
- Prefer configuration and capability detection over assumptions about a
  particular machine or topology.

## Scope

- Work in bounded phases.
- Do not implement unrelated future features while completing the current task.
- Browser, VNC, ADB, clipboard and other optional integrations should remain
  modular.
- Do not use ADB or alter a physical device unless the task explicitly allows it.
- Do not turn experimental ideas from the private deployment into public
  requirements without first establishing that they belong in Overtura.

## Verification

- Read `README.md` and the relevant files under `docs/` before changing
  architecture or public behavior.
- Run tests appropriate to the area changed. Documentation-only changes do
  not require running the application test suites.
- For CLI or protocol changes, run `python3 -m unittest discover -s tests -v`
  from the repository root.
- For substantive Android changes, run
  `./gradlew testDebugUnitTest lintDebug assembleDebug` from `android/`.
  These checks do not require ADB.
- Use the disposable Debian lab for Debian/SSH integration changes when
  relevant; follow `tests/lab/README.md`. Rebuild with current source before
  claiming lab verification, and check for user work before resetting it.
- Keep documentation consistent with actual implemented behavior and limitations.
- Do not claim verification that was not actually performed. Report deferred
  or blocked checks explicitly.

## Android

- Manual Termux/SSH fallback must remain available.
- Do not take ownership of SSH credentials or silently execute commands unless
  an explicit design and task introduce that capability.
- Keep transport, protocol parsing, UI state and device automation as separable
  concerns where practical.
