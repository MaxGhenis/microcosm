# Joint US geography assignment

PUMA ladder schema v2 retains the population of each `(2020 PUMA, 2020 tract,
congressional district)` cell from the Census populated-block join. County is
the tract prefix. These are actual joint cells from source assembly; the
assignment does not multiply independently estimated county and district
probabilities. A county and district can each overlap a PUMA while their pair
has no populated-block support.

An ACS household keeps its observed 2020 PUMA. An ASEC household keeps its
assigned state and draws a PUMA within that state using PUMA population.
Each household then receives one population-weighted joint cell within its
PUMA. The supplied seed and sorted source rows make these draws reproducible.
Enabling `assign_tract` exposes the selected tract without changing PUMA,
county or district assignments. This tract is an assigned crosswalk cell,
not observed residence.

The artifact includes four new integer arrays: `joint_overlap_puma`,
`joint_overlap_tract`, `joint_overlap_cd` and `joint_overlap_population`.
Loading, assigning and checking support require these rows to reproduce
the anchor and every retained marginal population exactly. The loader refuses
marginal-only schema v1 artifacts; rebuild from the block, tract-to-PUMA and
district source inputs with `tools/build_us_puma_ladder_artifact.py`.
Relabeling an old artifact or multiplying its marginals cannot supply missing
joint evidence.

`us_puma_ladder_joint_support_gate` checks every assigned household, including
zero-weight clones, against the joint support table. It optionally checks
tract and the expected district vintage. The build must compose this check
with the existing state/NYC mass gate and the separate calibration, coverage,
source-custody and export-vintage checks. The support check does not certify
county or tract analysis, establish the authenticity of an arbitrary NPZ, or
make an otherwise uncalibrated file releasable.

The launch profile remains national and congressional district analysis.
County is retained as a model input; tract export remains optional. Actual
source rebuilding, gate composition in the current graph and release
verification are separate build steps after the invented source controls.
