# v0.3.0 implementation decisions

## Current release state (October 8, 2026)

Version 0.3.0 is published: [merged PR 16](https://github.com/alawein/outcome-check/pull/16),
[immutable tag](https://github.com/alawein/outcome-check/tree/v0.3.0),
[GitHub Release](https://github.com/alawein/outcome-check/releases/tag/v0.3.0),
[successful publish run](https://github.com/alawein/outcome-check/actions/runs/37799710726),
and [PyPI](https://pypi.org/project/outcome-check/0.3.0/).
The source commit is `66fea09ab87352224d3e01b65709392c3259e0ca`.
Do not retry that successful publication or replace its tag/assets.

Version 0.4.0 is now public on [PyPI](https://pypi.org/project/outcome-check/0.4.0/)
from immutable source `6f026e2f59059c34dd53b496eb4ff973712d380d`.
Its retained distribution bytes and publisher/build provenance were verified.
The initial post-upload registry check observed an incomplete listing. Recovery
[run 37824835131](https://github.com/alawein/outcome-check/actions/runs/37824835131)
succeeded without reuploading verified files and created the public
[GitHub Release](https://github.com/alawein/outcome-check/releases/tag/v0.4.0).
Exact hashes and recovery evidence are in [release readiness](release.md).
The entire Dependabot family remains excluded from this closeout.

## v0.4.0 decisions

- Keep `canonical_json` and default `sign_observation` on the legacy restricted
  profile. Schema v3 signatures require `canonicalization: "RFC8785"`; that field,
  algorithm and key ID are signed. Unknown profiles fail closed. v2 cannot opt in.
- Full JCS numbers use finite binary64, Python's shortest round-trip digits and
  ECMAScript decimal placement. Python integers are accepted only when exactly
  representable as binary64, avoiding implicit loss. Encode larger exact values
  as strings. Negative zero canonicalizes to zero; no Unicode normalization.
- Freeze official RFC 8785 Appendix B vectors and legacy bytes. Pin dev-only
  rfc8785 0.1.4; an additional Node 22.23.2 V8 differential command independently
  matched 99,956 seeded finite values. Core has no reference-package dependency.
- `migrate_to_v3` deep-copies unsigned packets. Signed packets require the trusted
  signer to re-sign original content; migration never relabels signature metadata.
- Full-state protocol requires supplied complete baseline/final/goal databases.
  Entire-database equality plus explicit mutation paths prevents unrelated changes
  from satisfying a required target mutation. Correct unchanged goals remain valid.
- Missing public states remain unobserved. Retain 13/9/62 reservation projections
  and all-84 full-state-unobserved finding. No tool replay or model reconstruction.
- Release 0.4.0 uses a single locked Hatchling 1.32.4 build; verify retained bytes
  before OIDC publish and GitHub upload. Existing different assets fail closed.
  A missing interactive credential is an access issue, not renewed permission.

## Reviewed release failure fixes (October 8, 2026)

- Keep the canonical build immutable. The pinned PyPA publisher writes attestation
  sidecars, so only missing file copies go to a separate fresh publish-dist directory
  through its packages-dir input. Canonical inventory validation remains strict;
  build verification addresses only manifest distribution filenames.
- Resume a partial upload only after every present file passes registry digest,
  downloaded-byte and exact publisher-provenance checks. Require the complete
  inventory after publication. Reject extra/conflicting files and foreign provenance;
  never use blind skip-existing or replace existing registry/GitHub assets.
- Generate factual public release notes only after verified complete registry state.
  Include version, source/tag and byte digests; keep checkout preparation notes and
  dated v0.3.0 history out of the generated public body. Tags and asset bytes remain
  immutable. Future retries reconcile existing release notes only after final
  download/readback verifies every asset; any mismatch prevents the notes edit.
  The current v0.4.0 public body already matches its verified release identity.

## Registry propagation recovery (October 8, 2026)

The first v0.4.0 run uploaded successfully, then failed because the immediate PyPI
version listing was incomplete. Verified retained bytes and provenance allowed a
failed-job rerun to skip existing uploads and finish the GitHub release. Preserve
that source/tag and every published byte. Future workflow checks retry only the
typed incomplete-inventory condition, at most five attempts with 37 seconds total
backoff. File conflicts, download errors and failed/missing provenance still fail
immediately; no unverified file is accepted and preflight never blindly skips.
Network and verification duration is additional to the bounded backoff.

## Dated v0.3.0 prepublication record

The following records the earlier preparation run, before the publication above.

Scope: local autonomous hardening on feat/v0.3.0-hardening. Root alone publishes a draft PR; no merge, main push, tags, releases, settings, secrets or Pages changes.

- Preserve schema_version 1 packets and report bytes. Version 2 adds baselines, optional checks, signatures and the unconfirmed status. Unconfirmed is review-needed exit 1, not a success.
- Equality defaults to recursive typed JSON equality; integers and floats are numerically equivalent, booleans differ from numbers. Range only compares finite numbers; contains checks array members using the same equality.
- Regex accepts anchored fixed-width patterns only, with a small whitelist and bounds. Reject ambiguous or unbounded complexity rather than claiming timeout guarantees.
- Baselines are explicit IDs in a separate array. Their timestamp must strictly precede the chosen final observation. The tool does not establish when an action actually ran; the caller owns that provenance.
- requires_change checks the addressed value, not unrelated state. A satisfied unchanged state returns unconfirmed / no observed change. Missing or incompatible baseline evidence returns unobserved.
- Optional local signature verification establishes the supplied bytes and named key, not the truth of state. Core remains dependency-free; Ed25519 support is an optional cryptography extra. Canonicalization supports an explicitly restricted RFC 8785 subset, with floats rejected for signing.
- Outputs use same-directory temporary files and per-file atomic replacement. Nonforce publication uses a hard link so a competing creation is never overwritten. Multiple outputs are not a transaction; filesystem failures can leave an earlier completed output.
- Lower the supported Python floor to 3.11 only after running its suite. Property tests, schema validation and type checks are dev dependencies.

- Existing release automation remains tag-only and uses OIDC with artifact attestations.
  Pages workflow is manual-only so merging the draft cannot deploy. No publication
  is authorized in this task. Hosted settings verification is root-owned.

## Release coordination decisions

Hosted link checks returned 404 only for the repository's maintainer-only security
settings URL. Keep its exact click path, exclude only that anchored URL from
anonymous lychee probes, and continue checking all public research/document links.
Read-only API checks separately established the disabled alerts/update settings.
No setting or credential was changed to make the check pass.

Pages deployment is manual-only so approving a merge does not also approve
hosting. A release tag starts trusted package publication, so the tag requires
both tag and registry publication authorization. npm first-publication bootstrap,
if needed, is a separate owner-approved publication using existing access; this
run does not create secrets or bypass registry setup.

## Siftgrain State redesign

This is an architectural extension across integration, presentation, and evaluation.
Retain the tested stdlib checker and schemas; add explicit adapters, a bounded
read-only MCP transport, and a self-contained report. A core rewrite would add
compatibility risk; a viewer-only update would leave integration gaps.

Display brand changes to Siftgrain State after the documented limited name search.
Package/import/repository identities remain stable. Canonical suite tokens are
vendored unchanged from claim-review; no independently published shared package.

Public trajectory fault labels are deterministic interventions on supplied
reservation snapshots, not human annotations or external full-task gold. Keep
archive transcripts out of Git, retain license/provenance, and generate local
downloadable splits and separate answer keys. Split by source task identity.
Missing native full-state goals cannot be reconstructed from hashes or rewards.
The native replay baseline is therefore unavailable; LLM judgment is omitted.

WebGL2 effects use an optional OffscreenCanvas worker because main-thread GPU
initialization caused material Lighthouse blocking time. A static surface remains
usable without GPU/worker support. Finite sweeps show existing evidence; CSS
settling and contradiction motion keep their supplied verdict meaning.

No WebGPU path: it adds no demonstrated need over this small WebGL2 field.
No new runtime dependency: optional signing stays optional; browser/audit tools
are development dependencies. No automatic package release is triggered.

Motion cancellation explicitly covers Web Animations API handles, because CSS
animation:none alone did not cancel an already running replay. Two failing
controller-contract tests reproduced pause/reduced-motion behavior before the
fix; both now pass. Cartoon settles with transform squash/stretch, Calm has a
small guarded pointer parallax on its decorative field, and Pixel uses a static
dither texture behind stepped motion. Text opacity remains unchanged.

## Retain source branches on delivery

On October 13, 2026, GitHub reported automatic branch deletion enabled. The coordinator changed only `delete_branch_on_merge` to `false` and verified the live readback, applying this repository's explicit feature-branch retention instruction. Other settings, protections, and Dependabot were unchanged.
