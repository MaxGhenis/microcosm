Add a bounded, deterministic v2 columnar allocation transport
(`microcosm.build.us_runtime.survey_allocation_columnar`) that carries the
allocation instruction values without the v1 payload's repeated per-household
JSON keys, preserving exact int64 identifiers, arbitrary rationals, native
lexemes and float64 weight bits. The default host, its artifact type and the
existing 64 MiB bounds are unchanged; the new encoder, decoder and public
manifest are opt-in and carry no source authority.
