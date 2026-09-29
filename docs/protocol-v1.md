# CLI JSON protocol v1

CLI 0.2.0 adds an opt-in machine interface. Ordinary terminal commands retain
human-readable output. The Android app consumes read-only replies through an
opt-in Termux transport; manual copy/open-Termux actions remain available.

## Invocation and envelope

```sh
overtura --json capabilities
overtura --json doctor
overtura --json session list
overtura --json session create work --detach
```

`--json` also works after the subcommand. Put global `--config` and `--socket`
options before the subcommand. A handled request writes one UTF-8 JSON object
and a newline to stdout, with no diagnostic prose on stderr:

```json
{"schema_version":1,"cli_version":"0.2.0","command":"session.list","ok":true,"data":{"sessions":[]},"error":null}
```

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer wire-format version, currently 1. Independent of CLI and config versions. |
| `cli_version` | CLI release string; informational, not a schema selector. |
| `command` | `capabilities`, `doctor`, `session.list`, or `session.create`. Invalid argument parsing uses null; rejected operations retain their command name. |
| `ok` | Boolean success. A failed doctor can still contain useful data. |
| `data` | Command-specific object, or null on an operation error. |
| `error` | Null on success; otherwise an object with a machine-readable `code` and human-readable `message`. |

Exit 0 means success, 1 means a failed check or operation, and 2 means invalid
arguments or an unsupported JSON operation. Do not discard stdout on a nonzero
exit: a failing doctor carries the complete report. `--help` and `--version`
remain plain text even with `--json`. Python startup failures, process termination,
and failures before the CLI starts cannot guarantee an envelope.

Consumers must check the schema, command, field types, and exit-code agreement.
Unknown fields may be ignored within v1; incompatible required-field or semantic
changes require a new schema. Do not parse English messages to make decisions.
Unknown error codes should become a generic operation error, never success.
Fixtures in `tests/fixtures/protocol-v1` are shared by Python producer tests and
Android JVM consumer tests. They contain invented, public test data.

## Command data

### capabilities

Requires neither tmux nor configuration. Returns:

```json
{"schema_versions":[1],"config_version":1,"json_commands":["capabilities","doctor","session.list","session.create"],"session_create_requires_detach":true}
```

### doctor

Returns `ready` (boolean) and `checks` (array). Each check has a unique `id`,
a `status` of `ok`, `warn`, `fail`, or `info`, and a `message`.
Core IDs are `python`, `tmux`, `ssh`, `config`, and `durability`. A readable,
valid configuration adds `workspace` and `workload.NAME` entries.

A missing tmux executable, invalid/missing configuration, or missing workspace
makes `ready` and `ok` false, with error code `doctor_failed` and exit 1.
Missing optional SSH/workload executables are warnings. Ready does not mean
that a remote connection, agent authentication, or every workload will work.
The check runs on the host and does not start a tmux server.

### session.list

Returns `sessions`, an array of records with:

| Field | Type and meaning |
| --- | --- |
| `id` | tmux ID such as `$0`, unique within the running server. Not a persistent identity across server restarts. |
| `name` | tmux's display form of the session name. |
| `windows` | Positive integer window count. |
| `attached_clients` | Nonnegative integer client count. |
| `attachable` | Whether the displayed name satisfies Overtura's CLI name rules. |

Names created through Overtura match `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`. Native
tmux sessions can use other names; they remain visible with `attachable:false`.
Tmux escapes control characters and backslashes in its displayed names. Clients
must display these as text and must not unescape them into commands. Unicode,
spaces, quotes and separators cannot change the record structure. Counts and
IDs are read separately from names, and UTF-8 output is requested explicitly.

An absent server or no sessions is success with an empty array. Missing tmux,
permission errors, malformed records, and timeouts are failures with null data;
they must never be presented as an empty successful list. Listing needs no
configuration. It is a best-effort snapshot, not an atomic transaction: sessions
that disappear between reads are omitted, and counts may already have changed.
No pane contents, terminal titles, working directories, or process arguments
are collected.

### session.create

JSON creation requires `--detach`. It returns
`{"session":{"id":"$0","name":"work","workload":"shell"}}` after tmux
accepts creation. This does not guarantee the workload remains running.
Duplicate names fail with `session_exists`; the existing session is untouched.
A timeout or disconnected transport can leave the outcome uncertain. Inspect the
session list before deciding whether to retry a mutation.

JSON `setup`, `session.attach`, and creation without `--detach` are rejected
before side effects with exit 2 and `unsupported_operation`. Interactive
attachment continues through the ordinary terminal interface.

## Errors and privacy

The v1 error codes are `invalid_arguments`, `unsupported_operation`,
`doctor_failed`, `dependency_missing`, `config_missing`, `config_invalid`,
`config_unreadable`, `workload_unknown`, `workload_unavailable`,
`directory_missing`, `session_exists`, `tmux_failure`, `tmux_timeout`,
`os_error`, and the fallback `operation_failed` for other validation failures.
Doctor wraps its individual findings in checks and uses `doctor_failed`.

Errors do not echo raw tmux stderr, malformed config contents, bad argument
values, configured paths, or workload command arguments. Session names and
workload identifiers are intentional output and may still be private user data.
Do not automatically publish responses. The Android reader uses generic parser
errors without retaining the raw reply or nesting parser exceptions.

Each tmux subprocess has an eight-second deadline. A list may use multiple
subprocesses, so this is not a total request deadline. Large installations may
exceed the companion reader's limits; show an error rather than partial success.

## Android consumer boundary

`Commands.readOnlyQuery` generates only capabilities, doctor and list queries,
using `ssh -T`, `BatchMode=yes`, an eight-second connection timeout, and server
alive checks. It keeps host keys and credentials in Termux's SSH configuration.
It does not disable host-key verification. First connection, password prompts,
and key unlocking belong in the manual Termux flow. The Android app now runs
these queries only after a tap and Termux permission/setup.

`ApiReply` uses the platform JSON decoder and validates required fields and their
types. It accepts schema 1, limits responses to 256 KiB and nesting to 32 levels,
and rejects banners, trailing output, missing fields, mismatched commands,
inconsistent readiness, duplicate IDs, and unsafe attachable names. Unknown
fields are ignored. JVM tests use a test-only org.json dependency; Android's
platform decoder has parsed successful Doctor and Sessions replies in an
initial Pixel smoke test. This is a schema validator, not a general-purpose
strict JSON syntax validator.

SSH exit 255 becomes a connection error; 126/127 indicate an unavailable CLI.
An empty exit-2 reply suggests an older CLI. Other malformed output gets a
compatibility error. Raw SSH stderr is not a parser input or user-facing report.

`QueryState` tracks a monotonically increasing request token for one host and
operation. Switching either clears old data; superseded or repeated callbacks
are ignored. The caller supplies monotonic elapsed milliseconds. Requests expire
after 20 seconds; results become stale after 30 seconds or when refreshed or
cancelled. A failed refresh keeps the previous snapshot explicitly stale. A
failed doctor with valid checks is fresh data requiring attention. A failed list
with null data cannot replace a prior list with an empty success.

`TermuxBridge` now uses the opt-in Termux RUN_COMMAND permission and a one-shot
callback for background queries. Termux must also have `allow-external-apps=true`
and `coreutils` installed. The shell command uses `timeout` to stop SSH after
18 seconds (with a one-second kill grace); the UI rejects callbacks after 20
seconds. Leaving the Activity or changing hosts drops callbacks, while an
already-started SSH command may run until its Termux timeout. Termux truncation
metadata and the 256 KiB parser limit prevent partial replies from appearing
as complete data. Callbacks are not persisted across app process termination.
Manual copy/open remains available.

The Pixel smoke test covered successful Doctor and Sessions replies, an
unreachable SSH alias, and recovery after restoring the alias. The 0.2.1 ADB
reliability pass additionally covered denied permission, failed Doctor and
older-CLI response fixtures, timeout, background cancellation and process
recreation. Rotation and permission revocation during a query remain untested.

## Verification history

- 31 Python CLI/protocol tests passed locally and in the disposable Debian 13 lab.
- Lab installation, successful and failed JSON replies over SSH, and abrupt SSH
  loss followed by reattachment to the same shell process passed.
- 17 Android JVM tests passed; Android lint reported no issues; debug APK assembly
  passed. That protocol-only phase had no ADB, emulator or on-device checks.

The subsequent Termux transport and onboarding phase passed Android JVM tests,
lint and a debug build. Its 0.2.0 debug APK was installed on a Pixel running
Android 17. The user granted Termux command permission and enabled external
commands in Termux. Live Doctor and Sessions queries succeeded; an unreachable
alias produced the expected connection error, and restoring the alias restored
the session list. This initial device smoke test preceded the reliability pass.

An assisted fresh-phone setup on a second Pixel on 2026-09-30 also confirmed
live Doctor and session-list callbacks after enabling Termux external commands
and granting the Android permission. Manual SSH, Doctor, session creation and
detach/reattach passed against an existing Debian host over local Wi-Fi. This
did not itself cover transport failures.

For app 0.2.1, `android/reliability.py` exercises Termux's real SSH and callback
path against a temporary SSH fixture server. Denied permission prevented any
request; failed Doctor data, the old-CLI empty exit-2 case, timeout and recovery
passed. Background cancellation ignored a late result. Android process death
and restoration preserved navigation/scroll while discarding transient results.
The runner restores the phone's original configuration and permissions. This
pass changes neither CLI 0.2.0 nor the protocol-v1 contract.
