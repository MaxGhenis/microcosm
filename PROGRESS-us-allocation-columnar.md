# US allocation columnar artifact (v2 encoder/decoder) — 2026-09-13

Lane: `microcosm-us-allocation-columnar-20260913`, branch
`us-allocation-columnar-20260913`. Base: fresh `origin/main` `15ebde806`,
fast-forwarded to the compatible continuation `a96fc850942d3fd96d24251c07d9ebc38b79f8de`.

Scope: source-only. A compact, deterministic, versioned **v2 private columnar**
allocation encoder/decoder beside the existing row-wise JSON v1 payload in
`graph_survey_population._allocation_payload`, plus an integration proposal. The
default v1 host is byte-for-byte unchanged; no format switch is propagated to
any owner. No push, merge, deploy, native build, test execution or performance
claim.

## State

Complete and local, source-only. The codec baseline for this repair is
`2419e65f411daf2cbd9baa66fe15c68639f11987` (an earlier line here mistyped
it with an extra `d`); the successor coverage pass continued from
`4a8fe60dd96e33089f4d15980fc61c2a3328c69a` on the same branch.
The inherited rational-domain gap is repaired in both encoder and decoder, and
the independent review's two coverage findings are now closed in the test file.
Production codec bytes are unchanged by the successor pass.
No tests have been collected or run.

Tests are **UNRUN**: counted by stdlib `ast` over the test file only, 76 test
functions and 188 parametrized cases, never collected or executed in this lane.
The codec baseline carried 71 functions / 172 cases; the domain repair added
3 functions / 9 cases; the successor coverage pass added 2 functions / 7 cases.
One case asserts a byte count and is held for a separately reviewed root guard.

## Done

- Traced the v1 payload, its consumers, the maintained store/Frame codecs, the
  repo's bounded-binary idiom, the CI test partition and the artifact-type and
  implementation-identity machinery before any edit.
- Established that no maintained codec can carry this artifact: `ContentStore`'s
  typed-column codec is directory-based, and a kernel only ever receives plain
  bytes. Reused `microcosm.graph.canonical.canonical_json` for the header, which
  is the one maintained codec whose API fits.
- Added `microcosm/build/us_runtime/survey_allocation_columnar.py`: bounded
  streaming encoder, re-proving decoder, and a public manifest that carries no
  native identifier or row value.
- Refused a zero inclusion probability on both sides, which previously would
  have raised `ZeroDivisionError` out of the module.
- Added `packages/microcosm-build/tests/test_us_allocation_columnar.py`.
- Enforced v1's `0 < share <= 1` and `0 < inclusion_probability <= 1` domains
  on both sides, including before derived multiplier/weight checks.
- Added authored lower/upper-bound, double-negative, zero-anchor, and
  repaired-checksum decoder tampering regressions.
- Closed the independent review's two coverage findings, source-only:
  `test_decoder_rejects_negative_rationals_a_zero_anchor_would_mask` (3 cases:
  negative share, negative probability, both negative) rewrites the anchor to
  zero and repairs the derived multiplier cell, the float weight cell, every
  column digest and the envelope checksum, so the refusal it asserts is the
  domain and not stale integrity metadata; and
  `test_the_closed_upper_bound_and_a_small_rational_are_accepted` (4 cases)
  accepts `share == 1`, `inclusion_probability == 1`, both interior mixes and
  a small `1/1000` share, which the helper defaults of `1/2` and `2/7` never
  exercised. Both remain UNRUN.
- Removed the unsolicited `FINAL_REPORT-us-allocation-probability-bounds-*.md`
  from the change set; it had recorded a mistyped predecessor SHA and a
  boundary-1 coverage claim the source did not support. Its own commit
  (`4a8fe60dd`) stays in history.
- Added `docs/us-allocation-columnar-v2.md` and the changelog fragment.
- Ran a five-lens adversarial review over the codec and the unrun tests and
  closed every confirmed defect: a source-codebook relabel the ordering digest
  did not catch, a manifest that republished provenance digests without
  verifying the envelope seal, a `payload_sha256` confirmation oracle in that
  manifest, a surrogate lexeme escaping as `UnicodeEncodeError`, float
  spellings of the version fields giving one document two byte forms, and a
  rational width bound narrower than v1's own. No unrun test was found that
  would fail; one that could have passed for the wrong reason was anchored.
- Static checks: `ruff check` and `ruff format --check` clean on both new files;
  `tools/ci_test_groups.py --verify` prints `verification=ok` with the new test
  in `fast:rest` and `engine:us-am`, never `[defaulted]`.

## Next

Root review is the next action. Static checks in the successor pass were
`ruff check` and `ruff format --check` (both clean on the test file, ruff
0.15.0 direct binary), a stdlib `ast` recount, and `git diff`; no `uv`,
dependency resolution, project import, test collection or execution, network
or data access was used or attempted. All 188 cases remain UNRUN; no
performance/capacity claim or host integration is in scope.

The preparation payload's own 64 MiB cap is untouched and unrelieved by this
work; it remains the other ceiling on the same path.
