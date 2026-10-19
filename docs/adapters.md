# Adapter and MCP contracts

Adapters project one explicit JSON record into schema v3. They do not execute
agents, replay tools, download files, inspect clocks, or turn scores into state.
The converter validates duplicate keys, file bounds, all packet relationships,
and input/output identity before an atomic write. It never silently drops a row.

## tau

Supply `task_id` (string or integer), optional object `final_state`, and optional
object `initial_state`. Supply a nonempty JSON goal object with `--goal`. Each goal
key becomes a typed equality requirement at that key. Use `--requires-change`
only for genuine mutation targets; it requires a preceding baseline. Missing
final or baseline evidence stays unobserved. Extra trajectory metadata is ignored,
including rewards and tool-call claims. Real tau-bench archives often omit full
final databases, so their rewards cannot be rechecked through this adapter alone.

## SWE-bench

Accept `{ "instance_id": "x", "resolved": true }` or native per-instance
`{ "x": { "resolved": true, "patch_successfully_applied": true } }`.
The wrapper must contain exactly one instance. `resolved` must be Boolean.
The requirement is `resolved=true`; this checks the supplied native checker result,
not a rerun of its tests. A missing resolved result is invalid conversion, not
success inferred from a submitted patch. Bulk summaries and predictions need
explicit per-instance extraction first.

## Inspect

Accept a JSON sample with `id`, and `store.outcome_state` as an object from an
explicit caller-owned state collector. Optional `store.baseline_state` is the
baseline. `--goal` supplies the goal object. Scores, messages, model output, and
sample completion are never observations. Native `.eval` zip decoding and
collection plugins are outside this adapter's finite scope; export JSON first.

## Clocks and identity

Every conversion requires `--as-of`, `--observed-at`, and `--max-age-seconds`.
A supplied baseline additionally requires `--baseline-at`. Times require explicit
RFC3339 zones. No inferred wall-clock or freshness claim is added. Subjects bind
to the supplied task/sample/instance ID. The converter preserves its input object.

## MCP

`uv run outcome-check-mcp` runs an MCP 2025-06-18 stdio server with `initialize`,
`ping`, `tools/list`, and `tools/call`. JSON-RPC requests use one UTF-8 JSON object
per line, at most 5 MiB. Oversized frames terminate the stream without parsing a
tail as a new request. Notifications get no reply. Unsupported methods and
invalid requests use protocol errors; invalid packets use tool `isError=true`.

Native stdin is framed in bytes and decoded as strict UTF-8, independent of the
host's text-stream locale. Malformed UTF-8 produces a parse error (`-32700` with
null ID); the next valid frame can still be handled. The byte limit includes the
frame's newline. Valid Unicode request IDs are preserved.

The only tool is `check`, with exactly `{ "packet": <packet object> }`.
It returns both text JSON and `structuredContent`. It advertises read-only,
idempotent, closed-world behavior. Tests deny sockets, subprocesses, and every
file open during the tool invocation. No paths, URLs, signing keys, commands,
external tools, HTTP listener, model sampling, or collection capability exists.
Signatures passed to this endpoint remain unverified because it has no configured
public-key verifier; signature-required input cannot silently confirm.

Initialization offers the supported 2025-06-18 version when a client requests an
unsupported version; a client that cannot use it must disconnect. This is a small
finite server, not a claim of compatibility with every MCP SDK extension.

## GitHub Action

Checkout this repository at an exact reviewed commit and invoke `uses: ./` with
`packet: examples/checks-v3.packet.json` and an optional `html` path. The runner
must already supply Python 3.11+. The composite action needs no package install,
network, or secret. Exit 1 fails the step when evidence needs review. Workflows
using a remote action should pin its full reviewed commit SHA.

A SWE-bench single-instance wrapper may repeat its ID inside the report only when both value and type agree. Conflicting explicit IDs reject the whole conversion; no subject is silently overwritten.
