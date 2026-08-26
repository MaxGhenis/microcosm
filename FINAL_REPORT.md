# Final report: PR #768 `origin/main` merge

## Outcome

Local `origin/main` at `bb796cb7ba57` is merged into
`battery-residual-fixes`. The merge happened in two coherent steps because the
shared remote-tracking ref advanced while the first verified merge was being
closed:

- `4e16e9c7` merged the then-current `f9d3b483`, resolved all four conflicts,
  re-pinned the US anti-rot chain, and passed 7,347 tests with 78 skips.
- The commit containing this report merges the path-disjoint PR #743 delta at
  `bb796cb7`; it had no conflict, no US semantic overlap, and passes 7,419 tests
  with 78 skips on the final tree.

Main's #742 typed F0 bundle and #763 spec/checkpoint folds remain authoritative,
while PR #768's behavior remains intact: late `weeks_unemployed` carrier
calibration no longer requires positive unemployment compensation. The
PUF-only QRF source rule that zeros weeks when UC is unavailable is unchanged.
PR #743 adds its UK calibration/readiness semantics without touching that US
path.

No build, push, certification, publication, release mutation, gate tuning, or
identity hand-edit occurred.

## Conflicts resolved

The first merge had exactly four conflicts; each resolution is justified in
the `4e16e9c7` merge body.

| Conflict | Resolution and justification |
| --- | --- |
| `FINAL_REPORT.md` | Resolved `--ours` because it is PR #768's owner-designated output journal. Main's unrelated report remains in main's history; this file now carries the final merged verdict. |
| `PROGRESS.md` | Resolved `--ours` because it carries this branch's active state/done/next record. Main's unrelated lane state remains in its history. |
| `_LANE-NOTES.md` | Resolved `--ours` to retain PR #768's no-build evidence and owner handoff. A dated header marks the residual material as historical after the merge. |
| `specs/us_imputation_lineage.yaml` | Accepted main's deletion because #742 superseded the root mirror with the typed F0 bundle and #763 moved later attested surfaces. Re-expressed the branch delta as `special_constraint: none` in the generator, regenerated the packaged typed spec, and removed the retired enum from the closed schema. This preserves both main's folds and the branch's weeks/UC decoupling. |

No conflict was semantically contradictory. The follow-on `bb796cb7` merge
was automatic and conflict-free. Its only shared runtime change has UK-only
callers; “UC” in PR #743 means UK Universal Credit, not US unemployment
compensation.

## Pins moved

All local movers were derived first and then updated through the repository's
own US bundle and coverage tools.

| PR #768 attested surface | Previous | Merged |
| --- | --- | --- |
| Nested post-draw policy | `ff609afd95d8a1443a5c32b08dc9d444c439d802a77972158c355afc56955332` | `8326939889ba4036c191a9ab3347a3eae98527ad79b3abc9e9f98bfc58873aa3` |
| US typed-spec envelope | `5378bb9189aec96f50da22aac71e5bd2c3d919e9795f6ef2147e0bc9c739dd8e` | `57966f08b3d706dfba66885f120313d82b408ef81d5f33f25ef9e72f6d2a25e4` |
| Post-transfer authority component | `141519684c72ab84a077ae0f5716a0416f1e19da57262948e459633cbe560576` | `427438c2f3f4694e8cb45ff6ad381f6cc5ee60acb40a06977e3624814f6b234d` |
| Overall stacked authority | `3a980927227704d0589f246eef9cd825c2ae84f3a4134ac835e0e5ed39a563ac` | `bc3c640268127077cc1210bef138f05d3f432936737c508e29da7fd2b0d20cb8` |
| Full checkpoint identity | `a128a85f877fb32def9382b841b8b340f974e8a9148ac029c1f04becdc956c18` | `8b284b774a8a6eb211b0abc93b69297fdf4f997aa515d85d902de9d5e2812eac` |

The generated F0 coverage report and both US fixture spec literals moved with
those identities.

PR #743's already-reviewed incoming pins were retained exactly rather than
locally re-pinned:

| Incoming UK/data surface | Previous | Final |
| --- | --- | --- |
| UK typed-spec envelope | `e3b171bdaae1bdfe842e61c129fd279a6b29001cdef4c18de51823768911ec8c` | `0c85845b4d463638ae3e5c5a25e17de8b720794e3653c5991dc4f069d95762d3` |
| UK gate manifest | `f2cc2af4ae41b3e84e0d7a6e8a1a4480fd0aa5f034b9e8eeefe8e0c2bc40d239` | `4f66eea7e593b795da93217e9ac8b3b53ca1f82375ec346b3a2ecbb558b89cb6` |
| UK gate spec fingerprint | `3601b4c77b5672205e14435d4833412f55a6b4bbabd5bbd2b6e33b29a63bf74e` | `26fdbcccfaa01e9afa116339cfaa870f76fc6ed3bd5db57fec498781ff3efc64` |

The UK gate policy remains
`623f340ddde6f705717c3a6306522f8cf46c1c17a067f9e89df190ecc690f0fc`.
Independent runtime projection matches both moved UK/data pins.

Non-movers were checked rather than re-pinned: 42,120 US field uses (32,351
authored and 9,769 resolved), all 49 claims, the US pointer inventory
`bc4a948ab632191954600da8474c5b011f977a65e24c399d126f3dc4a79f23e5`,
US documentation identity, BE envelope
`86143c1c3f98980e34490c75706fe7dbf72e96e8accb8d7d4bbd2c1ae1a29b65`,
usage modes/effects, seed identities, and compiler ABI remain unchanged. F0
coverage is 42,120/42,120 with 41/41 inventory checks.

## Verification

The required `uv sync --all-packages --extra us` ran before merge work. Because
the sandbox denied the default cache and network, it used a writable offline
cache seeded from the host's lock-compatible cache. The final merged tree
resolves all 123 packages, including `policyengine-us==1.819.0` and
`policyengine-core==3.31.0`.

Final capped no-build results for the exact `bb796cb7` merge tree:

| Shard | Result | Peak RSS |
| --- | ---: | ---: |
| calibrate | 203 passed | 0.444 GiB |
| data | 318 passed, 2 skipped | 0.750 GiB |
| fit | 93 passed | 0.808 GiB |
| frame | 295 passed, 36 skipped | 6.781 GiB |
| build A | 4,335 passed, 37 skipped | 11.478 GiB |
| build B | 2,175 passed, 3 skipped | 13.217 GiB |
| **Total** | **7,419 passed, 78 skipped** | **13.217 GiB maximum** |

The combined PR #743 changed-surface and PR #768 identity/behavior matrix
passed 627 tests with 1 skip at 2.373 GiB. The first merge's focused
semantic/identity matrix passed 116 tests at 2.648 GiB.

An earlier pre-commit Build-B attempt emitted four failures in main-identical
trade tests and lost its terminal trace when that long session closed. No code
or expectation was changed: all 125 mapped trade tests passed, then both the
first merge's complete Build-B rerun and the final tree's complete Build-B run
passed in natural order. Both clean runs carry JUnit records.

The following final checks also pass:

- `generate_us_bundle_from_constants.py --check` at US spec
  `57966f08b3d706dfba66885f120313d82b408ef81d5f33f25ef9e72f6d2a25e4`;
- `spec_engine_coverage.py --check` at 42,120/42,120 and 41/41;
- country envelopes at US `57966f08...`, BE `86143c1c...`, and UK
  `0c85845b...`;
- repository-wide Ruff; and
- `git diff --check`.

## Remaining risk and owner handoff

- A direct fetch from this sandbox could not resolve GitHub DNS. A separate
  same-session fetch advanced the shared `origin/main` ref to `bb796cb7` at
  22:23+02, and the ref remained identical immediately before closeout, but
  remote equality could not be independently re-proven afterward.
- The first Build-B trade-test failure burst did not reproduce in the focused
  125-test run or either subsequent full Build-B rerun. The two clean full
  reruns are the final verdict, but the transient is recorded for hosted-CI
  comparison.
- Wheel/platform builds and the serial-host pool/certification path were not
  exercised, as required by the no-build order. Hosted CI and the owner retain
  those gates.
- The branch is deliberately unpushed. The owner reviews and pushes it.
