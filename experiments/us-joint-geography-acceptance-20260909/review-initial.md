# Independent joint-geography source review

Reviewed frozen manifest b6ee998962dcb1b8953fd2dfd4f8a5da9af26ff9f74b4a257dd84b18b6857800 and all 10 file diffs. All manifest entries verified. Current implementation source bytes match the packet except the separately revised lazy facade and changelog, which are outside this review. No project execution or native data access by this reviewer.

## P2: Revalidate tract-to-PUMA nesting on the direct/mutable ladder path

`packages/microcosm-build/src/microcosm/build/us_runtime/puma_ladder.py:447` validates unique joint triples and state prefixes, but does not require a tract to belong to only one PUMA. The NPZ loader separately enforces tract uniqueness at line 278; `assign_us_puma_ladder` and the new support gate call only `_validated_joint_support`, so a directly constructed or mutated ladder can pass both while violating the same source relationship. Concrete case using the maintained fixture: replace index 2 of both `joint_overlap_tract` and `tract_overlap_tract` with index 1 (1003000100). Both rows share county 01003 and CD 102, so every current marginal check remains exact and the joint triples remain sorted/unique, while tract 01003000100 is now assigned to two PUMAs. The loader rejects the equivalent serialized artifact.

Add the tract-to-unique-PUMA check to the shared validator (multiple CDs per tract remain legitimate), and a direct/mutated-ladder regression proving assignment raises and the support gate fails. This is an invariant gap on the public in-memory path; the genuine assembler's dictionary-based tract map does not itself create it.

The block-to-joint aggregation, exact integer marginal reconciliation, one weighted joint draw, county prefix derivation, coarse assignment stability across the tract flag, schema-v1 refusal, and zero-weight-independent support membership are otherwise coherent in this source review. The existing state/NYC gate must still be composed with the new support gate as documented. Four integration fixture updates retain their actual marginals and add corresponding joint cells. No additional actionable finding in those changes.

The separate lazy-facade amendment, graph gate composition, actual source assembly, statistical calibration, source custody and release verification are not certified by this review.
