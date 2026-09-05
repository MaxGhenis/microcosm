# US production graph development

The source and geography graph stages run the existing US operations on actual
declared inputs. They are development stages, not a terminal pool or a certified
dataset. Downstream source preparation, fitted transfers, structural support,
validation and calibration must still run before a release can be evaluated.

`us_runtime.graph_sources.us_assembly_graph` declares two nodes under the
`assemble_stacked_spine` phase. The preparation CREATE reads the authenticated
operator-free ASEC v4 checkpoint and the two national ACS2024 PUMS archives. It
performs the existing whole-household sampling and full/sample mass ratio
normalization, then stacks the actual DESIGN weights. Its separate preparation
artifact contains source lineage and allocation controls, with no precomputed
importance weights or completed stacked-spine manifest. This captures the
normalized sampled DESIGN anchor used by later graph weight constraints.

The REWEIGHT node reads declared source-channel and membership views plus the
same producer's typed preparation/context artifacts. The existing harmonization
helper computes IMPORTANCE weights with exact source-order floating operations.
Household share allocation and the graph's declared person mass by source
stratum are distinct checks. All six resolved entity weights are compared with
the direct operation in the tiny integration tests.

`us_runtime.graph_geography.us_geography_nodes` then declares lookup import,
an all-row version boundary, household assignment and its integrity gate.
The raw-byte source codec reads bounded regular files; existing decoders validate
the PUMA2020 NPZ and the 117th-to-119th crosswalk. Their district universe must
match exactly. Assignment preserves native PUMAs and the existing seed0 draw
order. It reads household cells only and owns PUMA, congressional district and
county outputs. Every inner node declares its outer phase. The integrity gate
checks the existing assignment rules; it does not establish CD fit or accuracy.

The versioned `microcosm.us.frame_context` artifact carries audited operator
metadata, ordered entity IDs/column inventories, explicit weight kinds and the
legacy operator mass history. Population cells, memberships, weights and strata
remain graph-owned. Context and preparation must have the declared typed producer;
reconstruction checks the available entity identities. Unknown operator metadata
and operational fields are refused. Geography updates only the household column
inventory while preserving untouched descriptors.

Two mass histories are retained deliberately. The executor records the actual
CREATE-to-REWEIGHT transition in its aggregate ledger. The context retains the
source-ordered legacy operation history. A direct-checkpoint comparison restores
the authenticated legacy history and metadata after checking the graph population
identity; it never overwrites the executor's manifest. Nullable integer storage
uses the existing Frame checkpoint schema4 extension and preserves exact values,
including observed zero and integers above2**53.

Tests cover actual small source construction, normalized anchors, source/codec
identity, tampered context, missing or corrupt required-cache inputs, source
mutation, direct output/weight/context parity, complete HDF5 byte parity, geography
failure evidence and a fresh-store replay with zero source calls. Model and source
implementation identities are conservative; code changes legitimately invalidate
development caches. The source importer binds its actual h5py dependency.

Real-source runs must keep their source hashes, code identity, measured memory,
wall time, store size and failure receipts. A successful fraction run remains
development evidence. A failed run with no saved population has no population
quality metrics. Neither state changes a production, staging or latest pointer.
