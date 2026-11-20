# Results

Measured October 13, 2026 with recorded Python platform Windows-10-10.0.26300-SP0 (Windows 11 host),
Python 3.11.13, AMD64 Family 25 Model 117 Stepping 2, AuthenticAMD.
Numbers below are real software runs, not agent competence or human-study scores.

## Controlled trajectory faults

200 source trajectories; 173 with an explicit reservation
snapshot; 1038 cases across six controlled variants. All fault labels are
programmatic interventions on supplied snapshots, not independent task-success
gold. The selected state becomes the declared goal only for this diagnostic.

| Verdict | Gold cases | Predicted | Precision | Recall |
| --- | --- | --- | --- | --- |
| confirmed | 173 | 173 | 1.0 | 1.0 |
| contradicted | 173 | 173 | 1.0 | 1.0 |
| unconfirmed | 173 | 173 | 1.0 | 1.0 |
| unobserved | 519 | 519 | 1.0 | 1.0 |

Overall diagnostic accuracy: 1.000. Naive typed equality accuracy:
0.333; confirmed precision:
0.200. Its failure to distinguish
no-op, wrong subject, and timestamp ineligibility is deliberate baseline scope.
Every individual fault family has accuracy 1.0 on its 173 constructed cases.

Timed checker loop: 1.513819 s, 685.68 cases/s with tracemalloc enabled;
peak traced Python allocation 160892 bytes. This is not resident process memory,
a production SLA, or an instrument-free speed estimate. Reversed input ordering
reproduced identical ID-bound verdicts. Timing is machine/load-sensitive.
Exact environment, splits, metrics and source checksum: [results.json](results.json).

Native tau reward baseline: unavailable because the archive omits full final/goal
databases and its native checker reconstructs goals by executing tools. We did
not replay tools or relabel a naive comparison as native. LLM-as-judge omitted:
no model calls or new judgments. Confidence intervals are not appropriate for
these correlated deterministic variants of a nonrandom source inventory.

## Existing external projection study

The retained prior study of 84 native-reported successes has 13 confirmed,
9 contradicted,62 unobserved reservation-field projections. These are not
full-task success judgments or proof of nine wrong native scores. All 84 full
database/goal comparisons are unobserved because required snapshots are absent.
See [tau study](../studies/tau-airline/README.md). No missing state is recovered from
reward bits, signatures, or hashes.

## Software and viewer

Prechange:240 tests at 7c49ae4. Current product run:262 tests pass; lint/format,
mypy, pyright,19 versioned schemas/10 examples, wheel/sdist build and actionlint
pass. Fresh-clone source-bound results are recorded below and in the audit.
See [performance](../docs/performance.md) for actual three-engine accessibility/cadence/LCP results,
Lighthouse, byte budgets, and unavailable field-INP/hardware claims.

Human participants/labels: none. A future [protocol](data-v1/HUMAN_PROTOCOL.md)
is supplied without fabricated outcomes. Native `.eval` archive support,
independent collection, external full-task gold and population-level precision
remain outside demonstrated coverage.

## Fresh-clone verification

A no-hardlink clone started at d5a0817 and fast-forwarded to a2e423e (CI-only
interpreter-selection fix; core source unchanged). Fresh Python 3.11.13,
explicitly selected through UV_PYTHON, passed all 260 tests in 20.50 s, lint/format,
mypy, pyright, 19 schemas/10 examples, and the wheel/sdist build. A separate
Python 3.13.9 clean-clone gate passed 260 tests. An isolated installed-wheel
Python 3.11 environment had no cryptography dependency and rendered all four
states successfully. New benchmark split bytes matched between both interpreters.

Native mlcroissant 1.1.1 parsed two RecordSets and extracted 168 dev/870 test rows
with only an explicit FileObject-to-local-path mapping. Optional newer context
keys produce a warning, not a parse error. The package release date was verified
as October 5, 2026. No hosted dataset upload occurred.

Final browser harness uses fresh navigation through about:blank to exercise saved
preferences. Windows Firefox file reload intermittently timed out even with GPU
disabled; no application assertion is skipped. The unchanged startup/persistence
assertions and all 27 browser observations pass in the final local matrix.
A prior concurrent WebKit p95 of 33 ms correctly failed the unchanged 25 ms cap.
A controlled same-context comparison under reduced host contention measured
blank p95 17 ms and app replay p95 17 ms. These runs do not certify every laptop.

The additional fresh 4a321c6 clone passed 260 tests on Python 3.11.13 in 10.46 seconds, Ruff, mypy and all 19 schemas/10 examples. Its build under an ignored build/ ancestor was interrupted after confirming Hatchling discarded its ignore patterns; it is not counted as a successful build. Final-head verification is performed outside that path and recorded in PR21. Previously successful builds remain dated evidence above.

## Final product-source verification

Fresh temporary clone `1bed622efcacc88de57b074b4d02aa0fa41a7fa2` passed all 260 tests on Python 3.11.13 in 10.82 seconds, Ruff, mypy, pyright, 19 schemas/10 examples, and wheel/sdist build. It also passed 27 browser observations, both motion cancellation regressions, all 1038 benchmark cases, and native Croissant parsing. This resolves the interrupted nested-clone build above without changing source or build requirements.

The separate direct Lighthouse run measured performance 0.82, accessibility 1.00, LCP 1145 ms and TBT 335 ms. Native Lighthouse CI measured performance 0.92, accessibility 1.00, LCP 894.226 ms and TBT 196.5 ms and passed its unchanged LCP/accessibility assertions. Both measurements are retained in docs/final-verification.json. Neither proves field INP. Independent review of 4a321c6..1bed622 found no actionable defects. Final hosted status and landing are recorded by PR21.

## SWE-bench identity follow-up

A final native-review finding reproduced silent replacement of a conflicting nested instance ID by its wrapper key. The adapter now rejects differing or differently typed explicit IDs; matching IDs and source input immutability are covered. The negative regression failed on the previous implementation. All 262 tests passed on Python 3.11.13 in 8.08 seconds, with Ruff, mypy, pyright, 19 schemas/10 examples and wheel/sdist build. The checker and viewer remain unchanged. Final clean-clone/hosted execution and independent review bind the follow-up in PR21.

The fresh temporary clone was fast-forwarded to 974e64e and passed all 262 Python 3.11.13 tests in 9.72 seconds, Ruff, mypy, pyright, schemas and wheel/sdist build. Source hashes in docs/final-verification.json explicitly use canonical LF Git blob bytes. The viewer is byte-unchanged from its complete 1bed622 browser/Lighthouse verification.
