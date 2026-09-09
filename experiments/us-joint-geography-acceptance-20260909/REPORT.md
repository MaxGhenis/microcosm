# Joint geography source acceptance — 9 September 2026

The schema v2 PUMA ladder retains actual `(PUMA, tract, district, population)`
cells from the block join. Assignment makes one joint draw and derives county
from the selected tract. Observed ACS PUMA, ASEC state, deterministic seeds
and the coarse assignment across the tract-export flag are preserved.
Marginal-only schema v1 requires a source rebuild. The independent joint
support gate checks all rows and stays separate from the existing NYC mass
gate and national/CD calibration.

All **64 invented tests and their runtime guard passed**: 4.356 seconds wall,
4.013 seconds CPU, 329,826,304 bytes peak RSS, one native thread, no child or
network operations, no resource-content permissions or reads, no skips,
and no unknown or excess refusals. The exact ordinary run was
`/private/tmp/us-joint-geography-final-invented-root-20260909`.

- Receipt SHA256: `1b4835b6ee8bde7a487f119581f96344ebf514c422d86c9249532396bad85392`.
- Independent external rehash of 38 source/runtime/config/owned/executable pins:
  `4b19ddf5e914ef89799c0e40fa7baedb74f9475472092b76b3448a5dbec0fa6e`.
- Final execution packet manifest:
  `c5f4805e5c764838c299c6535f9daf7a3f6842e841bc7fe02348f866e1aae795`.

The controls cover crossed county/district pairs, preserved survey geography,
exact joint-to-marginal counts, live-array mutation, tract nesting, vintage
errors, schema refusal and complete small invented offline CLI assembly.
Eight CLI cases exercise real parsers and the maintained tool, including
source-envelope errors and mutations after source parsing. Four existing
multispine fixture constructors were updated with explicit invented joint
cells; their broader engine/HDF suites were not run in this bounded check.

The first independent review found that a direct or mutated ladder could
place one tract in two PUMAs while preserving every marginal. The common
validator now refuses that corruption, with assignment and gate regressions.
The follow-up independent source review is clean; its SHA256 is
`9f87cbffa2c2e722ac8031daa5acd284936d67ee785880918a69a673c2811228`.

The fresh-main eager US facade initially tried to load unrelated SOI metadata.
That access was refused before reading. The root authorized integrating the
accepted lazy facade as a real source change. Its mechanism matches accepted
W source by AST; all 904 main public names, their order, 80 module owners,
BuildConfig and plan contents are preserved, including the new joint gate.
W-only checkpoint exports and operator-contract redirects were not imported.

Earlier probes remain preserved. Actual-path pytest collection was refused
when it tried to enumerate `/Users`; owned-copy collection was restored.
Argparse's eight new calls produced 24 additional requests to the same denied
locale metadata path. After exact argparse/gettext review, the root approved
raising that reporting ceiling from 12 to 36 while keeping the path denied.
A generated guard count typo was caught before project imports and corrected.
These failures were not accepted as successful executions.

The source tool now streams archive/text lines and accepts an exact pinned
local input manifest that disables downloads and verifies source and manifest
identity before and after parsing. No actual crosswalk payload was read,
hashed or parsed during this acceptance. A metadata-only inventory found all
53 expected named cache files (1,336,231,055 bytes), but no corresponding
default acquisition summary. Source authentication, genuine crosswalk
assembly, current graph gate composition and national/CD release checks remain
required before a data artifact is releasable. No release or deployment is
claimed by these code controls.
