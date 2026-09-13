# Complete-source property38 to PUF bridge

Status: source-authored tests, not executed. This is a proposed invented-source
wiring check. It does not complete child or missing adult property observations
in a native dataset and does not establish release readiness.

`test_us_graph_property38_puf_bridge.py` constructs the existing common ACS and
ASEC source fixture with all selected persons in the age-15+ property reporting
universe. Its `complete_adults` fixture option refers to that survey universe,
not an age-18 legal classification. It retains the signed ACS property anchor
and the ASEC survivor-overlap row whose independently qualified interest and
dividend values survive exclusion from the joint donor fit.

The two former age-14 ASEC fixture persons instead have explicit invented
age-15 source values, including Social Security nonreceipt codes. The original
parent and household attachments, member hashes, and person-income restoration
are rebuilt before any source preparation is issued. This is a different
invented source case, not a production rule that changes NIU to observed zero.
The default fixture still contains its child and malformed ACS observations.

The proposed positive path retains the actual financial issuer and calls
`run_survey_puf55` using the existing original-PUF fixture route. The expected
counts are 38 financial nodes followed by six shared PUF boundary nodes and
one 55-fit/55-apply chain: 154 nodes. All original Social Security measurement
reports must support the known-total route; the test refuses another route
count rather than relabeling a two-route execution. A separate required replay
must hit all 154 nodes and reproduce the complete Population and checked bytes.

Five controls share that one positive construction and replay. They check the
existing complete-property gate, clone/original identity, the declared
post-clone geography order, retained prefix keys, every nonowned cell, original
channel owned cells, weights and design anchors. Copied financial/PUF handles
must remain unissued; changing a retained replay value must permanently revoke
only that replay handle. These tests do not use the existing `sys.monitoring`
helpers.

The proposed bounded packet separately selects the existing incomplete38
admission test from `test_us_graph_atomic_property_tax_financial.py`. That
requires its own source/38-node fixture; it must run after the positive module
tears down, so distinct source registry pins do not overlap. It exercises the
real `PROPERTY_TAX_INPUTS_INCOMPLETE` refusal without changing the gate or
manufacturing an issued handle. The older incomplete38 acceptance remains
historical evidence, not acceptance of these new source bytes.

No production module, source authority, allocation rule, or release gate is
changed. A passing invented bridge would demonstrate composition only. Native
property completeness remains a separate prerequisite, and PUF clone1 outputs
cannot bootstrap missing original-channel observations before admission.
