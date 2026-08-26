# Final report: PR #768 `origin/main` merge

> Intermediate checkpoint: while this fully green report was being prepared,
> the shared `origin/main` ref fast-forwarded from `f9d3b4838c13` to
> `bb796cb7ba57` with PR #743. The follow-on merge will supersede this report
> before owner handoff.

## Outcome

Local `origin/main` at `f9d3b4838c13` is merged into
`battery-residual-fixes`. Main's #742 typed F0 bundle and #763 spec/checkpoint
folds remain authoritative, while PR #768's behavioral change remains intact:
late `weeks_unemployed` carrier calibration no longer requires positive
unemployment compensation. The PUF-only QRF source rule that zeros weeks when
UC is unavailable is unchanged.

The resolved tree passes the complete memory-safe no-build suite and all
repository anti-rot checks. No build, push, certification, publication,
release mutation, gate tuning, or identity hand-edit occurred.

## Conflicts resolved

| Conflict | Resolution and justification |
| --- | --- |
| `FINAL_REPORT.md` | Resolved `--ours` because it is PR #768's owner-designated output journal. Main's unrelated report remains in main's history; this file is now rewritten with the merged verdict. |
| `PROGRESS.md` | Resolved `--ours` because it carries this branch's active state/done/next record. Main's unrelated lane state remains in its history. |
| `_LANE-NOTES.md` | Resolved `--ours` to retain PR #768's no-build evidence and owner handoff. A dated header now marks the residual material as historical after this merge. |
| `specs/us_imputation_lineage.yaml` | Accepted main's deletion because #742 superseded the root mirror with the typed F0 bundle and #763 moved later attested surfaces. Re-expressed the branch delta as `special_constraint: none` in the generator, regenerated the packaged typed spec, and removed the retired enum from the closed schema. This preserves both main's folds and the branch's weeks/UC decoupling. |

No conflict was semantically contradictory. The branch's runtime behavior and
regression auto-merged with main's spec engine; the live regression proves
late weeks calibration succeeds even when every UC carrier is zero.

## Anti-rot pins moved

All movers were derived first and then updated through the repository's own US
bundle and coverage tools.

| Attested surface | Previous | Merged |
| --- | --- | --- |
| Nested post-draw policy | `ff609afd95d8a1443a5c32b08dc9d444c439d802a77972158c355afc56955332` | `8326939889ba4036c191a9ab3347a3eae98527ad79b3abc9e9f98bfc58873aa3` |
| US typed-spec envelope | `5378bb9189aec96f50da22aac71e5bd2c3d919e9795f6ef2147e0bc9c739dd8e` | `57966f08b3d706dfba66885f120313d82b408ef81d5f33f25ef9e72f6d2a25e4` |
| Post-transfer authority component | `141519684c72ab84a077ae0f5716a0416f1e19da57262948e459633cbe560576` | `427438c2f3f4694e8cb45ff6ad381f6cc5ee60acb40a06977e3624814f6b234d` |
| Overall stacked authority | `3a980927227704d0589f246eef9cd825c2ae84f3a4134ac835e0e5ed39a563ac` | `bc3c640268127077cc1210bef138f05d3f432936737c508e29da7fd2b0d20cb8` |
| Full checkpoint identity | `a128a85f877fb32def9382b841b8b340f974e8a9148ac029c1f04becdc956c18` | `8b284b774a8a6eb211b0abc93b69297fdf4f997aa515d85d902de9d5e2812eac` |

The generated F0 coverage report and both US fixture spec literals moved with
those identities. Non-movers were checked rather than re-pinned: 42,120 field
uses (32,351 authored and 9,769 resolved), all 49 claims, the pointer inventory
`bc4a948ab632191954600da8474c5b011f977a65e24c399d126f3dc4a79f23e5`,
documentation identity, BE/UK spec envelopes, usage modes/effects, seed
identities, and compiler ABI remain unchanged. Coverage is 42,120/42,120 with
41/41 inventory checks.

## Verification

The required `uv sync --all-packages --extra us` ran before merge work. Because
the sandbox denied the default cache and network, it used a writable offline
cache seeded from the host's lock-compatible cache. After the merge, the same
method reconciled all 123 packages, including `policyengine-us==1.819.0` and
`policyengine-core==3.31.0`.

Final capped no-build results:

| Shard | Result | Peak RSS |
| --- | ---: | ---: |
| calibrate | 203 passed | 0.444 GiB |
| data | 318 passed, 2 skipped | 0.742 GiB |
| fit | 93 passed | 0.721 GiB |
| frame | 295 passed, 36 skipped | 6.757 GiB |
| build A | 4,263 passed, 37 skipped | 10.637 GiB |
| build B | 2,175 passed, 3 skipped | 13.242 GiB |
| **Total** | **7,347 passed, 78 skipped** | **13.242 GiB maximum** |

The focused semantic/identity matrix passed 116 tests at 2.648 GiB. After an
earlier long Build-B attempt emitted four failures in the main-identical trade
range and lost its terminal trace when the session closed, all 125 mapped trade
tests passed and the complete order-preserving Build-B rerun passed with a
clean JUnit record. No code or expectation was changed to obtain that result.

The following final checks also pass:

- `generate_us_bundle_from_constants.py --check` at US spec
  `57966f08b3d706dfba66885f120313d82b408ef81d5f33f25ef9e72f6d2a25e4`;
- `spec_engine_coverage.py --check` at 42,120/42,120 and 41/41;
- US/BE/UK country-envelope digest checks;
- repository-wide Ruff; and
- `git diff --check`.

## Remaining risk and owner handoff

- A direct final fetch could not resolve GitHub DNS. The merged local
  `origin/main` is `f9d3b4838c13`, and its reflog records a same-session
  fast-forward fetch before this lane began, but remote equality could not be
  independently re-proven inside the sandbox.
- The first Build-B trade-test failure burst did not reproduce in either the
  focused 125-test run or the full 2,178-outcome rerun. The clean rerun is the
  final verdict, but the transient is recorded here for hosted-CI comparison.
- Wheel/platform builds and the serial-host pool/certification path were not
  exercised, as required by the no-build order. Hosted CI and the owner retain
  those gates.
- The branch is deliberately unpushed. The owner reviews and pushes it.
