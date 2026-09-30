# Overtura ideas

This file collects promising directions that are not yet commitments or roadmap
requirements. Keep implementation decisions in the relevant design docs once an
idea becomes concrete.

## Guided setup over Termux

The existing Termux RUN_COMMAND transport proves that Overtura can execute
commands through Termux and receive structured results. That opens a path from
today's copy/paste onboarding toward a guided setup wizard.

The key boundary remains: Termux must already be installed and opened once, and
the user must explicitly allow Overtura to run commands through it. Overtura
should not try to hide that trust boundary.

A future setup flow could progressively handle:

1. Detect whether Termux is installed and ready.
2. Check/install phone-side tools such as OpenSSH and coreutils.
3. Check for an SSH key and offer to create one.
4. Build or update an SSH host alias from user-supplied values.
5. Test the host connection.
6. Help authorize the phone's public key on the host.
7. Install or update Overtura on the Debian host over SSH.
8. Run host setup and Doctor.
9. Confirm that session creation, detach and reattach work.
10. Enable optional live Doctor and session-list integration.

Sensitive or trust-bearing steps should stay visible and explicit. Host-key
verification, credentials, key authorization and similar decisions should not be
silently accepted on the user's behalf.

## One engine, several levels of guidance

Do not build separate "beginner" and "expert" installers. Prefer one underlying
set of setup actions with progressively different presentation.

Possible UI modes:

### Guided

For someone setting up Overtura without much SSH/Termux experience.

- Plain-language explanations.
- One clear next action at a time.
- Safe deterministic commands can be executed through Termux after permission is
  granted.
- Trust-sensitive steps pause for explicit confirmation or handoff.
- Success is shown as a checklist rather than terminal output.

Example:

```text
✓ Termux detected
✓ OpenSSH installed
✓ SSH key ready
✓ Host configured
✓ Host reachable
✓ Overtura installed
✓ Doctor healthy
```

### Assisted

For someone who understands roughly what is happening or is being helped by
another person.

- Show the exact command before it runs.
- Allow copy/open-Termux as an alternative to automatic execution.
- Show useful structured diagnostics and exact failure reasons.
- Make host aliases, public keys and configuration snippets easy to inspect and
  share safely.
- A future "setup report" could help someone troubleshoot without exposing
  private keys or unrelated device data.

The current fresh-phone walkthrough is already close to this mode.

### Direct

For experienced users who want the abstraction out of the way.

- Host and session dashboard first.
- Fast access to Doctor, session list and raw command previews.
- Manual Termux/SSH handoff remains available.
- Advanced transport and diagnostic details may be exposed directly.

Avoid asking users to permanently classify themselves as "beginner" or "pro".
Default to the guided presentation and let them reveal more detail with controls
such as "Show commands" or "Advanced".

## Shared setup actions

The three presentations should call the same underlying operations rather than
implement separate flows. Conceptually:

```text
ensure_termux_tools()
ensure_ssh_key()
configure_host_alias()
test_host()
authorize_public_key()
install_or_update_overtura_host()
run_doctor()
verify_session_roundtrip()
```

Each action should have explicit inputs, structured results and clear side
effects. Guided mode can wrap them in explanations; Assisted mode can expose the
commands and outputs; Direct mode can expose the primitives more directly.

This keeps the easy path and expert path from drifting into two different
installation systems.

## Dedicated Android test device

When a spare supported Pixel becomes available, use it as Overtura's dedicated
physical test phone. A separate device gives onboarding its own primary Android
user, Termux installation, SSH files and app permissions, avoiding changes to a
daily phone. Stock Termux's fixed installation paths make secondary Android
users and work profiles unsuitable for a fresh Termux environment.

Keep the phone available on trusted Wi-Fi and power, but enable or connect ADB
when a test needs it rather than treating a permanently open ADB connection as
a requirement. Pair it with the disposable Debian lab for host-side checks.
Keep the side-by-side Overtura Lab app on the current phone for quick app checks;
use an emulator or dedicated phone for a truly fresh Termux install and
first-run walkthrough. Hardware availability is a future convenience, not a
prerequisite for Overtura development.

## Security and recovery principles

- RUN_COMMAND access is powerful. Setup actions should be visible,
  user-initiated and narrowly scoped.
- Never pass passwords or private SSH keys through Overtura merely to make setup
  look automatic.
- Keep host-key verification an explicit trust decision.
- Prefer idempotent checks before mutations.
- Detect existing tools, keys and SSH config before creating or replacing them.
- Never overwrite an existing SSH key.
- Preserve manual Termux + SSH + tmux as the recovery path.
- Automatic setup should make the underlying system easier to use, not make it
  impossible to understand or repair without the app.

## Possible evolution

A conservative progression could be:

1. **Current** — documentation plus copy/paste/manual Termux handoff.
2. **Guided checks** — detect state and tell the user exactly what remains.
3. **Guided safe actions** — run deterministic setup commands through Termux.
4. **Explicit trust handoffs** — host verification/key authorization remain
   interactive.
5. **Mostly terminal-free normal operation** — once configured, everyday Doctor,
   session listing and session actions happen from Overtura while manual SSH/tmux
   remains available underneath.

The important goal is not to remove Termux or SSH. It is to stop requiring a new
user to understand every layer before Overtura becomes useful.
