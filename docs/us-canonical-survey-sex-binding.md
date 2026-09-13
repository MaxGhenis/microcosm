# Canonical survey sex: source projection and binding

`current_survey_sex.py` qualifies the canonical `is_female` leaf for every
selected original person of both survey arms. `graph_current_survey_sex.py`
declares a two-node fragment that carries the qualified rowwise observations on
a private branch and writes exactly one leaf on a receiving post-clone
population. Neither module is wired into the accepted country enrichment host,
and neither changes an existing declaration, cache key, source contract or
output contract.

## What each arm actually observes

| Arm | Value | Allocation | Knownness |
| --- | --- | --- | --- |
| ASEC | `A_SEX` 1 = male, 2 = female, as printed | `AXSEX` 0 = no change, 4 = allocated, as printed | Binding needs **both** codes printed. An unprinted `A_SEX` leaves the person unbound with reason `sex_code_outside_printed_codes`; an `AXSEX` inside the printed 0:4 range but not named (1, 2, 3) leaves the person unbound with reason `allocation_flag_outside_printed_codes`. |
| ACS | `SEX` 1 or 2, the only codes the current source modules admit | **Not observed** | Code and value knownness are true for a successfully issued row. Allocation knownness is false. |

Both the states and their labels come from `asec_demographic_source`
(`SEX_BINDING_STATES`, `SEX_UNBOUND_REASONS`, `SEX_ALLOCATION_STATES`) and are
pinned, not restated: `_shared_code_tables()` refuses if the owner's tables move.
Allocation is classified independently of sex binding, exactly as that owner
classifies it, so an allocated flag on an unprinted sex code stays allocated and
the person stays unbound.

The ASEC arm is read through `qualify_current_asec_demographics`, and every raw
code is reclassified here and compared against the states, knownness, universe
and origin label that projection published. The ACS arm is read from the issued
native coverage Frame after `verify_acs_native_coverage`, and the recorded
relation `is_female == (SEX == 2)` is verified against that live Frame rather
than assumed from `acs_inputs`.

## What is deliberately not claimed

- **ACS allocation provenance is unresolved.** No `FSEXP` column exists anywhere
  in this runtime's declared ACS readset. An absent allocation flag is not a
  male value and not an invented "not allocated" code. The ACS origin label is
  `census_published_acs_allocation_unresolved`; the word "unallocated" is never
  used, and `unallocated_observation_claim` is false in every receipt.
- **The two surveys do not carry equivalent allocation evidence today.**
  `equivalent_allocation_evidence_claim` is false in the contract and in every
  binding receipt. Supplying real ACS allocation evidence is a separate,
  separately reviewed source projection; requiring it would hold ACS binding
  pending that projection, not delete the existing source observation.
- **No printed ACS dictionary page was read by this lane.** The admitted ACS
  codes are pinned to the current source modules (`acs_pums` admits `{1, 2}`;
  `acs_inputs` records `SEX == 2`), and the contract records
  `printed_dictionary_page_read_by_this_lane: false`.
- **No age gate, headship inference, default, learned value or carried
  fallback.** An unresolved cell stays null. The historical composed-stage
  unbound guard in `graph_composed_asec_binding.py` is untouched.

## The fragment

| Node | Meaning |
| --- | --- |
| `survey_sex.source_projection` | A CREATE node on a private branch of the retained preparation Frame. It keeps the original support, design weights, strata, metadata and mass log, adds the namespaced `sex_source_*` columns, and emits the rowwise table as the private typed artifact `microcosm.us.current_survey_sex_projection@1`. |
| `survey_sex.bind` | Owns exactly `person.is_female` on the receiving population. It consumes the typed projection, an explicit `after` ordering edge, and the four declared lineage columns, and emits the typed `microcosm.us.current_survey_sex_binding@1` aggregate receipt. |

Private rowwise codes, identities and reasons live only in the typed projection
artifact and on the private branch. Public graph receipts carry the closed
aggregate set `current_survey_sex.PUBLIC_RECEIPT_KEYS` — counts, digests,
contract references and closed flags — and nothing else.

## Binding rules

Each qualified original person is mapped onto exactly its two initial clones by
`person_source_id`, with `person_spine_source_id` and `person_support_channel`
checked against the qualified row and `(source id, clone index)` required unique
over `{0, 1}`. Integers never travel through a float, so identities above 2\*\*53
are exact.

- An absent canonical column is **created** as a nullable Boolean.
- An existing column is a **declared full-column rewrite** at the incumbent's own
  storage. Every already-known cell is preserved and verified equal to its
  qualified source-bound observation; a matching incumbent is not treated as
  authoritative from equality alone.
- Only null cells whose source binding is known are filled. Both clones receive
  the same original observation; there is no redraw.
- A known incumbent that conflicts with its qualified observation refuses
  (`CANONICAL_CONFLICT`). A known incumbent without a current qualified binding
  refuses (`KNOWN_ASEC_INCUMBENT_UNBOUND` for the ASEC arm,
  `KNOWN_INCUMBENT_WITHOUT_QUALIFIED_BINDING` otherwise). Neither erases nor
  silently relabels the supplied value.

## Host integration is a separate, reviewed step

The fragment is exercised independently, by a tiny graph over invented values
and the real compiler, executor, ContentStore and replay comparison. Adopting it
in the accepted country host is not done here and needs, at minimum:

1. **An explicit host extension.** The host must declare these two nodes, supply
   the real typed ancestry through `country_host_edges()` with matching
   `host_pins`, and pass the actual receiving version — not the original clone
   version.
2. **A receiving version with a base, if the leaf already exists.** A rewrite
   inside a CREATE version is refused at compile time, so the host must place the
   bind node in a version opened by a later structural node (full cloning and
   atomic geography already open such versions). For a post-38 successor, the
   real `survey_property.tax_leaf_gate` verification artifact is an available
   ordering edge.
3. **A declarable incumbent storage.** The canonical dtype is taken from the
   receiving Frame through the graph's `token_for_dtype`. If the incumbent
   column is neither `bool` nor `boolean` — for example an object column
   produced by a column union that null-filled one arm — the fragment refuses
   with `INCUMBENT_DTYPE_NOT_DECLARABLE` rather than coercing it. Resolving that
   storage is a reviewed host decision, not something this seam may work around.
4. **The materialized verification.** `verify_materialized_survey_sex` compares
   the complete retained receiving population against an independent
   reconstruction through the shared replay equality, and it is the check that
   catches a declaration disagreeing with the population it is applied to.
