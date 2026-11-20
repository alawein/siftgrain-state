# Release readiness

## Verified v0.3.0 publication

[PR 16](https://github.com/alawein/outcome-check/pull/16) merged on October 8, 2026
at commit `66fea09ab87352224d3e01b65709392c3259e0ca`.
The [immutable tag](https://github.com/alawein/outcome-check/tree/v0.3.0),
[GitHub Release](https://github.com/alawein/outcome-check/releases/tag/v0.3.0),
[PyPI release](https://pypi.org/project/outcome-check/0.3.0/), and
[publish run 37799710726](https://github.com/alawein/outcome-check/actions/runs/37799710726)
are published successfully. Do not retry or replace that version.

## v0.4.0 delivery

[PR 17](https://github.com/alawein/outcome-check/pull/17) merged at immutable source
`6f026e2f59059c34dd53b496eb4ff973712d380d` on October 8, 2026.
The [v0.4.0 tag](https://github.com/alawein/outcome-check/tree/v0.4.0),
[PyPI release](https://pypi.org/project/outcome-check/0.4.0/) and
[GitHub Release](https://github.com/alawein/outcome-check/releases/tag/v0.4.0)
are public. [Release run 37824835131](https://github.com/alawein/outcome-check/actions/runs/37824835131)
succeeded on attempt 2. Attempt 1 uploaded successfully but its immediate registry
check saw an incomplete file listing. Before retrying failed jobs, the retained
canonical bytes were reconciled against PyPI and exact publisher/build provenance.
The recovery preflight verified existing files and skipped upload; the GitHub job
published the same distributions plus inventory.json and SHA256SUMS.

Verified canonical distribution SHA-256:

- `outcome_check-0.4.0-py3-none-any.whl`:
  `26f6fd325933c9f761ca01544182fb0ff64738e9cf9cac0f80eca4baae2e73ae`
- `outcome_check-0.4.0.tar.gz`:
  `385e5e70752bbfbb97de65deef509b36d9dae0d96962cef3682fe9eabf52c4dd`

The bounded registry visibility retry below is forward-only maintenance. It does
not alter the v0.4.0 source/tag, retained artifacts or published bytes. Do not retry
that successful release. Preserve prior feature branches, tags and assets. The
entire Dependabot family remains excluded from the authorized closeout.

`release.yml` starts only on a new `v*` tag whose commit is the current main tip
and whose version equals pyproject.toml. Build once with the frozen development
lock and Hatchling 1.32.4. Default runtime dependencies remain empty.
The build job checks tests, types, schemas, metadata and a fresh wheel install,
creates an exact two-file inventory, attests those files and retains them in the
`canonical-distributions` Actions artifact before registry authentication.
SHA256SUMS and inventory.json live in release-assets, outside dist.

The publish job downloads and verifies those retained files, reconciles PyPI, and
verifies each existing upload's digest, downloaded bytes and exact publisher
provenance. A matching partial upload resumes only its missing files through OIDC;
extra files, conflicting bytes or missing/foreign provenance fail closed. A fresh
`publish-dist` directory holds copies of only missing files. PyPA's generated
`.publish.attestation` sidecars stay there; retained dist and its inventory are
never modified or loosened. Already verified existing files are never uploaded again.
After publication the complete exact registry inventory is required. An incomplete
version listing (metadata HTTP 404 or missing files) is checked at most five times
with delays of 2, 5, 10 and 20 seconds, totaling 37 seconds of backoff. Network and
verification time is additional. Every visible file is reverified on each attempt;
checksum, extra/duplicate-file, download and provenance errors fail immediately.
Exhaustion fails closed. Preflight keeps its existing missing-only staging behavior.
Downloaded registry bytes must match, with build provenance constrained to the
repository, release workflow, source commit, tag and hosted runner. PyPI publish
attestations are cryptographically checked and their certificate claims bind the
repository, workflow, signer/source commit, tag and hosted runner. Only the final GitHub upload job
has contents:write. It uploads the same files and checksums and rejects conflicting
existing assets. After every asset passes final download/readback, retries also
reconcile an existing release body from the verified notes file. Asset mismatches
stop before any body edit. Its public release body is generated only after complete registry
byte and publisher-provenance verification, and includes the actual version, source,
tag and digests. It does not copy this checkout's preparation notes. Version-specific
historical notes and existing tags/assets remain unchanged. The bounded visibility
retry is locally tested maintenance for future release runs; the successful v0.4.0
recovery used its immutable original workflow.

Publication states must remain distinct:

- **Published successfully:** verify destination files and hashes, then stop.
- **Failed with a verified cause:** retain the build artifact and record that cause.
  Repair access/configuration as needed; rerun failed jobs using retained bytes.
  Reconcile the destination first because a timeout may have had an effect.
- **Not attempted:** no successful or failed external publication is claimed.

The current intended PyPI publisher identity is owner `alawein`, repository
`siftgrain-state`, workflow `release.yml`, environment `pypi`. On October 13, the
settings page redirected to sign-in; no publisher setting was read back or changed,
so the native binding remains unverified after the rename. Owner-entered interactive
authentication is an access requirement when needed, not a renewed authorization request.
Never expose a token or invent an alternative secret flow.

## Pages and security

Pages remains manual-only. The latest [deployment run](https://github.com/alawein/outcome-check/actions/runs/37828214231)
succeeded from source `6500ecf94692bfb818c2fe00ae3371d9dac67b88`. [Security settings](security-settings.md) describe supported controls
and report-only audits. Local checks do not prove those remote controls changed.
