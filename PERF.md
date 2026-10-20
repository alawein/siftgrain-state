# Performance and accessibility

Targets: local-file LCP below 2500  ms, interaction response below 200  ms,
approximately 60 fps main interactions, and a 32,768-byte gzip report budget.
These are measured in automated local runs, not certified for all hardware.

`npm test` blocks HTTP(S) and opens the actual file URL in Chromium, Firefox,
and WebKit. It runs axe 4.10.3 WCAG2/2.1/2.2AA tags for all four themes in both
appearances, rejects every reported violation, checks mobile width, labels,
keyboard-capable native controls, storage denial, reduced motion, and GPU fallback.
No automated tool alone establishes full WCAG conformance.

## Observed browser samples

| Engine | Local-file LCP ms | Event duration maximum ms | Active rAF median/p95 ms | GPU path |
| --- | --- | --- | --- | --- |
| chromium | 52 | 24 | 16.70/16.70 | webgl2 |
| firefox | 267 | 16 | 6.06/6.06 | webgl2 |
| webkit | 31 | 24 | 16.00/17.00 | static |

Each cadence sample contains 60 rAF deltas while replaying timeline state motion.
These are main-thread presentation cadence, not GPU profiler frame times or a
midrange-laptop certification. CI enforces median<=18 ms and p95<25 ms for this
finite smoke interaction, plus every observed event duration<200 ms. Event Timing
samples are not field INP; if no qualifying interaction entry appears, it is
unavailable. Engines may differ in LCP/Event Timing support. Exact raw local
results are in [docs/browser-results.json](docs/browser-results.json).

## Lighthouse and bytes

`npm run perf` runs Lighthouse 13.5.0 on the same report through an ephemeral
localhost server because Lighthouse navigation requires HTTP. No external assets
or network-enabled product path is introduced. The retained Lighthouse 12.8.2
candidate-source clean-clone measurement has performance score
0.97, accessibility 1, LCP 1002.00 ms,
total blocking time 0.00 ms. Field INP is unavailable in a navigation audit.
Local-file LCP comes from Playwright above, not the localhost Lighthouse run.

The October 19, 2026 local Lighthouse 13.5.0 run measured performance 0.97,
accessibility 1, LCP 955.175 ms and total blocking time 0 ms. These synthetic
measurements do not replace the retained 12.8.2 summary in
[docs/lighthouse-summary.json](docs/lighthouse-summary.json).

CI enforces Lighthouse LCP<2500 ms and accessibility 1.0, full axe checks,
active-cadence/event limits, and emitted report gzip<=32,768 bytes. The exact bytes
are printed by `uv run python scripts/check_perf.py`, which also verifies the
runtime CSS/logo embeds against their canonical sources. All assets are local.

WebGL2 runs in an optional OffscreenCanvas worker only after viewer interaction.
Initial rendering uses a static surface; no startup GPU context or idle render
loop. Finite 600 ms sweeps stop under reduced motion, pause, or hidden-page state.
Workers terminate on pagehide. Text remains full contrast during motion after an
observed opacity-fade contrast defect was fixed. No WebGPU layer is needed.

## Reproduce

```sh
uv run python scripts/build_demo.py
uv run python scripts/build_state_demo.py
uv run python scripts/check_perf.py
npm ci --ignore-scripts
PLAYWRIGHT_SKIP_BROWSER_GC=1 npx playwright install chromium firefox webkit
npm test
npm run perf
npm run lhci
node scripts/record-demos.mjs
```

Browser tooling is development-only. Playwright 1.62.1 release July 30, 2026;
axe 4.10.3 March 5, 2025 (npm time metadata read October 13, 2026). Direct
Lighthouse is pinned at 13.5.0; LHCI retains its nested 12.6.1.
npm/pip audits are report-only. No audit result is a security
certificate. Hardware identity is in RESULTS.md; remote CI timing is separate.

## Host contention and exact tooling

A prior shared-host WebKit replay sample had median 16 ms/p95 33 ms and correctly
failed the unchanged budget. A later same-context blank/app comparison under
reduced contention had p95 17 ms for each; the final full matrix above passed.
[Raw comparison](docs/webkit-cadence-comparison.json) is not a fully isolated
hardware certification. Other agent sessions were still active during the
diagnostic. No budget was relaxed to obtain a pass.

The named Lighthouse CI CLI is additionally pinned at @lhci/cli 0.15.1, released
June 25, 2025. `npm run lhci` uses its native collect and assert commands with
local static files, the same desktop viewport, LCP ceiling 2500 ms and
accessibility floor 1.0. It performs no upload. Collection is additive so prior
generated measurements are retained. Its final run is recorded with PR checks.

Native Lighthouse CI completed one local URL/run successfully: performance
0.95, accessibility 1, LCP 853.15 ms,
TBT 165.50 ms using Lighthouse 12.6.1.
Both configured assertions passed. [Native result](docs/lhci-results.json).

Final controller regression checks include immediate cancellation of active Web
Animations on Pause and reduced-motion changes, plus keyboard focus/Space
activation. A visible confirmed row is verified to have an active replay before
the final browser cadence window; replay is restarted at frames 20 and 40. This
avoids treating offscreen or paused animation as an active-interaction sample.
Offscreen effects are canceled through IntersectionObserver where available.

Final temporary-clone verification at 1bed622 passed all 27 browser observations. Direct Lighthouse measured LCP 1145 ms/TBT 335 ms/performance 0.82/accessibility 1.00. Native Lighthouse CI measured LCP 894.226 ms/TBT 196.5 ms/performance 0.92/accessibility 1.00 and passed its unchanged assertions. These additional results preserve load-sensitive variation rather than replacing slower measurements. See docs/final-verification.json.
