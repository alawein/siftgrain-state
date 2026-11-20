# Research through October 13, 2026

Siftgrain State serves evaluators who already own observation collection and
need deterministic, inspectable checks. It complements harnesses through explicit
packets, local conversions, CI, and read-only MCP. It cannot replace benchmark
execution, independently collected state, or a complete task specification.

## Dated source table

Every source below was accessed October 13, 2026. Unknown dates are explicit;
access is not a publication date. No post-cutoff release is used. Live docs may
lack immutable revision dates, so precise version claims use pinned source.

| Source | Publication | Revision | Release | Why it matters |
| --- | --- | --- | --- | --- |
| [tau-bench paper](https://arxiv.org/abs/2406.12045v1) | June 17, 2024 | v1 June 17, 2024 | Not applicable | Final database goals and repeated-trial pass^k. |
| [Pinned tau source](https://github.com/sierra-research/tau-bench/tree/59a200c6d575d595120f1cb70fea53cef0632f6b) | Unknown | March 18, 2026, GitHub commit | Unknown | Actual public trajectories and native reward implementation. |
| [tau2-bench](https://arxiv.org/abs/2506.07982v1) | June 9, 2025 | v1 June 9, 2025 | Unknown | Dual control extends who can change the environment. |
| [Hyper-tau-bench](https://arxiv.org/abs/2609.04611v1) | September 4, 2026 | v1 September 4, 2026 | Unknown | Recent agent-construction evaluation uses held-out simulations. |
| [tau-Rec](https://taubench.com/community/tau-rec.html) | September 2026, exact day unknown | Unknown | Unknown | Programmatic recommendation and policy checks with repeated trials. |
| [AgentSuite tau trajectories](https://huggingface.co/datasets/AgentSuite/tau-bench-trajectories) | Unknown | Unknown | Unknown | Additional public trajectory inventory; not used without source/license pin. |
| [SWE-bench harness](https://www.swebench.com/SWE-bench/api/harness/) | Unknown | Unknown | Unknown | Per-instance report.json contains native resolved result. |
| [Inspect logs](https://inspect.aisi.org.uk/eval-logs.html) | Unknown | Unknown | Unknown | Samples, scores, store, and completion status remain distinct. |
| [Inspect scoring](https://inspect.aisi.org.uk/scoring.html) | Unknown | Unknown | Unknown | Custom scoring can inspect supplied state or execute other code; our core cannot. |
| [WebArena](https://arxiv.org/abs/2307.13854) | July 26, 2023 | Unknown in this scan | Unknown | Website environments evaluate functional task completion. |
| [OSWorld](https://arxiv.org/abs/2404.07972) | April 12, 2024 | Unknown in this scan | Unknown | Computer environments use task-specific execution-based evaluation. |
| [Agentic Benchmark Checklist](https://arxiv.org/abs/2507.02825v5) | July 3, 2025 | August 7, 2025, v5 | Not applicable | Reward/task setup defects limit interpretation of success rates. |
| [MCP schema](https://modelcontextprotocol.io/specification/2025-06-18/schema) | Unknown | Protocol June 18, 2025; page revision unknown | Not applicable | Closed-world readOnlyHint and structured tool results; hints are not proof. |
| [RFC8785](https://www.rfc-editor.org/rfc/rfc8785) | June 2020 | RFC8785 | Not applicable | Canonical JSON bytes for optional signatures. |

September 1 to October 13 emphasis: the September hyper-tau paper and tau-Rec
spotlight show continuing demand for verifiable outcomes and repeated trials.
This is a dated primary-source scan, not an exhaustive market census or proof
of product demand. GitHub/Hugging Face inventories were inspected; no unpinned
external data from a search result was silently added to the benchmark.

## How similar tools are evaluated

The original tau-bench environment compares its final database hash with a goal
database produced by executing annotated tools, and can check required response
content. Its repeated-trial metric measures reliability, not just a single run.
The archived airline trajectories used here do not expose complete databases,
so replaying rewards faithfully is impossible from those records alone.

SWE-bench evaluates patches through instance-specific test results. A submitted
patch and a resolved instance are different facts. Our converter accepts the
native per-instance resolved Boolean without claiming to have run those tests.
Inspect offers configurable scorers and structured log stores. A stored score
is not an independently supplied final-state snapshot.

WebArena and OSWorld evaluate task-specific environment outcomes. Siftgrain State
has a narrower task: evaluate explicit predicates over supplied state with subject,
time, and baseline constraints. It reports missing evidence rather than estimating
it. Signatures and hashes make byte identity inspectable, not state truthful.

Our benchmark injects six controlled faults into real public reservation-state
anchors. Gold is the intervention contract, not independent task-success labels.
Report per-state precision/recall, naive equality, coverage, deterministic replay,
throughput, and traced Python memory. Retain the earlier public projection study's
13 confirmed, 9 contradicted, 62 unobserved among 84 native reward successes as
projection classifications only. Every full-state recheck remains unobserved.

## Source and distribution choices

Use the pinned MIT tau archive and retain Sierra's notice. Fetch raw source into
ignored local storage and bind it by SHA-256; generate locally downloadable
licensed derivatives and separate answer keys. No transcripts enter Git. Newer
inventories without a verified license/version/checksum are research references,
not redistributed data. No human labels or LLM judge run are claimed.

The family name search, rejected collision, and limited trademark-style result
are in [name checks](name-checks.json). Actual repository commits, PRs,
releases, and current security observations are in [repo history](repo-history.json).
Cross-repository visual/style history is in [shared history](shared-history.md).
Settings history is not fully observable from the available user-repository API.
