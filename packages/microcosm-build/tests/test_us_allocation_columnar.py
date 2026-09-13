"""Invented-value contract tests for the v2 columnar allocation transport.

Every row here is fabricated. Nothing in this file reads a source, opens a
store or asserts anything about a real cohort. The one byte-count comparison is
a source-defined count over two encoders on identical invented input, not a
runtime or capacity measurement.
"""

import hashlib
import json
import struct
from fractions import Fraction

import pytest

from microcosm.build.us_runtime import graph_survey_population as graph
from microcosm.build.us_runtime import survey_allocation_columnar as columnar
from microcosm.build.us_runtime.survey_population_domains import HouseholdKey, Source
from microcosm.graph.canonical import canonical_json

KWARGS = {
    "preparation_sha256": "b" * 64,
    "input_context": b"{}",
    "output_context": b"[]",
}


def instruction(
    index=0,
    *,
    household_id=None,
    source=Source.ACS,
    source_year=2024,
    survey_year=None,
    native=None,
    receiving=None,
    anchor=Fraction(13),
    share=Fraction(1, 2),
    probability=Fraction(2, 7),
):
    """One invented row in the host's own value shape."""
    if survey_year is None:
        survey_year = 2024 if source is Source.ACS else 2025
    return graph.AllocationInstruction(
        index if household_id is None else household_id,
        HouseholdKey(
            source,
            source_year,
            survey_year,
            f"2024HU{index:07d}" if native is None else native,
        ),
        index if receiving is None else receiving,
        anchor,
        share,
        probability,
    )


def cohort(count=3):
    """A mixed-source cohort with distinct identifiers on every axis."""
    return tuple(
        instruction(
            index,
            source=Source.ACS if index % 2 == 0 else Source.ASEC,
            anchor=Fraction(13 + index),
        )
        for index in range(count)
    )


def narrow(count=3):
    """A cohort whose every exact integer occupies exactly one payload byte.

    That makes each rational stream fixed-width, so :func:`resealed` can rewrite
    a single rational cell the same way it rewrites a fixed-width column. The
    native lexemes are all thirteen ASCII characters for the same reason.
    """
    return tuple(
        instruction(
            index,
            anchor=Fraction(13),
            share=Fraction(1, 2),
            probability=Fraction(1, 4),
        )
        for index in range(count)
    )


def payload_of(instructions=None, **overrides):
    return columnar.encode_allocation(
        cohort() if instructions is None else instructions, **{**KWARGS, **overrides}
    )


def split(payload):
    """Header dict, per-column sizes, and the body region of a valid payload."""
    header, sizes, body_start = columnar._parse_header(
        payload, max_bytes=columnar.MAX_BYTES
    )
    bodies, cursor = {}, body_start
    for name in columnar._BODY_NAMES:
        bodies[name] = bytearray(payload[cursor : cursor + sizes[name]])
        cursor += sizes[name]
    return header, bodies


def seal(header, bodies):
    encoded = canonical_json(header)
    parts = [
        columnar.MAGIC,
        len(encoded).to_bytes(4, "big"),
        encoded,
        *(bytes(bodies[name]) for name in columnar._BODY_NAMES),
    ]
    joined = b"".join(parts)
    return joined + hashlib.sha256(joined).digest()


def resealed(payload, mutations):
    """Rewrite fixed-width cells, then repair every digest a tamper would break.

    The column digests and the trailing checksum are recomputed honestly, so the
    only guard left to notice the change is the one the calling test is about.
    """
    header, bodies = split(payload)
    rows = header["rows"]
    for name, index, raw in mutations:
        width = len(raw)
        # The cell width is taken from the replacement bytes, which is only
        # sound while every cell in the column is that wide. narrow()'s uniform
        # one-byte rationals and thirteen-byte lexemes make that true today;
        # checking it here means a future cohort change fails loudly instead of
        # silently overwriting a neighbouring cell.
        assert len(bodies[name]) == rows * width, (name, len(bodies[name]), rows, width)
        bodies[name][index * width : (index + 1) * width] = raw
    for column in header["columns"]:
        column["sha256"] = hashlib.sha256(bytes(bodies[column["name"]])).hexdigest()
    return seal(header, bodies)


def reheaded(payload, mutate):
    """Rewrite the header, leaving the bodies and repairing the checksum."""
    header, bodies = split(payload)
    mutate(header)
    return seal(header, bodies)


# ---------------------------------------------------------------------------
# Exact round trip and legacy parity
# ---------------------------------------------------------------------------


def test_round_trip_preserves_every_exact_value_and_row_order():
    instructions = cohort(4)
    decoded = columnar.decode_allocation(payload_of(instructions))
    assert decoded.rows == 4
    assert decoded.household_id == tuple(r.household_id for r in instructions)
    assert decoded.selected_receiving_household_id == tuple(
        r.selected_receiving_household_id for r in instructions
    )
    assert decoded.source == tuple(r.key.source for r in instructions)
    assert decoded.source_year == tuple(r.key.source_year for r in instructions)
    assert decoded.survey_year == tuple(r.key.survey_year for r in instructions)
    assert decoded.raw_native_id == tuple(r.key.native_id for r in instructions)
    assert decoded.original_anchor == tuple(r.original_anchor for r in instructions)
    assert decoded.share == tuple(r.share for r in instructions)
    assert decoded.inclusion_probability == tuple(
        r.inclusion_probability for r in instructions
    )
    assert decoded.importance_multiplier == tuple(
        r.share / r.inclusion_probability for r in instructions
    )
    assert decoded.importance_weight == tuple(
        float(r.importance_weight) for r in instructions
    )
    assert list(decoded.household_keys()) == [r.key for r in instructions]


def test_decoded_rows_render_the_exact_v1_instruction_documents():
    instructions = cohort(4)
    v1 = json.loads(graph._allocation_payload(instructions, **KWARGS))
    decoded = columnar.decode_allocation(payload_of(instructions))
    assert list(decoded.legacy_instruction_documents()) == v1["households"]


def test_v2_header_repeats_the_v1_provenance_metadata_but_not_its_protocol():
    instructions = cohort()
    v1 = json.loads(graph._allocation_payload(instructions, **KWARGS))
    header = columnar.decode_allocation(payload_of(instructions)).header
    for key in (
        "preparation_sha256",
        "input_context_sha256",
        "output_context_sha256",
        "weight_transition",
    ):
        assert header[key] == v1[key]
    assert header["release_eligible"] is False and v1["release_eligible"] is False
    # The two payloads are different artifacts and say so.
    assert v1["protocol"].endswith(".v1")
    assert header["protocol"] == columnar.PROTOCOL
    assert header["protocol"].endswith(".v2")
    assert header["schema_version"] == 2
    assert header["type"] == [columnar.ARTIFACT_TYPE_NAME, 2]


def test_zero_weight_row_round_trips_like_the_v1_document():
    instructions = (instruction(0, anchor=Fraction(0)),)
    decoded = columnar.decode_allocation(payload_of(instructions))
    assert decoded.importance_weight == (0.0,)
    document = next(decoded.legacy_instruction_documents())
    assert document["importance_weight_float64_hex"] == "0x0.0p+0"
    assert (
        document
        == json.loads(graph._allocation_payload(instructions, **KWARGS))["households"][
            0
        ]
    )


# ---------------------------------------------------------------------------
# Widths the JSON document could not hold safely
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value", [2**53 + 1, 2**62 + 12345, 2**63 - 1, 9007199254740993]
)
def test_identifiers_above_the_double_precision_range_survive_exactly(value):
    instructions = (instruction(0, household_id=value, receiving=value - 1),)
    decoded = columnar.decode_allocation(payload_of(instructions))
    assert decoded.household_id == (value,)
    assert decoded.selected_receiving_household_id == (value - 1,)


@pytest.mark.parametrize(
    ("numerator", "denominator"),
    [
        (10**40, 10**40 + 1),
        (2**512 - 1, 2**512 + 1),
        (63803, 25),
        (1, 2**300 + 1),
    ],
)
def test_arbitrary_exact_rationals_survive_exactly(numerator, denominator):
    anchor = Fraction(numerator, denominator)
    instructions = (
        instruction(0, anchor=anchor, share=Fraction(1, 3), probability=Fraction(2, 5)),
    )
    decoded = columnar.decode_allocation(payload_of(instructions))
    assert decoded.original_anchor == (anchor,)
    assert decoded.original_anchor[0].numerator == anchor.numerator
    assert decoded.original_anchor[0].denominator == anchor.denominator
    assert decoded.importance_multiplier == (Fraction(5, 6),)


@pytest.mark.parametrize(
    "native",
    [
        "2024HU0000001",
        "café-éè",
        "\U0001d7d8" * 32,
        "\U0001d7d8" * 128,
        "a" * 128,
        "\u0000embedded",
    ],
)
def test_unicode_and_boundary_width_native_lexemes_round_trip(native):
    decoded = columnar.decode_allocation(payload_of((instruction(0, native=native),)))
    assert decoded.raw_native_id == (native,)


@pytest.mark.parametrize("native", ["", "a" * 129, "\U0001d7d8" * 129])
def test_out_of_range_native_lexemes_refuse(native):
    with pytest.raises(columnar.AllocationColumnarError, match="ROW_LEXEME"):
        payload_of((instruction(0, native=native),))


@pytest.mark.parametrize("native", ["\ud800abc", "abc\udfff", "\ud800"])
def test_a_surrogate_lexeme_is_a_refusal_not_a_unicode_error(native):
    """A surrogateescape decode of malformed source bytes produces these.

    Encoding one must raise a refusal code, not a UnicodeEncodeError whose
    message would quote the lexeme this module promises never to echo.
    """
    with pytest.raises(columnar.AllocationColumnarError, match="ROW_LEXEME"):
        payload_of((instruction(0, native=native),))


def test_a_rational_wider_than_v1_can_carry_still_round_trips():
    """v2 must not be narrower than the transport it would replace.

    v1 bounds a whole row document at 4096 JSON bytes, so this anchor's decimal
    rendering alone overruns it. v2 carries the same exact value.
    """
    anchor = Fraction(2**13000, 2**13000 + 1)
    instructions = (instruction(0, anchor=anchor, probability=Fraction(1, 2)),)
    with pytest.raises(graph.SurveyPopulationGraphError, match="TRANSPORT_LIMIT"):
        graph._allocation_payload(instructions, **KWARGS)
    decoded = columnar.decode_allocation(payload_of(instructions))
    assert decoded.original_anchor == (anchor,)
    assert decoded.original_anchor[0].numerator == 2**13000


def test_a_rational_beyond_the_transport_bound_is_refused():
    """Reached through the share, not the anchor.

    Any anchor wide enough to overrun the integer bound also overflows or
    underflows float64, so the weight check would fire first and the integer
    bound would never be exercised. A zero anchor keeps the weight exactly 0.0
    while the share carries the over-wide integer.
    """
    over = Fraction(2 ** (8 * columnar.MAX_RATIONAL_BYTES) + 1)
    row = instruction(0, anchor=Fraction(0), share=over, probability=Fraction(1))
    with pytest.raises(columnar.AllocationColumnarError, match="ROW_RATIONAL"):
        payload_of((row,))


# ---------------------------------------------------------------------------
# Determinism and ordering
# ---------------------------------------------------------------------------


def test_encoding_the_same_rows_twice_yields_identical_bytes():
    instructions = cohort(5)
    assert payload_of(instructions) == payload_of(instructions)
    assert payload_of(instructions) == payload_of(tuple(instructions))


def test_row_order_is_carried_through_and_never_sorted():
    instructions = cohort(4)
    forward = columnar.decode_allocation(payload_of(instructions))
    backward = columnar.decode_allocation(payload_of(instructions[::-1]))
    assert forward.household_id == (0, 1, 2, 3)
    assert backward.household_id == (3, 2, 1, 0)
    assert payload_of(instructions) != payload_of(instructions[::-1])


def test_row_order_is_bound_by_the_identity_digest():
    instructions = cohort(4)
    forward = columnar.decode_allocation(payload_of(instructions)).header
    backward = columnar.decode_allocation(payload_of(instructions[::-1])).header
    assert forward["identity_sha256"] != backward["identity_sha256"]


def test_swapping_two_identity_cells_refuses_on_the_ordering_digest():
    payload = payload_of(narrow(3))
    _, bodies = split(payload)
    first = bytes(bodies["household_id"][0:8])
    second = bytes(bodies["household_id"][8:16])
    swapped = resealed(
        payload, [("household_id", 0, second), ("household_id", 1, first)]
    )
    with pytest.raises(columnar.AllocationColumnarError, match="IDENTITY_DIGEST"):
        columnar.decode_allocation(swapped)


def test_substituting_a_native_lexeme_refuses_on_the_ordering_digest():
    payload = payload_of(narrow(3))
    substituted = resealed(payload, [("raw_native_id_payload", 0, b"2024HU9999999")])
    with pytest.raises(columnar.AllocationColumnarError, match="IDENTITY_DIGEST"):
        columnar.decode_allocation(substituted)


def test_a_forged_identity_digest_is_refused():
    payload = payload_of()
    forged = reheaded(payload, lambda h: h.__setitem__("identity_sha256", "0" * 64))
    with pytest.raises(columnar.AllocationColumnarError, match="IDENTITY_DIGEST"):
        columnar.decode_allocation(forged)


# ---------------------------------------------------------------------------
# Corruption, truncation and length attacks
# ---------------------------------------------------------------------------


def test_magic_is_required():
    payload = payload_of()
    with pytest.raises(columnar.AllocationColumnarError, match="PAYLOAD_MAGIC"):
        columnar.decode_allocation(b"x" + payload[1:])


@pytest.mark.parametrize("keep", [0, 1, 20, 60, 120])
def test_a_truncated_payload_is_refused(keep):
    payload = payload_of()
    assert keep < len(payload)
    with pytest.raises(columnar.AllocationColumnarError):
        columnar.decode_allocation(payload[:keep])


def test_dropping_one_trailing_byte_is_refused():
    payload = payload_of()
    with pytest.raises(columnar.AllocationColumnarError, match="PAYLOAD_LENGTH"):
        columnar.decode_allocation(payload[:-1])


def test_appending_trailing_bytes_is_refused():
    payload = payload_of()
    with pytest.raises(columnar.AllocationColumnarError, match="PAYLOAD_LENGTH"):
        columnar.decode_allocation(payload + b"\x00")


def test_a_flipped_checksum_byte_is_refused():
    payload = payload_of()
    broken = payload[:-1] + bytes([payload[-1] ^ 0xFF])
    with pytest.raises(columnar.AllocationColumnarError, match="PAYLOAD_CHECKSUM"):
        columnar.decode_allocation(broken)


def test_a_flipped_body_byte_is_refused_by_the_envelope_checksum():
    payload = payload_of(narrow(3))
    _, bodies = split(payload)
    offset = len(payload) - 32 - sum(len(b) for b in bodies.values())
    broken = bytearray(payload)
    broken[offset] ^= 0xFF
    with pytest.raises(columnar.AllocationColumnarError, match="PAYLOAD_CHECKSUM"):
        columnar.decode_allocation(bytes(broken))


def test_a_body_edit_hidden_behind_a_repaired_checksum_is_refused_by_its_column():
    payload = payload_of(narrow(3))
    header, bodies = split(payload)
    bodies["household_id"][0] ^= 0xFF
    # The column digests are deliberately left stale; only the envelope
    # checksum is repaired, so the per-column digest is the guard under test.
    with pytest.raises(columnar.AllocationColumnarError, match="BODY_DIGEST"):
        columnar.decode_allocation(seal(header, bodies))


def test_a_declared_row_count_that_disagrees_with_the_bodies_is_refused():
    payload = payload_of()
    for delta in (1, -1):
        bad = reheaded(payload, lambda h, d=delta: h.__setitem__("rows", h["rows"] + d))
        with pytest.raises(columnar.AllocationColumnarError, match="COLUMN_SIZE"):
            columnar.decode_allocation(bad)


def test_an_inflated_column_length_is_refused_before_any_body_is_read():
    payload = payload_of()

    def inflate(header):
        header["columns"][-1]["bytes"] = columnar.MAX_ROWS * columnar.MAX_RATIONAL_BYTES

    bad = reheaded(payload, inflate)
    # _parse_header never slices a body, so a refusal raised by it proves the
    # bound was checked before the declared length could be allocated for.
    with pytest.raises(columnar.AllocationColumnarError, match="COLUMN_SIZE"):
        columnar._parse_header(bad, max_bytes=columnar.MAX_BYTES)


def test_a_per_column_legal_but_impossible_total_is_refused_before_any_body_is_read():
    payload = payload_of()
    rows = columnar.decode_allocation(payload).rows

    def inflate(header):
        header["columns"][-1]["bytes"] = rows * columnar.MAX_RATIONAL_BYTES

    bad = reheaded(payload, inflate)
    with pytest.raises(columnar.AllocationColumnarError, match="PAYLOAD_LENGTH"):
        columnar._parse_header(bad, max_bytes=columnar.MAX_BYTES)


def test_a_shrunken_fixed_column_length_is_refused():
    payload = payload_of()
    bad = reheaded(
        payload,
        lambda h: h["columns"][0].__setitem__("bytes", h["columns"][0]["bytes"] - 8),
    )
    with pytest.raises(columnar.AllocationColumnarError, match="COLUMN_SIZE"):
        columnar.decode_allocation(bad)


# ---------------------------------------------------------------------------
# Header schema, version and authority
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda h: h.__setitem__("claimed_authenticated", True), "HEADER_SCHEMA"),
        (lambda h: h.pop("identity_sha256"), "HEADER_SCHEMA"),
        (lambda h: h.pop("columns"), "HEADER_SCHEMA"),
        (
            lambda h: h.__setitem__("protocol", "microcosm.us.other.v2"),
            "HEADER_PROTOCOL",
        ),
        (lambda h: h.__setitem__("schema_version", 3), "HEADER_VERSION"),
        (lambda h: h.__setitem__("type", ["other", 2]), "HEADER_TYPE"),
        (
            lambda h: h.__setitem__("type", [columnar.ARTIFACT_TYPE_NAME, 1]),
            "HEADER_TYPE",
        ),
        (lambda h: h.__setitem__("body_endianness", "big"), "HEADER_ENDIANNESS"),
        (
            lambda h: h.__setitem__("header_length_endianness", "little"),
            "HEADER_ENDIANNESS",
        ),
        (
            lambda h: h.__setitem__("weight_transition", ["importance", "design"]),
            "HEADER_TRANSITION",
        ),
        (lambda h: h.__setitem__("release_eligible", True), "HEADER_AUTHORITY"),
        (lambda h: h.__setitem__("source_authenticated", True), "HEADER_AUTHORITY"),
        (lambda h: h.__setitem__("descriptive_only", False), "HEADER_AUTHORITY"),
        (lambda h: h.__setitem__("preparation_sha256", "z" * 64), "HEADER_DIGEST"),
        (lambda h: h.__setitem__("output_context_sha256", "abc"), "HEADER_DIGEST"),
        (lambda h: h.__setitem__("rows", 0), "ROW_LIMIT"),
        (lambda h: h.__setitem__("rows", True), "ROW_LIMIT"),
        (lambda h: h["columns"].pop(), "COLUMN_ROSTER"),
        (lambda h: h["columns"][0].__setitem__("name", "nope"), "COLUMN_ROSTER"),
        (lambda h: h["columns"][0].__setitem__("kind", "uint8"), "COLUMN_KIND"),
        (lambda h: h["columns"][0].__setitem__("extra", 1), "COLUMN_SCHEMA"),
        (lambda h: h["columns"][0].__setitem__("sha256", "nope"), "COLUMN_DIGEST"),
    ],
)
def test_an_unknown_wrong_or_forged_header_field_is_refused(mutate, code):
    bad = reheaded(payload_of(), mutate)
    with pytest.raises(columnar.AllocationColumnarError, match=code):
        columnar.decode_allocation(bad)


def test_a_reordered_or_respaced_header_spelling_is_refused():
    payload = payload_of()
    header, bodies = split(payload)
    # Same document, legal JSON, non-canonical bytes.
    encoded = json.dumps(header, sort_keys=False, indent=1).encode()
    parts = [
        columnar.MAGIC,
        len(encoded).to_bytes(4, "big"),
        encoded,
        *(bytes(bodies[name]) for name in columnar._BODY_NAMES),
    ]
    joined = b"".join(parts)
    with pytest.raises(columnar.AllocationColumnarError, match="HEADER_NOT_CANONICAL"):
        columnar.decode_allocation(joined + hashlib.sha256(joined).digest())


@pytest.mark.parametrize("length", [0, 0xFFFFFFFF, columnar.HEADER_MAX_BYTES])
def test_a_forged_header_length_field_is_refused(length):
    """The four-byte length prefix is bounded before it is used to slice."""
    payload = payload_of()
    start = len(columnar.MAGIC)
    forged = payload[:start] + length.to_bytes(4, "big") + payload[start + 4 :]
    with pytest.raises(columnar.AllocationColumnarError, match="HEADER_LENGTH"):
        columnar.decode_allocation(forged)


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda h: h.__setitem__("schema_version", 2.0), "HEADER_VERSION"),
        (
            lambda h: h.__setitem__("type", [columnar.ARTIFACT_TYPE_NAME, 2.0]),
            "HEADER_TYPE",
        ),
        (lambda h: h.__setitem__("type", [columnar.ARTIFACT_TYPE_NAME]), "HEADER_TYPE"),
        (lambda h: h.__setitem__("type", columnar.ARTIFACT_TYPE_NAME), "HEADER_TYPE"),
    ],
)
def test_a_float_or_malformed_version_spelling_is_refused(mutate, code):
    """``2.0 == 2`` in Python, so equality alone would admit a second byte form.

    Two canonical payloads decoding to identical values but hashing differently
    would give one allocation two identities.
    """
    with pytest.raises(columnar.AllocationColumnarError, match=code):
        columnar.decode_allocation(reheaded(payload_of(), mutate))


def test_a_header_that_is_not_json_is_refused():
    payload = payload_of()
    _, bodies = split(payload)
    encoded = b"not json at all"
    parts = [
        columnar.MAGIC,
        len(encoded).to_bytes(4, "big"),
        encoded,
        *(bytes(bodies[name]) for name in columnar._BODY_NAMES),
    ]
    joined = b"".join(parts)
    with pytest.raises(columnar.AllocationColumnarError, match="HEADER_JSON"):
        columnar.decode_allocation(joined + hashlib.sha256(joined).digest())


@pytest.mark.parametrize(
    ("codebook", "code"),
    [
        ({"acs": 0, "puf": 1}, "SOURCE_CODEBOOK"),
        ({"acs": 1, "asec": 2}, "SOURCE_CODEBOOK"),
        ({"acs": 0, "asec": 0}, "SOURCE_CODEBOOK"),
        ({}, "SOURCE_CODEBOOK"),
        # Anchored: "SOURCE_CODE" is a prefix of "SOURCE_CODEBOOK", so an
        # unanchored match would also pass if the codebook guard fired first.
        ({"acs": 0}, r"^SOURCE_CODE$"),
    ],
)
def test_a_malformed_or_short_source_codebook_is_refused(codebook, code):
    bad = reheaded(
        payload_of(cohort(2)), lambda h: h.__setitem__("source_codebook", codebook)
    )
    with pytest.raises(columnar.AllocationColumnarError, match=code):
        columnar.decode_allocation(bad)


def test_relabelling_the_source_codebook_is_refused_by_the_ordering_digest():
    """The header's codebook may not silently reassign every row's channel.

    Swapping the two entries changes no body byte and no column digest, so a
    digest over the numeric code alone would still match while every decoded
    row reported the other source. The digest folds the resolved channel
    string, which closes that.
    """
    payload = payload_of(cohort(2))
    relabelled = reheaded(
        payload, lambda h: h.__setitem__("source_codebook", {"acs": 1, "asec": 0})
    )
    with pytest.raises(columnar.AllocationColumnarError, match="IDENTITY_DIGEST"):
        columnar.decode_allocation(relabelled)


def test_the_declared_source_codebook_is_the_enum_definition_order():
    header = columnar.decode_allocation(payload_of(cohort(2))).header
    assert header["source_codebook"] == {"acs": 0, "asec": 1}


def test_an_out_of_codebook_source_code_is_refused():
    bad = resealed(payload_of(narrow(3)), [("source_code", 0, b"\x07")])
    with pytest.raises(columnar.AllocationColumnarError, match=r"^SOURCE_CODE$"):
        columnar.decode_allocation(bad)


# ---------------------------------------------------------------------------
# Redundant-field and rational consistency
# ---------------------------------------------------------------------------


def test_an_importance_multiplier_that_disagrees_with_its_parts_is_refused():
    bad = resealed(
        payload_of(narrow(3)), [("importance_multiplier_numerator_payload", 0, b"\x03")]
    )
    with pytest.raises(columnar.AllocationColumnarError, match="REDUNDANT_MULTIPLIER"):
        columnar.decode_allocation(bad)


def test_a_float_weight_that_disagrees_with_the_exact_rationals_is_refused():
    bad = resealed(
        payload_of(narrow(3)),
        [("importance_weight_float64", 0, struct.pack("<d", 25.0))],
    )
    with pytest.raises(columnar.AllocationColumnarError, match="REDUNDANT_WEIGHT"):
        columnar.decode_allocation(bad)


@pytest.mark.parametrize(
    "raw",
    [
        struct.pack("<d", -1.0),
        struct.pack("<d", -0.0),
        struct.pack("<d", float("inf")),
        struct.pack("<d", float("nan")),
    ],
)
def test_a_negative_or_non_finite_float_weight_is_refused(raw):
    bad = resealed(payload_of(narrow(3)), [("importance_weight_float64", 0, raw)])
    with pytest.raises(columnar.AllocationColumnarError, match="FLOAT_WEIGHT"):
        columnar.decode_allocation(bad)


@pytest.mark.parametrize(
    ("mutations", "code"),
    [
        ([("importance_multiplier_denominator_payload", 0, b"\x00")], "ROW_RATIONAL"),
        ([("share_denominator_payload", 0, b"\x00")], "ROW_RATIONAL"),
        (
            [
                ("importance_multiplier_numerator_payload", 0, b"\x04"),
                ("importance_multiplier_denominator_payload", 0, b"\x02"),
            ],
            "ROW_RATIONAL",
        ),
        ([("original_anchor_denominator_payload", 0, b"\xff")], "ROW_RATIONAL"),
    ],
)
def test_a_zero_unreduced_or_negative_denominator_is_refused(mutations, code):
    bad = resealed(payload_of(narrow(3)), mutations)
    with pytest.raises(columnar.AllocationColumnarError, match=code):
        columnar.decode_allocation(bad)


def test_a_zero_inclusion_probability_is_a_refusal_not_a_division_error():
    with pytest.raises(columnar.AllocationColumnarError, match="ROW_RATIONAL"):
        payload_of((instruction(0, probability=Fraction(0)),))
    # Both cells are rewritten so the crafted probability is exactly 0/1: a
    # lone zero numerator over the original denominator would be caught as an
    # unreduced rational and never reach the division guard under test.
    bad = resealed(
        payload_of(narrow(3)),
        [
            ("inclusion_probability_numerator_payload", 0, b"\x00"),
            ("inclusion_probability_denominator_payload", 0, b"\x01"),
        ],
    )
    with pytest.raises(columnar.AllocationColumnarError, match="ROW_RATIONAL"):
        columnar.decode_allocation(bad)


@pytest.mark.parametrize(
    "value",
    [0, 1, -1, 127, 128, -128, 255, -255, 2**63, -(2**63), 10**50, -(10**50)],
)
def test_the_canonical_integer_form_round_trips_signed_values(value):
    raw = columnar._encode_int(value, "ROW_RATIONAL")
    assert columnar._decode_int(raw, "ROW_RATIONAL") == value
    assert len(raw) == columnar._canonical_int_length(value)


@pytest.mark.parametrize(
    "raw",
    [
        b"\x00\x01",
        b"\x00\x00\x7f",
        b"\xff\xff\x80",
        b"\x80",
        b"",
        b"\x00" * (columnar.MAX_RATIONAL_BYTES + 1),
    ],
)
def test_a_padded_over_long_or_empty_integer_is_refused(raw):
    with pytest.raises(columnar.AllocationColumnarError, match="ROW_RATIONAL"):
        columnar._decode_int(raw, "ROW_RATIONAL")


# ---------------------------------------------------------------------------
# Encoder-side value contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"household_id": True}, "ROW_INTEGER"),
        ({"household_id": -1}, "ROW_INTEGER"),
        ({"household_id": 2**63}, "ROW_INTEGER"),
        ({"household_id": 1.0}, "ROW_INTEGER"),
        ({"receiving": -1}, "ROW_INTEGER"),
        ({"receiving": True}, "ROW_INTEGER"),
        ({"source_year": True}, "ROW_INTEGER"),
        ({"source_year": 2024.0}, "ROW_INTEGER"),
        ({"anchor": 13}, "ROW_RATIONAL"),
        ({"anchor": 13.0}, "ROW_RATIONAL"),
        ({"share": True}, "ROW_RATIONAL"),
        ({"probability": "1/2"}, "ROW_RATIONAL"),
        ({"native": 7}, "ROW_LEXEME"),
    ],
)
def test_a_row_value_of_the_wrong_type_or_range_is_refused(changes, code):
    with pytest.raises(columnar.AllocationColumnarError, match=code):
        payload_of((instruction(0, **changes),))


def test_a_row_missing_the_household_key_is_refused():
    class Bare:
        household_id = 1
        selected_receiving_household_id = 1
        original_anchor = Fraction(1)
        share = Fraction(1, 2)
        inclusion_probability = Fraction(1, 2)

    with pytest.raises(columnar.AllocationColumnarError, match="ROW_KEY"):
        payload_of((Bare(),))


def test_a_household_key_carrying_a_plain_string_source_is_refused():
    row = instruction(0)
    forged = graph.AllocationInstruction(
        row.household_id,
        HouseholdKey("acs", 2024, 2024, row.key.native_id),
        row.selected_receiving_household_id,
        row.original_anchor,
        row.share,
        row.inclusion_probability,
    )
    with pytest.raises(columnar.AllocationColumnarError, match="ROW_SOURCE"):
        payload_of((forged,))


@pytest.mark.parametrize("axis", ["household_id", "native", "receiving"])
def test_duplicate_identities_are_refused_by_the_encoder(axis):
    first = instruction(0)
    changes = {
        "household_id": {"household_id": 0},
        "native": {"native": first.key.native_id},
        "receiving": {"receiving": 0},
    }[axis]
    with pytest.raises(columnar.AllocationColumnarError, match="ROW_DUPLICATE"):
        payload_of((first, instruction(1, **changes)))


def test_an_empty_allocation_is_refused():
    with pytest.raises(columnar.AllocationColumnarError, match="EMPTY_ALLOCATION"):
        payload_of(())


@pytest.mark.parametrize(
    ("preparation", "code"),
    [("b" * 63, "PREPARATION_DIGEST"), ("Z" * 64, "PREPARATION_DIGEST")],
)
def test_a_malformed_preparation_digest_is_refused(preparation, code):
    with pytest.raises(columnar.AllocationColumnarError, match=code):
        payload_of(preparation_sha256=preparation)


@pytest.mark.parametrize("context", [b"", "{}", None])
def test_a_missing_or_non_byte_context_is_refused(context):
    with pytest.raises(columnar.AllocationColumnarError, match="CONTEXT_BYTES"):
        payload_of(input_context=context)


# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------


def test_the_row_bound_is_checked_while_streaming(monkeypatch):
    monkeypatch.setattr(columnar, "MAX_ROWS", 2)
    with pytest.raises(columnar.AllocationColumnarError, match="ROW_LIMIT"):
        payload_of(cohort(3))


def test_the_byte_bound_admits_the_exact_size_and_refuses_one_byte_less():
    instructions = cohort(4)
    payload = payload_of(instructions)
    assert payload_of(instructions, max_bytes=len(payload)) == payload
    with pytest.raises(columnar.AllocationColumnarError, match="ALLOCATION_LIMIT"):
        payload_of(instructions, max_bytes=len(payload) - 1)


def test_the_streaming_bound_refuses_before_the_buffers_grow():
    with pytest.raises(columnar.AllocationColumnarError, match="ALLOCATION_LIMIT"):
        payload_of(cohort(64), max_bytes=200)


@pytest.mark.parametrize("limit", [0, -1, columnar.MAX_BYTES + 1])
def test_an_out_of_range_transport_limit_is_refused(limit):
    with pytest.raises(columnar.AllocationColumnarError, match="TRANSPORT_LIMIT"):
        payload_of(max_bytes=limit)
    with pytest.raises(columnar.AllocationColumnarError, match="TRANSPORT_LIMIT"):
        columnar.decode_allocation(payload_of(), max_bytes=limit)


def test_a_payload_larger_than_the_decoder_bound_is_refused():
    payload = payload_of()
    with pytest.raises(columnar.AllocationColumnarError, match="PAYLOAD_SIZE"):
        columnar.decode_allocation(payload, max_bytes=len(payload) - 1)


@pytest.mark.parametrize("value", [None, "payload", bytearray(b"x"), memoryview(b"x")])
def test_a_non_bytes_payload_is_refused(value):
    with pytest.raises(columnar.AllocationColumnarError, match="PAYLOAD_TYPE"):
        columnar.decode_allocation(value)


def test_the_declared_artifact_type_is_pinned_to_the_host_declaration():
    """The hand-copied type literal must not drift from the host it names."""
    assert columnar.ARTIFACT_TYPE_NAME == graph.ALLOCATION_TYPE.name
    assert columnar.ARTIFACT_SCHEMA_VERSION == graph.ALLOCATION_TYPE.schema_version + 1


def test_the_declared_bounds_match_the_v1_host_and_are_not_raised():
    assert columnar.MAX_BYTES == graph.ALLOCATION_MAX_BYTES
    assert columnar.MAX_ROWS == graph.ALLOCATION_MAX_BYTES // 128
    assert columnar.MAX_NATIVE_ID_CHARS == 128


# ---------------------------------------------------------------------------
# The public manifest and the absence of authority
# ---------------------------------------------------------------------------


def private_cohort():
    """Rows whose every asserted value is long enough to be a real absence.

    The manifest legitimately carries four SHA-256 digests. A short literal such
    as ``"25"`` appears inside 64 characters of hexadecimal text most of the
    time, so every identifier and numerator below is at least ten digits and the
    two-digit denominators are deliberately not asserted on.
    """

    return (
        instruction(
            0,
            household_id=9007199254740993,
            receiving=4611686018427387904,
            native="2024HU7654321",
            anchor=Fraction(638031234567891, 25),
        ),
        instruction(
            1,
            source=Source.ASEC,
            household_id=8888888888888881,
            receiving=7777777777777771,
            native="9182736455",
            anchor=Fraction(191409876543211, 50),
        ),
    )


def test_the_public_manifest_exposes_no_native_id_or_row_value():
    instructions = private_cohort()
    payload = columnar.encode_allocation(instructions, **KWARGS)
    rendered = canonical_json(columnar.allocation_manifest(payload)).decode()
    for row in instructions:
        assert row.key.native_id not in rendered
        assert str(row.household_id) not in rendered
        assert str(row.selected_receiving_household_id) not in rendered
        assert str(row.original_anchor.numerator) not in rendered
        assert float(row.importance_weight).hex() not in rendered
        assert str(row.key.source.value) not in rendered


def test_the_public_manifest_omits_the_identity_and_column_digests():
    manifest = columnar.allocation_manifest(payload_of(private_cohort()))
    assert "identity_sha256" not in manifest
    assert all(
        set(column) == {"name", "kind", "bytes"} for column in manifest["columns"]
    )
    # Pin the guard itself, not only the shape it happens to produce, so a
    # later edit that widens either roster fails here.
    assert columnar._MANIFEST_COLUMN_KEYS == frozenset({"name", "kind", "bytes"})
    assert "identity_sha256" in columnar._PRIVATE_HEADER_KEYS
    decoded = columnar.decode_allocation(payload_of(private_cohort()))
    assert decoded.header["identity_sha256"] not in canonical_json(manifest).decode()


def test_the_public_manifest_reports_shape_and_claims_no_authority():
    instructions = private_cohort()
    payload = columnar.encode_allocation(instructions, **KWARGS)
    manifest = columnar.allocation_manifest(payload)
    assert manifest["rows"] == len(instructions)
    assert manifest["protocol"] == columnar.PROTOCOL
    assert manifest["schema_version"] == 2
    assert manifest["total_bytes"] == len(payload)
    # The payload digest is deliberately absent: the encoder is deterministic,
    # so publishing it beside the exact column lengths would let a holder who
    # knew all but one native lexeme re-encode each candidate and confirm it.
    assert "payload_sha256" not in manifest
    assert "source_codebook" not in manifest
    assert manifest["header_bytes"] + manifest["body_bytes"] + len(
        columnar.MAGIC
    ) + 4 + 32 == len(payload)
    assert [column["name"] for column in manifest["columns"]] == list(
        columnar._BODY_NAMES
    )
    assert manifest["release_eligible"] is False
    assert manifest["source_authenticated"] is False
    assert manifest["descriptive_only"] is True
    header = columnar.decode_allocation(payload).header
    for key in (
        "preparation_sha256",
        "input_context_sha256",
        "output_context_sha256",
    ):
        assert manifest[key] == header[key]


def test_the_manifest_refuses_the_same_malformed_payloads_the_decoder_does():
    with pytest.raises(columnar.AllocationColumnarError, match="PAYLOAD_LENGTH"):
        columnar.allocation_manifest(payload_of() + b"\x00")


def test_the_manifest_refuses_a_payload_whose_seal_is_broken():
    """A manifest must never republish provenance digests over rewritten bodies.

    Without the envelope check the header parses cleanly, so the manifest would
    report the producer's untouched preparation and context digests over column
    bodies an attacker controls.
    """
    payload = payload_of(narrow(3))
    _, bodies = split(payload)
    offset = len(payload) - 32 - sum(len(body) for body in bodies.values())
    broken = bytearray(payload)
    broken[offset] ^= 0xFF
    with pytest.raises(columnar.AllocationColumnarError, match="PAYLOAD_CHECKSUM"):
        columnar.allocation_manifest(bytes(broken))
    with pytest.raises(columnar.AllocationColumnarError, match="PAYLOAD_CHECKSUM"):
        columnar.decode_allocation(bytes(broken))


def test_a_decoder_issues_no_source_or_release_authority():
    decoded = columnar.decode_allocation(payload_of())
    assert decoded.source_authenticated is False
    assert decoded.population_binding_authenticated is False
    assert decoded.release_eligible is False
    assert "issued_preparation_bytes" in decoded.required_bindings
    assert "materialized_population_and_weight_kind" in decoded.required_bindings


# ---------------------------------------------------------------------------
# Roster and host-parity invariants
# ---------------------------------------------------------------------------


def test_the_body_roster_is_closed_and_matches_the_sealed_header():
    names = [name for name, _ in columnar.BODY_ROSTER]
    assert len(names) == len(set(names))
    assert {kind for _, kind in columnar.BODY_ROSTER} <= {
        "int64-le",
        "uint8",
        "uint16-le",
        "float64-le-bits",
        "utf8-payload",
        "int-be-twos-complement-payload",
    }
    header = columnar.decode_allocation(payload_of()).header
    assert [column["name"] for column in header["columns"]] == names
    assert [column["kind"] for column in header["columns"]] == [
        kind for _, kind in columnar.BODY_ROSTER
    ]


@pytest.mark.parametrize(
    "value",
    [
        Fraction(0),
        Fraction(13),
        Fraction(63803, 25),
        Fraction(-1),
        Fraction(10**400),
        Fraction(1, 10**400),
    ],
)
def test_the_local_weight_check_agrees_with_the_host_on_every_verdict(value):
    try:
        expected = graph._finite_weight(value)
    except graph.SurveyPopulationGraphError:
        with pytest.raises(columnar.AllocationColumnarError, match="FLOAT_WEIGHT"):
            columnar._checked_weight(value, "FLOAT_WEIGHT")
        return
    assert columnar._checked_weight(value, "FLOAT_WEIGHT") == expected


def test_the_encoder_accepts_instructions_built_by_the_real_allocation_join():
    from test_us_graph_survey_population import plan_and_origins

    plan, origins = plan_and_origins()
    instructions = graph.allocation_instructions(plan, origins)
    decoded = columnar.decode_allocation(
        columnar.encode_allocation(instructions, **KWARGS)
    )
    assert (
        list(decoded.legacy_instruction_documents())
        == json.loads(graph._allocation_payload(instructions, **KWARGS))["households"]
    )


# ---------------------------------------------------------------------------
# Source-defined byte-count comparison
# ---------------------------------------------------------------------------


def test_v2_carries_a_modest_synthetic_cohort_in_fewer_bytes_than_v1():
    """Count bytes from both encoders on identical invented rows.

    This is a byte count, not a measurement: it says nothing about wall time,
    memory or any real cohort, whose native-lexeme and fraction widths are not
    represented here. The synthetic rows are deliberately favourable to v1 -
    short ASCII lexemes and one- or two-digit rationals - so the comparison is
    conservative.
    """
    instructions = cohort(2000)
    v1 = graph._allocation_payload(instructions, **KWARGS)
    v2 = columnar.encode_allocation(instructions, **KWARGS)
    assert columnar.decode_allocation(v2).rows == 2000
    assert len(v2) < len(v1)
