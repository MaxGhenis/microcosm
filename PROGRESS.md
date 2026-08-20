# Battery package 1 progress

## State

In progress on branch `battery-pkg1-puf-tax`: designing the adjudicated
sign/carrier hurdle and conditional-amount quantile calibration for the 38
`puf_tax_sign_hurdle_and_quantile_calibration` checks, plus joint-parent
reconciliation for the one Schedule-D check. No implementation or frozen gate
parameter has changed yet.

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

## Next

- Add pure-helper behavioral tests and implement deterministic weighted
  carrier selection plus conditional magnitude transport.
- Integrate the exact 38-leg registry into both banked and non-banked transfer
  paths, then add the four-state Schedule-D parent reconciliation.
- Run the PR-CI suite and the required off-chain 1% before/after builds with
  sample fraction `0.01` and sample seed `578`, staying below 15 GiB RSS.
- Record code-cited mechanism notes and per-check measurements in
  `_LANE-NOTES.md`, then write the final report to `FINAL_REPORT.md`.
