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

Complete and local. Five commits. The codec, its tests, the changelog fragment
and the integration proposal are in the tree; nothing calls the new module, so
no declaration, node key, spec digest or implementation identity moves.

Tests are **UNRUN**: 61 test functions, 152 parametrized cases, never collected
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
- Added `docs/us-allocation-columnar-v2.md` and the changelog fragment.
- Static checks: `ruff check` and `ruff format --check` clean on both new files;
  `tools/ci_test_groups.py --verify` prints `verification=ok` with the new test
  in `fast:rest` and `engine:us-am`, never `[defaulted]`.

## Next

Root's call. An opt-in host integration is a separate, reviewed change; its full
cost — the three consumers that parse the bytes, the artifact type bump, the
implementation-inventory edit that moves every US stage hash, and every recorded
`allocation_sha256` — is written up in `docs/us-allocation-columnar-v2.md`.

The preparation payload's own 64 MiB cap is untouched and unrelieved by this
work; it remains the other ceiling on the same path.
