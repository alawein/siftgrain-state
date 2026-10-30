# Siftgrain State

Siftgrain State checks whether the evidence you supply supports an AI agent's
requested outcome. It is for developers who evaluate agents and need to verify a
reported result against observed state. It does not execute actions or track
them over time.

![Siftgrain State](brand/wordmark.svg)

A successful action receipt can accompany the wrong state. Siftgrain State
shows the receipt, observation, baseline, freshness, and verdict together.
The `outcome-check` Python package and CLI need Python 3.11+ and the standard
library, with no network or model calls.

## First check

Install [uv](https://docs.astral.sh/uv/), then from a clone of this repository:

```sh
uv sync --frozen
uv run outcome-check examples/checks-v3.packet.json --html report.html
```

Open `report.html` directly, offline. The viewer has Cartoon, Calm, Pixel, and
Lab themes, dark and light appearance, keyboard controls, and reduced motion.
Exit 0 means every requirement confirmed; 1 means review is needed; 2 means
invalid input or I/O. Examples are original CC0 synthetic data.

| State | Meaning |
| --- | --- |
| Confirmed | Eligible observation satisfies the requirement and required receipt. |
| Contradicted | Observed state or required action contradicts the requirement. |
| Unobserved | Evidence is missing, stale, future, wrong-subject, or otherwise ineligible. |
| Unconfirmed-no-change | The target is satisfied, but its required change was not observed. |

The fourth display label corresponds to stable JSON status `unconfirmed`.
Baseline comparisons establish observed change, not which agent caused it.

## Integrate

Convert an explicit native SWE-bench per-instance report:

```sh
uv run outcome-convert swebench report.json --as-of 2026-10-13T12:00:00Z --observed-at 2026-10-13T11:59:30Z --max-age-seconds 60 --output packet.json
uv run outcome-check packet.json --html outcome.html
```

The tau adapter accepts explicitly supplied `initial_state` and `final_state`.
The Inspect JSON adapter reads caller-collected `store.outcome_state` and optional
`store.baseline_state`. Both require an explicit `--goal` file. Missing snapshots
stay unobserved; reward, score, tool-call arguments, and assistant claims do not
become observations. Native binary `.eval` archives are not decoded.
See [adapter contract](docs/adapters.md) for exact shapes and limits.

Run the read-only MCP tool over stdio with `uv run outcome-check-mcp`. Configure
that command in your MCP client. It accepts a packet object, never a file path,
command, URL, model, or executor. [MCP contract](docs/adapters.md#mcp) documents
its finite protocol scope. A [composite GitHub Action](action.yml) checks packets
and preserves the checker's exit status.

## Inspect the viewer

```sh
uv run python scripts/build_demo.py
uv run python scripts/build_state_demo.py
```

The viewer checks need Node.js 22:

```sh
npm ci --ignore-scripts
npm test
npm run perf
npm run lhci
```

Open `site/state.html` for the four-state showcase, `site/index.html` for the alarm case or `site/acceptance.html` for the
synthetic refund demo. All libraries, scripts, and styles are local or embedded.
A strict hashed CSP denies connections; imported evidence uses escaped text.
The GPU evidence sweep runs in an optional WebGL2 worker, with a static fallback.

Demo recordings: [Cartoon](assets/demos/cartoon.mp4),
[Calm](assets/demos/calm.mp4), [Pixel](assets/demos/pixel.mp4),
[Lab](assets/demos/lab.mp4). See [performance evidence](PERF.md) for measured
results and the limits of automated accessibility and interaction measurements.

## Reproduce the benchmark

```sh
make bench
```

This fetches checksum-pinned public tau-bench trajectories outside the offline
core, injects known faults, checks each case, and creates
`build/siftgrain-state-data-v1.zip`. Subsequent offline runs use
`uv run python benchmarks/run.py` with the retained source.
Dev/test cases and separate answer keys are inside the local archive.
[Results](RESULTS.md), [datasheet](benchmarks/data-v1/DATASHEET.md), and
[dataset card](benchmarks/data-v1/README.md) describe its actual scope.

## How this differs

[tau-bench](https://arxiv.org/abs/2406.12045) evaluates database goals inside an
agent environment; [SWE-bench](https://www.swebench.com/SWE-bench/api/harness/)
evaluates instance test results; [Inspect](https://inspect.aisi.org.uk/scoring.html)
provides configurable scorers. Siftgrain State checks supplied, named evidence
against explicit conditions without running any of those environments. It adds
freshness, subject binding, and required-change checks, not independent collection
or an alternative measure of full-task success. [Research](RESEARCH.md) records
source dates and related work.

## Limits and compatibility

Unsigned observations are unauthenticated. Optional Ed25519 signatures identify
which local key supplied the canonical bytes, not whether those bytes are true.
A hash binds bytes only. The verifier cannot establish actual execution, state
collection accuracy, causation, or the completeness of a caller's goal.

v0.2.x packets still load with their original semantics; migration to schema v3
is explicit and refuses signed input. [Contract](docs/contract.md),
[migration](MIGRATION.md), and [requirement coverage](REQUIREMENTS.md) distinguish
implemented behavior from missing external evidence.
The bounded regex language deliberately rejects general expressions.

MIT license.

## Related

Siftgrain State is part of the Siftgrain suite, alongside
[Siftgrain Cite](https://github.com/alawein/siftgrain-cite) for human citation
review and [Siftgrain Audit](https://github.com/alawein/siftgrain-audit) for
evaluation completeness.
