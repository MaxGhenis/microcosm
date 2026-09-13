# Final report: v2 rational-domain repair

Status: complete, source-only, local; nothing pushed and no host integration.

- Confirmed baseline: branch `us-allocation-probability-bounds-20260913`, clean
  HEAD `2419e65f411dafd2cbd9baa66fe15c68639f11987`.
- Enforced inherited v1 domains in encoder and decoder:
  `0 < share <= 1` and `0 < inclusion_probability <= 1`.
- Added regressions for lower/upper bounds, double-negative cancellation,
  zero-anchor masking, and decoder tampering with repaired column digests and
  envelope checksum. Valid boundary-1 and small rationals remain covered.
- Wire format, v1 producer/consumers, bounds, identities, and valid bytes are
  unchanged. The independent v1 Unicode issue was not touched.
- AST parsing passed; direct Ruff check and format check passed; diff check
  passed. `uv run` was not usable offline because its uncached environment
  attempted a network dependency fetch; no tests were collected or run.
- Exact authored test inventory by AST: 74 test functions, 181 cases,
  all **UNRUN**. No performance or capacity claim.

Commits: `9c5e55567`, `4dbae3a86`, `ab1f56918`, plus this report commit.
