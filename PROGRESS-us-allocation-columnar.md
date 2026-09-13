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

Complete and local, source-only. Baseline confirmed clean at
`2419e65f411dafd2cbd9baa66fe15c68639f11987` on the fresh requested branch.
The inherited rational-domain gap is repaired in both encoder and decoder.
No tests have been collected or run.

Tests are **UNRUN**: 74 test functions, 181 parametrized cases, never collected
or executed in this lane. One of them asserts a byte count and is held for a
separately reviewed root guard.

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

Run the final static AST/hash/Ruff/diff checks and write the concise handoff to
`FINAL_REPORT.md`. All 181 cases remain UNRUN; no performance/capacity claim or
host integration is in scope.

The preparation payload's own 64 MiB cap is untouched and unrelieved by this
work; it remains the other ceiling on the same path.
