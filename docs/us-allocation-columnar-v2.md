# US allocation columnar transport (v2) — integration proposal

Status: **proposal only**. The v2 encoder, decoder and public manifest exist in
`microcosm.build.us_runtime.survey_allocation_columnar`; nothing calls them. The
default host still emits the v1 row-wise JSON payload, `ALLOCATION_TYPE` is
still schema version 1, and no declaration, node key, spec digest or stage
implementation hash moves. This document records what a later opt-in
integration would actually cost, so that the switch is a reviewed decision
rather than a side effect.

One identity does move, and it is not a graph identity. `builder_code_identity`
hashes every `.json`, `.py`, `.toml`, `.yaml` and `.yml` file under
`packages/*/src` (`packages/microcosm-build/src/microcosm/build/code_identity.py:50-63`),
so adding any source file anywhere in the workspace changes its
`source_sha256`. `tools/build_us_puf_support_base.py:704` records that pin, and
the UK run config pins its environment through the same value
(`uk_runtime/content_identity.py:22`). An operator resuming an in-flight build
on a checkout carrying this branch will see the run-config equality check
refuse, even though no code the builder executes changed. That is the pin
behaving as designed for a whole-tree code vintage, not a defect introduced
here, but it is the one recorded identity this branch does move.

## What v1 is today

`graph_survey_population._allocation_payload` streams one canonical JSON object
per selected household into a bytearray and appends a six-field metadata tail,
under a 64 MiB cap checked before every append
(`graph_survey_population.py:344-369`). Each row repeats eleven keys:

```
household_id, source, source_year, survey_year, raw_native_id,
selected_receiving_household_id, original_anchor, share,
inclusion_probability, importance_multiplier, importance_weight_float64_hex
```

`source_year`, `survey_year` and `importance_multiplier` are already redundant
given the other fields, and `importance_weight_float64_hex` is derivable from
the three rationals. The payload's size is therefore dominated by key text
rather than by the values it carries. The row bound applied upstream is
`ALLOCATION_MAX_BYTES // 128` (`graph_survey_population.py:153`).

## Why no maintained codec could carry this

Traced before the module was written:

- `ContentStore`'s typed-column codec is **directory-based**. `_write_series`
  and `_read_series` take a `Path` and write or read `values.npy`,
  `offsets.npy` and `mask.npy` through `np.save`/`np.load`
  (`packages/microcosm-graph/src/microcosm/graph/store.py:433-494`, `:497`,
  `:123-130`, `:294-303`). Neither returns or accepts a byte string.
- A kernel never receives a store. `KernelContext` carries
  `artifacts: Mapping[str, ArtifactValue]` and `ArtifactValue.payload` is
  validated to be plain `bytes`; `KernelResult.artifacts` is a bytes mapping
  (`packages/microcosm-graph/src/microcosm/graph/kernel.py`). The executor reads
  the store on the kernel's behalf and hands over bytes.
- The `frame-store` codec (`codecs.py:259-264`) loads a whole verified `Frame`
  from a materialised content-store object directory. It is a source codec for a
  CREATE-style node, not a bytes transform.

The one maintained codec whose API does fit a bytes-only artifact is
`microcosm.graph.canonical.canonical_json`, and v2 reuses it for the header —
the same reuse `puf_raw_source.py` already makes.

## What v2 provides

`encode_allocation(instructions, *, preparation_sha256, input_context,
output_context, max_bytes=MAX_BYTES) -> bytes` streams rows into column buffers
and seals magic, a bounded canonical JSON header, the column bodies and a
trailing SHA-256. It builds no row-shaped intermediate.

`decode_allocation(payload, *, max_bytes=MAX_BYTES) -> DecodedAllocation`
returns parallel columns in payload order and re-proves everything the payload
claims: the envelope checksum, each column's own digest, the importance
multiplier, the float weight and the row-ordering digest are recomputed rather
than believed. `DecodedAllocation.legacy_instruction_documents()` renders the
exact v1 per-row documents lazily, which is the parity bridge.

`allocation_manifest(payload)` describes shape and provenance digests only. It
omits every native lexeme, identifier, rational and weight, and also omits the
ordering digest and the per-column digests, because each of those is taken over
low-entropy native identifiers and would be a confirmation oracle for them.

The 64 MiB cap and the row bound are exactly the v1 values and are **not**
raised. A v2 payload fits more rows under the same ceiling because it carries
fewer bytes per row, not because the ceiling moved.

## What an opt-in integration would have to change

In dependency order. Every item below was read in the tree; none of it is
speculative.

1. **The three consumers that actually parse the bytes.** Everything else binds
   the edge and hashes the payload opaquely, but these read one key out of it
   with `microcosm.fit._graph_legacy_qrf.decode_json`:

   - `graph_puf_diagnostic_consumer.py:616`
   - `graph_current_survey_predictors.py:391`
   - `graph_current_survey_property.py:888`

   All three assert
   `sha(frame_context) == decode_json(allocation)["output_context_sha256"]`. A
   non-JSON payload under the same artifact name fails all three with a
   `ValueError` out of `decode_json` before any of their own refusal codes. They
   would have to read the v2 header instead — for example through
   `allocation_manifest(payload)["output_context_sha256"]`, which exposes that
   field and nothing private.

2. **The artifact type version.** Bumping `ALLOCATION_TYPE` to schema version 2
   is checked at four independent layers: compile time rejects a producer and
   consumer whose `ArtifactType` differs (`decl.py:805-814`), both node keys
   move, a cached record whose `typed_artifacts` disagree is rejected
   (`executor.py:1692-1695`), and `value_from_descriptor` rebuilds and re-checks
   the type on load. Producer and every consumer edge must move together in one
   change: `graph_survey_population.py:60, 577, 1110, 1263`,
   `graph_survey_budget.py:175`, `graph_puf_diagnostic_consumer.py:433`,
   `survey_age_calibration.py:493`.

3. **The implementation inventory.** Adding this module to the stage's reviewed
   fence requires an entry in
   `us_runtime/graph_implementation_inventory.json` under
   `stages.authenticated_survey_population_v1.modules`, a matching `contracts`
   entry (imports plus the unbound-use and resource-access digests), and an
   `import_classifications` line for the new import target in
   `graph_survey_population.py`'s own contract. Because
   `implementation_manifest` folds `inventory_sha256` into every stage manifest
   (`graph_implementation.py:442`), that edit moves the implementation hash of
   **every** US stage, not only this one.

   This is precisely why the module was added without touching the host:
   `microcosm.build` is excluded from `_validate_package_roster`
   (`graph_implementation.py:422`, and `package_rosters` has no
   `microcosm.build` key), so an unlisted, unimported module under
   `us_runtime/` contributes to no stage manifest and moves no identity.

4. **Every recorded `allocation_sha256`.** It is a digest of the payload bytes
   (`graph_survey_population.py:442`), so switching encoders moves it in the
   allocation receipt and in every document that pins it —
   `survey_origin_budget.py`, `current_survey_predictors.py`,
   `graph_puf_diagnostic_consumer.py` — plus any stored fixture that carries one.

## A latent v1 fragility found while tracing

The v2 encoder and decoder now also inherit v1's exact arithmetic domains:
`share` and `inclusion_probability` are both required to satisfy
`0 < value <= 1`. This closes the confirmed v2 gap where negative values could
cancel in the multiplier, and where a zero anchor could mask invalid values
from the weight check. The wire format and valid v1/v2 parity are unchanged.

`_bounded_json` encodes with `ensure_ascii=False`
(`graph_survey_population.py:253-261`), while `_graph_legacy_qrf.encode_json`
re-encodes with the `json.dumps` default `ensure_ascii=True`
(`packages/microcosm-fit/src/microcosm/fit/_graph_legacy_qrf.py:26-29`) and
`decode_json` requires the re-encoding to equal the payload byte for byte. A
non-ASCII `raw_native_id` — which `allocation_instructions` permits, checking
only `type(...) is str` and `0 < len(...) <= 128`
(`graph_survey_population.py:166-167`) — would therefore break all three consumers
today. This is a v1 property, not something v2 introduces; v2 carries native
lexemes as bounded UTF-8 bytes with an explicit length column and has no such
asymmetry. It is recorded here because it is a real defect in the current host
and the integration would retire it as a side effect.

## What this does not establish

This change is one `O(H)` transport. It does not establish full-national
capacity, and no runtime, memory or capacity measurement was taken.

The preparation payload remains the other 64 MiB ceiling on the same path.
`survey_population_preparation` encodes one canonical JSON document — request,
source files, catalogues, native receipts, the selection plan and the row-wise
`origins.entities` records for every stacked entity — through `_encode` under
`MAX_PAYLOAD_BYTES = 64 * 1024**2`
(`survey_population_preparation.py:50`, `:104-110`, `:823-877`, `:1346-1372`). That cap is
untouched by this work and is the next candidate for the same treatment; a v2
allocation artifact does not relieve it.
