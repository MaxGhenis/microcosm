Add explicit, fail-closed Axiom dense-relation bindings and deterministic
relation-batch receipts to the Microcosm frame adapter.  Cross-entity rules now
execute only when callers bind both frame entities and the exact membership
column; the adapter never infers direction from a relation name.
Receipts authenticate owned execution snapshots plus live outputs, preserve
signed-range integer or Unicode-string entity IDs, bind an exact injective
frame/engine entity map, and fail closed on unsafe repeated native keys,
duplicate relation edges, byte-string identity collisions, unsigned input
overflow, or output-coercion mutation. Relation-free ordinary execution keeps
its broader legacy entity-ID compatibility because those IDs never cross the
Axiom boundary.
