# Survey domain allocation core

`microcosm.build.survey_allocation.allocate_domain_weights` is an additive,
country-neutral numerical primitive. It multiplies each supplied design weight
by its declared population-domain/source share. Source shares are exact
Fractions summing to one; results use the Frame kernel's float64 IMPORTANCE
weights. A unique household identity and a unit count are mandatory for every
row, and output order matches input order.

Unit counts affect the reported estimate, not the household weight. Three
people in one group-quarters cluster inherit one weight; their count contributes
three times that weight to a person estimate. An ACS single-person placeholder
contributes once. These are counting conventions supplied by the caller, not a
new source classification. For physical housing units the caller must supply
one unit per row. Source/coverage and count authentication belongs to the
source-admission adapter.

Unknown/undeclared coverage, duplicate household identities, missing
positive-share support, invalid counts, non-DESIGN weights, floating-point
overflow and positive-weight underflow refuse. Explicit zero-share sources can
have no sample support and are reported with a declared zero contribution.
There is no query that invents an estimate for an undeclared population.
Estimates retain domain, source, statistical unit, period and basis. The module
does not expose a combined total across different units or periods.

This operation does not sample, restore sampled mass, classify source records,
read microdata, change a Frame, activate a graph or calibrate. The existing
whole-arm `assemble_spines` and local graph successors keep their semantics.
Any graph integration needs a new preparation/context/receipt version that
binds these inputs to the actual source population and records the domain
convention. The existing mixed-unit ASEC anchor must not be reapplied after
domain allocation. PUF support cloning follows the assembled survey pool and
must conserve each source household's already allocated weight.

The mathematical reference is the September 7 invented experiment at
`4dbb54107928d89b809f9a6b64bbc9f8377dcadf`: shared HU100/GQ10 accounting,
differing source estimates, refusal of unknown populations and household-axis
restrictions. The production-core tests additionally cover multi-person
clusters, explicit zero-share cells and float limits. None is evidence about
actual dataset bias, common residence/military eligibility or release accuracy.

The next integration must declare how source-period pooling and subsampling
restore per-domain support. It must preserve source observations for military
and quarters classifications and distinguish observed rules from harmonization
assumptions. No reserved target is needed to test this numerical primitive.
