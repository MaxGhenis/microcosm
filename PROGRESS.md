# Battery package 1 progress

## State

In progress on branch `battery-pkg1-puf-tax`: the pure, deterministic weighted
carrier/sign, conditional-magnitude, and Schedule-D joint-parent kernels are
implemented and verified by the complete suite. Integration into the exact
38-check PUF-tax surface and terminal pool derivation is next. No frozen gate
parameter has changed.

## Done

- Ran the required `uv sync --all-packages --extra us`. The default cache was
  denied by the managed filesystem; a retry with a writable cache reached
  dependency resolution but outbound DNS blocked the missing `msgpack` wheel.
- Read the complete battery adjudication and all 39 assigned machine-readable
  rows from the read-only `microcosm-arm-split` worktree.
- Read every assigned mechanism citation in `acs_transfer.py` and
  `stacked_spine.py`; the frozen comparator separately measures weighted sign
  incidence and conditional absolute-amount quantiles.
- Confirmed the named remedy must change the transfer artifact, not the frozen
  incidence band, QED ceiling, quantiles, seeds, folds, or comparators.
- Established a green full-suite baseline: 6,509 tests collected and pytest
  exited 0 using the locked `microcosm-arm-split` environment with this
  worktree's five `src` trees on `PYTHONPATH`. The long-running 44% block was
  traced to expected real PolicyEngine-US memory regressions.
- Extracted the exact registry: 20 continuous targets representing 15
  incidence/carrier checks and 23 conditional-amount checks (38 total).
- Added pure array kernels that separate weighted carrier/sign allocation from
  sign-preserving weighted inverse-ECDF amount mapping. Immutable and
  zero-weight rows are preserved; infeasible support and malformed IDs or
  weights fail closed with capacity/error receipts.
- Added a preservation-specific Schedule-D kernel that byte-preserves the
  long-term parent and permits only exact-equal-weight positive/zero swaps.
  This preserves the weighted non-Schedule-D carrier margin and conditional
  value distribution exactly while projecting unattainable joint targets into
  a disclosed feasible interval.
- Corrected conditional magnitude ranks to include immutable native carriers
  in the final-domain denominator and ordering, while leaving their bytes fixed.
- Added 37 focused behavioral test cases across the two kernels; all pass. The
  complete 495-case runtime source-blindness module and Ruff also pass.
- Reran the complete repository suite after both audit-driven corrections;
  pytest reached 100% and exited 0 with only the established warnings/skips.

## Next

- Integrate the exact 38-leg registry into both banked and non-banked transfer
  paths, then call the preservation-specific Schedule-D reconciliation before
  terminal derivation.
- Run the PR-CI suite and the required off-chain 1% before/after builds with
  sample fraction `0.01` and sample seed `578`, staying below 15 GiB RSS.
- Record code-cited mechanism notes and per-check measurements in
  `_LANE-NOTES.md`, then write the final report to `FINAL_REPORT.md`.
