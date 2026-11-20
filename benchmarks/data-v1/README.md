# Dataset card: Siftgrain State fault set v1

- Task: four-state supplied-evidence classification under controlled faults.
- Source: 200 public recorded tau-bench airline trajectories, pinned by SHA-256.
- Eligible: 173 trajectories with at least one explicit reservation tool response.
- Cases: six variants per eligible trajectory, 1,038 total; clean, no-op, stale,
  wrong subject, timezone skew, and successful action with wrong final state.
- Ground truth: programmatic intervention labels, not human labels or native
  benchmark task-success labels. The base goal is the selected snapshot itself.
- Splits: deterministic SHA-256 task-ID grouping, keeping repeated task trials
  together. Dev/test answers are separate files. No model training occurred.
- Distribution: local generated ZIP, case JSON, answer-key JSON, checksums,
  schema, license, datasheet, Croissant metadata, and this card.
- License: MIT for source derivatives and code; source notice retained.
- Intended use: regression/fault detection, not leaderboard or safety claims.
- Public upload: not performed; a repository/dataset publication gate remains.

Run `make bench`. This writes generated files into `build/benchmark-v1` and
`build/siftgrain-state-data-v1.zip`; raw source stays ignored in `studies/data`.
The source revision is March 18, 2026, but the underlying paper is June 2024.
This is genuine public recorded agent data, not a newly collected 2026 agent run.

See [datasheet](DATASHEET.md), [provenance](provenance.json),
[Croissant](croissant.json), and [results](../RESULTS.md).
