# Migration

Siftgrain State is the display brand and the GitHub repository is
`alawein/siftgrain-state`. Distribution `siftgrain-state` and import
`siftgrain_state` replace the old `outcome-check` package name. CLI
`outcome-check` and the `outcome-convert` and `outcome-check-mcp` entrypoints
remain compatible. No existing tag, packet, or JSON result field is renamed.

v0.2.x schema v1 packets load directly. Their three-state semantics remain intact;
no required change or baseline is silently added. Schema v2/v3 adds `unconfirmed`.
The viewer labels that state `unconfirmed-no-change` without changing JSON bytes.

Use `siftgrain_state.contract.migrate_to_v3(packet)` for validated deep-copy migration
of unsigned packets. Signed input requires authentic re-signing by the supplier;
the migrator refuses to discard or relabel signatures. See the versioned contract
for RFC8785 and legacy canonicalization differences.

New entrypoints `outcome-convert` and `outcome-check-mcp` are additive. Conversion
requires explicit subject, clocks, and goals. Outputs use the same no-clobber,
input-alias, and atomic-write policy as the checker.

The repository rename is complete, and the distribution and import rename to
`siftgrain-state` and `siftgrain_state` is applied. GitHub redirects do not rename
Python imports or preserve every external badge, so update verified consumers and
release metadata before publishing the new distribution name. A kohyr transfer
still needs confirmed organization permissions and its own explicit repository
transfer approval. No blanket transfer or registry-name availability is inferred
from the limited name search.

After a rename, verify current README/badges, package repository metadata and the
release-workflow repository guard. Read back the native PyPI publisher binding
against `alawein/siftgrain-state` and the `siftgrain-state` project; local metadata
does not prove a registry setting changed.
