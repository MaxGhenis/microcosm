WIC-FIX-COMPLETE

# WIC reconciliation dtype repair

Date: 2026-08-31

Branch: `stacked-dense-gate-sweep`

Lane base: `74acf94b`

Runtime-complete launcher repin SHA:
`b8d0980fd8e63b130fe235018b5af887976dda56`

The only later lane commit is this documentation-only `PROGRESS.md`/`out.md`
handoff; its SHA is reported in the final launcher message, so either commit
has the same runtime and generated-authority tree.

## Result

Implemented the binding Class-A minimal sound remedy exactly. WIC reconciliation
still derives deterministic values for the whole pool, but it now proves those
expected ASEC logical values equal the incumbent ASEC snapshot before any
write. It copies the incumbent Series and assigns expected values only at the
declared non-producer/ACS recipient positions. Nullable pandas `boolean`
storage and the physical ASEC cells are therefore preserved.

The existing post-write `Series.equals` guard, typed dtype hashing, receipt
validation, and fail-closed behavior are unchanged. No guard, gate, threshold,
or validator was weakened.

## Sibling audit

The complete `_apply_late_transfer_structural_reconciliation` registry contains
exactly WIC and education/AOTC. AOTC had the same whole-column redraw over five
nullable boolean source outputs, so it now uses the identical recipient-only
helper. Receipt validation rejects structural receipts on every other late
transfer group; there is no third callback to repair.

## Authority and checkpoint reuse

Both structural policies now state recipient-only assignment explicitly:

- WIC: stable-source-person expected values are assigned only to the
  target-specific complement of declared producer rows.
- AOTC: the positive-qualified-tuition predicate is assigned only to that same
  declared recipient scope.

The official generator changed only those policy/assignment strings in the US
imputation spec. Their hashes flow through late resource semantics, checkpoint
identity, stage identities, and per-target bank identity, so stale checkpoints
are invalidated by authority identity rather than manual carry-forward logic.
The final US spec SHA-256 is
`72a136ef233f748b0db15d2630f1ee702f34fcfb377b21f1a1e8163a575fcf4a`.

## Regression coverage

The production-shaped WIC regression composes the real guarded ASEC-only source
operator merge, ACS transfer, and structural reconciliation. It proves:

- source merge storage is nullable pandas `boolean`;
- ASEC values are complete while ACS recipient cells are initially null;
- the cold target-bank path is `rebuilt/missing`;
- the warm target-bank path is `checkpoint/resumed`;
- exact ASEC `Series.equals`, dtype, values, and typed SHA-256 are unchanged on
  both paths;
- reconciliation changes recipient rows and cold/warm final Series are exact;
- an adversarial ASEC logical-value mismatch fails before recipient assignment
  and leaves the input untouched.

The existing structural fixture now snapshots nullable storage before
reconciliation for WIC and all five AOTC outputs.

## Verification

| Check | Result |
| --- | --- |
| WIC/AOTC direct + adversarial + rebuilt/resumed corridor | 4 passed |
| US spec bundle, imputation, stacked authority, pool-tool identities | 220 passed |
| compiler/inventory/coverage/seed corridor | 42 passed |
| exhaustive spec-engine and country-spec sweep | 331 passed |
| repository-wide `pytest` | 7,610 passed, 83 skipped, 2,462 warnings; exit 0; 1:33:07 |
| repository-wide Ruff | green |
| CI test inventory | 315 tracked files; `verification=ok` |
| US generated bundle `--check` | green; spec SHA above |
| spec-engine coverage | 41,558/41,558 fields; 41/41 inventory checks |
| diff hygiene | `git diff --check` green |

Two aborted full runs exposed three stale seed-protocol goldens already present
at lane base. Archived execution proved the period-classifier's seed-attested
module edits had moved the shared protocol before this WIC lane: BE and UK
country-bundle hashes plus the rich-minimal loader hash were the only omitted
downstream vectors. They were re-pinned in isolated commits, with no runtime,
schema, gate, or country resource change. An exhaustive digest audit found no
fourth stale vector, and the 331-test sweep plus the final full suite are green.

## Commits

- `5b54c4195db2e978dce8f64ac764a606ecbdfee7` — start the WIC dtype repair journal
- `f650fc7d2ceb468b952907cf98368032f6239cc8` — record the late reconciliation audit
- `928e986e45e3fc7f50a8b8ac49db78508ee0039d` — record the production WIC failure prototype
- `9a4bab1681a6e44edc773968c560d606288a284c` — preserve nullable dtype in late reconciliation
- `b4852a2129d5ca61c501d27c497f6d3e3490b49b` — recut recipient-only reconciliation identities
- `2bb3148c7e31d5fe56ca42cda97b541b090f4d32` — test WIC reconciliation across target-bank reuse
- `c83046762647b5d81e29c1a908e191a5d5f9aa92` — refresh shared country spec-hash goldens
- `b8d0980fd8e63b130fe235018b5af887976dda56` — refresh the seed-bound loader golden

## Boundaries

No build, push, PR, publication, release, or candidate mutation was performed.
Candidate evidence remained read-only. No gate or threshold changed.
