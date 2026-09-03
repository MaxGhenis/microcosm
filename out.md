# PR #847 fresh gate, round 2 — lane report

## Result

All three ruled findings are implemented as three coherent commits on
`fix-847-r4`. The worktree is clean, nothing was pushed, and every required
check is green.

- Source ref: `origin/graph-amendments-11-13`
- Dispatched/base head: `1300f542c03ccdea1d2af02da8078da93fd2bddb`
- Worktree: `/private/tmp/microcosm-fix-847-r4`
- Final head: `cdc52131116e8b071b9a430d2d7f030bcd050ebe`
- Environment sync (strictly offline, using the lane cache):

  ```text
  UV_CACHE_DIR=/private/tmp/microcosm-fix847r4-uv-cache UV_OFFLINE=1 UV_NO_BUILD_ISOLATION=1 uv sync --all-packages --locked --extra us --extra uk
  Resolved 158 packages in 1ms
  ...
  Installed 6 packages ... microcosm==0.1.0, microcosm-dynamics==0.1.0,
  microcosm-fit==0.1.0, microcosm-graph==0.1.0, microcosm-uk==0.1.0,
  microcosm-us==0.1.0
  ```

- Import isolation:

  ```text
  inspect.getfile(microcosm.graph)
  /private/tmp/microcosm-fix-847-r4/packages/microcosm-graph/src/microcosm/graph/__init__.py
  ```

The lane journal is `/private/tmp/microcosm-fix-847-r4/_lane/PROGRESS.md`.
It and this report are intentionally uncommitted, as instructed.

## F6 — entrant membership may not name a copied group

Commit: `75c3c5702f476ab12abe6c8aa6594b79f92097e4`
(`fix(graph): reject entrant links to copied groups`)

Regression:

- Pytest id:
  `packages/microcosm-graph/tests/test_graph_population.py::test_expand_rejects_entrant_membership_to_copied_group`
- Regression node id: `entrant_membership`
- Parameterized paths: `cold` and `cached`

The shared EXPAND membership validator now validates both copied-person and
entrant-person rows. An entrant person's membership target must be either an
incumbent group id or a null-lineage group entrant admitted by this same
EXPAND. A non-null-lineage copied group is rejected by node, coordinate,
entrant person id, and copied group id. Both `_patch_expand` and
`restore_cached_expand` use the same validation.

The helper still returns only legal copied-person membership re-pointings.
Consequently, writer provenance remains exact: validating an entrant does not
claim that the invocation wrote a copied membership coordinate.

Fail-before command:

```text
UV_CACHE_DIR=/private/tmp/microcosm-fix847r4-uv-cache uv run --no-sync python -m pytest packages/microcosm-graph/tests/test_graph_population.py::test_expand_rejects_entrant_membership_to_copied_group -q
```

Fail-before excerpt:

```text
FF                                                                       [100%]
E   Failed: DID NOT RAISE <class 'microcosm.frame.population.PopulationError'>
E   Failed: DID NOT RAISE <class 'microcosm.frame.population.PopulationError'>
```

Pass-after command:

```text
UV_CACHE_DIR=/private/tmp/microcosm-fix847r4-uv-cache uv run --no-sync pytest packages/microcosm-graph/tests/test_graph_population.py::test_expand_rejects_entrant_membership_to_copied_group -q
```

Pass-after excerpt:

```text
..                                                                       [100%]
```

Anything not done as ruled: none. Cold and cached paths are both covered.

## F5 — declarations are distinct from writes

Commit: `5dcb6fcde7606606f2bf6c8fc196a3bba87d7fac`
(`fix(graph): separate expand declarations from writes`)

Regression:

- Pytest id:
  `packages/microcosm-graph/tests/test_graph_executor.py::test_entrant_expand_with_zero_entrants_allows_declared_materialized_claim`
- EXPAND node id: `zero_entrant_expand`
- Claimant node id: `claim_zero_entrant_size`

Every EXPAND receipt now has two separate executor-authored surfaces:

- `expand_declared`: the canonical, sorted coordinates declared in the node's
  `expand_cells`, present even when this invocation adds no rows.
- `expand_writes`: the exact per-coordinate row-class provenance actually
  written by this invocation.

`materialized_expand_outputs` is checked against `expand_declared`.
Tolerance-writer resolution continues to use `expand_writes`, so declaration
scope is not mistaken for actual writer provenance. Cache records missing the
new declaration attestation are treated as stale misses; malformed or
declaration-inconsistent attestations are corrupt.

The regression runs cold and warm. Its `entrants=True` kernel returns empty
lineage for all entities, a complete unchanged carried overlay, and unchanged
weights. Both it and the downstream claimant run green with:

```text
expand_declared == ("household.size",)
expand_writes == {}
tolerance_writers["household.size"] == ("survey",)
```

Fail-before command:

```text
UV_CACHE_DIR=/private/tmp/microcosm-fix847r4-uv-cache UV_OFFLINE=1 uv run pytest packages/microcosm-graph/tests/test_graph_executor.py::test_entrant_expand_with_zero_entrants_allows_declared_materialized_claim -q
```

Fail-before excerpt:

```text
F                                                                        [100%]
E   microcosm.graph.errors.NodeRejectedError: Node 'claim_zero_entrant_size'
E   names materialized EXPAND output household.size, but EXPAND population
E   version 'zero_entrant_expand' did not materialize that coordinate.
```

Pass-after excerpt from the same command:

```text
.                                                                        [100%]
```

Anything not done as ruled: none. The declared and written sets are separate,
and the warm-cache assertions preserve the same distinction.

## F1 — complete manifest authentication

Commit: `cdc52131116e8b071b9a430d2d7f030bcd050ebe`
(`fix(graph): authenticate complete manifest receipts`)

Regressions:

- `test_from_json_rejects_coordinated_gate_and_tier_tampering`
  - First differing node id: `gate`
- `test_v1_manifest_relabel_with_fabricated_tolerance_fails_key`
  - First differing node id: `fit_qrf`
- Control: `test_untouched_certified_manifest_round_trips_and_loads_certified`

The current manifest content-addressed projection is now a node-id-keyed map
of every complete `NodeReceipt._payload()` plus the rederived release tier.
This authenticates the full capabilities projection, explicit
`legacy_capabilities`, the complete kernel/executor receipt (including gate
outcome and evidence), `hit`, `seed`, kernel reference and implementation
hash, artifacts, and timing. Associating the payload with its node id also
prevents receipt permutation between nodes.

`RunManifest.from_json` reconstructs that projection from portable receipts,
compares it to the stored content-addressed body, and names the
lexicographically first differing node. Only after body equivalence does it
verify that the stored key hashes that body. The tier property re-walks the
release's gate ancestry, re-reads each gate receipt, derives `certified` or
`evidence`, and refuses a release receipt whose stored tier differs.
`load_certified` loads through those checks and re-evaluates `manifest.tier`
before certification.

Current keys exclude `Decision` records exactly as F5 requires. For schema-v1
compatibility only, the loader reconstructs the historical v1 projection
(which included decisions) to validate an already-serialized legacy key. That
legacy check does not become the loaded manifest's current key, and newly
serialized manifests never place decisions in their identity.

The existing v2 parser requires `legacy_capabilities` explicitly and legacy
receipts still reject tolerance. Relabeling the v1 fixture as v2, adding the
required flag, and fabricating a tolerance therefore parses far enough to hit
the body comparison and is refused at node `fit_qrf`.

Fail-before command:

```text
UV_CACHE_DIR=/private/tmp/microcosm-fix847r4-uv-cache UV_OFFLINE=1 uv run pytest packages/microcosm-graph/tests/test_graph_manifest.py::test_from_json_rejects_coordinated_gate_and_tier_tampering packages/microcosm-graph/tests/test_graph_manifest.py::test_v1_manifest_relabel_with_fabricated_tolerance_fails_key packages/microcosm-graph/tests/test_graph_manifest.py::test_untouched_certified_manifest_round_trips_and_loads_certified -q
```

Fail-before excerpt:

```text
FF.                                                                      [100%]
E   Failed: DID NOT RAISE <class 'ValueError'>
E   Failed: DID NOT RAISE <class 'ValueError'>
```

The third dot is the untouched certified-manifest control passing before the
fix.

Pass-after excerpt from the same command:

```text
...                                                                      [100%]
```

Anything not done as ruled: none. Decisions are outside the current key;
schema-v1 loading remains supported without weakening schema-v2 identity.

## Final verification

Touched files:

```text
packages/microcosm-graph/src/microcosm/graph/executor.py
packages/microcosm-graph/src/microcosm/graph/explain.py
packages/microcosm-graph/src/microcosm/graph/manifest.py
packages/microcosm-graph/src/microcosm/graph/population.py
packages/microcosm-graph/tests/test_graph_executor.py
packages/microcosm-graph/tests/test_graph_manifest.py
packages/microcosm-graph/tests/test_graph_population.py
```

Ruff:

```text
uv run ruff check <the seven touched files>
All checks passed!

uv run ruff format --check <the seven touched files>
7 files already formatted
```

Required graph and fit suite:

```text
UV_CACHE_DIR=/private/tmp/microcosm-fix847r4-uv-cache UV_OFFLINE=1 uv run pytest packages/microcosm-graph packages/microcosm-fit/tests
376 passed, 1 warning in 110.07s (0:01:50)
```

The single warning is the pre-existing Pydantic deprecation emitted through
`policyengine_uk`.

CI group verification (the repository scripts are mode `0644`, so invoked
through Python):

```text
UV_CACHE_DIR=/private/tmp/microcosm-fix847r4-uv-cache UV_OFFLINE=1 uv run python tools/ci_test_groups.py --verify
tracked_test_files=354
verification=ok
```

Acceptance burndown verification:

```text
UV_CACHE_DIR=/private/tmp/microcosm-fix847r4-uv-cache UV_OFFLINE=1 uv run python tools/graph_acceptance_burndown.py --verify
green 41
red 0
missing 0
verification=ok
```

Constraint audit:

- No diff in `decl.py`, `kernel.py`, `docs/graph-interface.lock`, or any
  `test_acceptance_*.py`.
- No diff in concurrently edited `keys.py` or
  `tools/graph_acceptance_burndown.py`.
- No edit near `manifest.py`'s `PopulationView`; the manifest implementation
  diff begins in `RunManifest`.
- No push.

## Proposed acceptance-test diffs — not applied

These are proposed for the independent acceptance lane. They were not applied
or committed here.

### F1: authenticate coordinated gate/tier edits and schema relabeling

Add the following beside F3 in
`packages/microcosm-graph/tests/test_acceptance_f_gates.py`:

```diff
@@
 def test_f3_the_one_field_flip_is_impossible(tmp_path: Path) -> None:
     ...

+def test_f3_coordinated_gate_and_tier_flip_is_impossible(
+    tmp_path: Path,
+) -> None:
+    red = toy.run_toy(toy.full_graph(**IMPOSSIBLE_BAND), tmp_path / "red")
+    path = tmp_path / "red" / "manifest.json"
+    red.manifest.save(path)
+
+    document = json.loads(path.read_text())
+    document["nodes"]["gate_tax"]["receipt"]["outcome"] = "pass"
+    document["nodes"]["release"]["receipt"].update(
+        {"outcome": "pass", "tier": "certified"}
+    )
+    document["tier"] = "certified"
+    document["known_failures"] = []
+    path.write_text(json.dumps(document))
+
+    from microcosm.graph import StoreCorruptError
+
+    with pytest.raises(StoreCorruptError, match="gate_tax"):
+        RunManifest.load_certified(path, store=red.store)
+
+
+def test_f3_v1_relabel_with_fabricated_tolerance_is_impossible() -> None:
+    path = (
+        Path(__file__).parent
+        / "fixtures"
+        / "manifests"
+        / "v1_tolerance_bound_without_tolerance.json"
+    )
+    document = json.loads(path.read_text())
+    document["schema_version"] = 2
+    receipt = document["nodes"]["fit_qrf"]
+    receipt["legacy_capabilities"] = False
+    receipt["capabilities"]["tolerance"] = {
+        "rtol": 1e-6,
+        "atol": 1e-9,
+        "ulps": 2,
+    }
+
+    with pytest.raises(ValueError, match="fit_qrf"):
+        RunManifest.from_json(json.dumps(document))
```

The existing green branch of F2 already supplies the untouched
round-trip-and-certify control; it should remain unchanged.

### F5: zero entrants still expose declaration scope

First add a test-only `zero_entrants` option to `_toy.py`'s
`ExpandEntrants` fixture and `entrant_expand_node`. The branch returns empty
lineage for `person`, `household`, and `release`, full unchanged overlays for
the two declared `expand_cells`, and unchanged household weights:

```diff
@@ class ExpandEntrants(ToyKernel):
     def compute(self, context: KernelContext) -> KernelResult:
         person = context.tables["person"]
+        if context.params.get("zero_entrants"):
+            household = context.tables["household"]
+            return KernelResult(
+                expand={
+                    entity: pd.Series(
+                        [],
+                        index=pd.Index([], dtype="int64", name=id_column(entity)),
+                        dtype="int64",
+                    )
+                    for entity in ("person", "household", "release")
+                },
+                columns={
+                    ("household", "household_size"): pd.Series(
+                        household["household_size"].array.copy(),
+                        index=pd.Index(household["household_id"], name="household_id"),
+                        dtype="int64",
+                    ),
+                    ("person", "person_household_id"): pd.Series(
+                        person["person_household_id"].array.copy(),
+                        index=pd.Index(person["person_id"], name="person_id"),
+                        dtype="int64",
+                    ),
+                },
+                weights=Weights(
+                    context.weights["household"].values.copy(),
+                    kind=context.weights["household"].kind,
+                ),
+            )
@@ def entrant_expand_node(
     missing_entrant_column: str | None = None,
+    zero_entrants: bool = False,
@@
             "missing_entrant_column": missing_entrant_column,
+            "zero_entrants": zero_entrants,
```

Then extend B6 in
`packages/microcosm-graph/tests/test_acceptance_b_ownership.py`:

```diff
@@
 from microcosm.graph import (
+    ContentStore,
     GraphError,
@@ def test_b6_entrants_are_declared(tmp_path: Path) -> None:
     assert "household_size" in str(error.value)
+
+    empty_expand, empty_claim = toy.entrant_expand_node(
+        "zero_scheduled_entries", zero_entrants=True
+    )
+    graph = toy.small_graph(nodes=(toy.CREATE, empty_expand, empty_claim))
+    registry = toy.toy_registry()
+    store = ContentStore(tmp_path / "zero" / "store")
+    cold = toy.run_toy(graph, tmp_path / "zero", registry=registry, store=store)
+    warm = toy.run_toy(
+        graph,
+        tmp_path / "zero",
+        sources=cold.sources,
+        registry=registry,
+        store=store,
+    )
+
+    for run in (cold, warm):
+        receipt = run.manifest.nodes[empty_expand.id].receipt
+        assert receipt["expand_declared"] == (
+            "household.household_size",
+            "person.person_household_id",
+        )
+        assert receipt["expand_writes"] == {}
+        assert run.manifest.nodes[empty_claim.id].receipt["capabilities"][
+            "tolerance_writers"
+        ]["household.household_size"] == (toy.CREATE.id,)
+    assert not cold.manifest.nodes[empty_expand.id].hit
+    assert not cold.manifest.nodes[empty_claim.id].hit
+    assert warm.manifest.nodes[empty_expand.id].hit
+    assert warm.manifest.nodes[empty_claim.id].hit
```

### F6: an entrant cannot join a same-EXPAND copied group

Add a fixture mode to `ExpandEntrantPerson` which copies the first household,
admits the person with null lineage, and points the entrant's materialized
`person_household_id` at that copied household id. Expose it as
`membership_mode="copied_group"` on `entrant_person_node`. Then extend B7:

```diff
@@ def test_b7_entrant_persons_carry_their_stratum(tmp_path: Path) -> None:
     for mode in ("missing", "unknown_id", "labels_incumbent", "labels_copied"):
         ...
+
+    copied_group, copied_group_claim = toy.entrant_person_node(
+        "cohort_entrant_to_copied_group",
+        membership_mode="copied_group",
+    )
+    with pytest.raises(
+        NodeRejectedError,
+        match=(
+            r"cohort_entrant_to_copied_group.*entrant person id.*"
+            r"copied household id"
+        ),
+    ):
+        toy.run_toy(
+            toy.small_graph(
+                nodes=(toy.CREATE, copied_group, copied_group_claim)
+            ),
+            tmp_path / "entrant_to_copied_group",
+        )
```

That is the public executor-level charter assertion. The committed regression
also parameterizes the lower-level restoration boundary as `cold` and
`cached`, because a rejected cold result cannot naturally become a legitimate
cache entry. If the acceptance owner wants cached corruption in B7 as well,
the companion toy fixture should install a previously valid cached frame whose
entrant membership alone is changed to the copied group; the expected refusal
and message are identical. No production API should be added for that fixture.
