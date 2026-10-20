# Security controls

The October 8, 2026 closeout authorizes supported security configuration while
excluding the entire Dependabot family: alerts, security updates, version-update
configuration and its PR automation remain unchanged. There is no instruction to
enable those features.

Existing CI runs `pip-audit --local` as a report-only check. It reports known
vulnerabilities in installed development dependencies; it is not a clean-security
certificate. The product has zero default runtime dependencies. Optional signing
uses cryptography. Lock review, full-SHA action pins, protected main, least-privilege
job permissions, OIDC, provenance checks and immutable release hashes provide
separate controls. Root verifies any authorized hosted settings after applying them.

Current root readback confirmed secret scanning and push protection enabled;
Dependabot alerts and security updates remain disabled. No control change was
needed. These are hosted observations, not claims from local preparation.

The read-only prepublication check on October 8 found vulnerability alerts and
automated security fixes disabled. That is a dated observation, not a new request
to change them. The exact maintainer page is
<https://github.com/alawein/siftgrain-state/settings/security_analysis>.
Its narrow anonymous-link-check exception remains because GitHub returns 404 to
anonymous readers; public citations and release links remain checked.

[Release readiness](RELEASE_READY.md) records the successful v0.3.0 trusted
publication and the new workflow. Never rotate or expose a token to work around
registry authentication.

## October 13 observation and optional restoration

Read-only API returned Dependabot security updates disabled, vulnerability alerts
HTTP404 with GitHub's explicit disabled message, and secret scanning/push protection
enabled. No settings were changed. The entire Dependabot family remains off by
owner instruction; restoration requires that instruction to change.

Optional exact owner click paths: repository Settings -> Security -> Advanced
Security (or Code security and analysis) -> Dependabot alerts -> Enable; then
Dependabot security updates -> Enable. Version-update PRs separately require
a reviewed `.github/dependabot.yml`; no such configuration is added here.
The current maintainer URL above is the destination, not proof of permissions.

Browser-only development tools now also use `npm audit --json` in report-only
CI. Audit findings do not change zero-default-dependency Python runtime scope.
Do not blindly apply audit fix --force or enable Dependabot to clear reports.

The pre-update development-tool audit snapshot reported 36 npm findings (2 low,
23 moderate, 11 high) after adding the requested native Lighthouse CI CLI.
The October 19, 2026 Lighthouse 13.5.0 update reduced that package-finding total
to 17 (2 low, 4 moderate, 11 high, 0 critical). The audit still labels direct
Lighthouse and both LHCI Lighthouse paths through aggregate Puppeteer findings;
the reduction does not establish exploit reachability or a clean dependency path.
These are development-only dependencies; no claim of a clean browser-tool audit
is made. The Python dependency snapshot reports no known vulnerabilities; the
unpublished development package itself is skipped by the public vulnerability
registry. Both jobs remain report-only, with no forced dependency upgrade.
