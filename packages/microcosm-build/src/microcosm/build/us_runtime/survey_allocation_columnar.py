"""A compact, deterministic, versioned columnar transport for allocation rows.

The default host still emits the row-wise JSON allocation payload declared in
:mod:`microcosm.build.us_runtime.graph_survey_population`. That payload repeats
eleven JSON keys for every selected household, so its byte size is dominated by
key text rather than by the values it carries. This module is the bytes-only v2
alternative: one bounded canonical header followed by fixed-width and
length-prefixed column bodies, with no repeated key text and no row-wise JSON
object tree on either side.

Nothing here reads a source, constructs a Frame, applies weights or touches a
store. Encoding a value does not authenticate it; decoding a payload proves only
that the bytes are internally consistent and that their redundant fields agree.
A decoder is descriptive: it cannot issue source, population or release
authority, and :class:`DecodedAllocation` reports exactly that. The declaration
and host-integration decision stay with the graph owner.

Layout, all lengths in bytes::

    MAGIC                                    len(MAGIC)
    header length, big-endian unsigned       4
    canonical JSON header                    header length
    column bodies, in ``BODY_ROSTER`` order  sum of declared body lengths
    sha256 of everything above               32

Integer columns use explicit little-endian widths, so a payload written on one
platform reads back identically on another. Exact rationals are two
length-prefixed big-endian two's-complement integer streams per field, which
keeps arbitrary-precision numerators and denominators exact without a decimal
rendering. The float64 importance weight is stored as its own eight raw bytes,
so its bits survive the round trip without going through text.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType

from microcosm.graph.canonical import canonical_json

from .survey_population_domains import HouseholdKey, Source

__all__ = [
    "ARTIFACT_SCHEMA_VERSION",
    "ARTIFACT_TYPE_NAME",
    "BODY_ROSTER",
    "HEADER_MAX_BYTES",
    "MAGIC",
    "MAX_BYTES",
    "MAX_NATIVE_ID_BYTES",
    "MAX_NATIVE_ID_CHARS",
    "MAX_RATIONAL_BYTES",
    "MAX_ROWS",
    "PROTOCOL",
    "SCHEMA_VERSION",
    "AllocationColumnarError",
    "DecodedAllocation",
    "allocation_manifest",
    "decode_allocation",
    "encode_allocation",
]

PROTOCOL = "microcosm.us.survey-population-allocation.v2"
SCHEMA_VERSION = 2

#: The artifact type a host would declare for this payload. The name is the
#: literal declared by ``graph_survey_population.ALLOCATION_TYPE``; the schema
#: version is the successor. This module deliberately does not import that
#: declaration: it would pull the graph, numpy and pandas behind a transport
#: that needs none of them, and would make the codec depend on the very host it
#: is meant to be reviewed independently of.
ARTIFACT_TYPE_NAME = "microcosm.us.survey_population_allocation"
ARTIFACT_SCHEMA_VERSION = 2

MAGIC = b"microcosm.us.survey-population-allocation/2\n"

#: Bound on the canonical JSON header, as in the PUF raw-source envelope.
HEADER_MAX_BYTES = 64 * 1024

#: The shared opaque-payload bound. This is exactly
#: ``graph_survey_population.ALLOCATION_MAX_BYTES``; it is repeated rather than
#: imported for the reason above, and it is deliberately not raised. A v2
#: payload fits more rows under the same ceiling because it carries fewer
#: bytes per row, not because the ceiling moved.
MAX_BYTES = 64 * 1024**2

#: The prospective record bound, identical to the one ``allocation_instructions``
#: applies before it builds its maps (``ALLOCATION_MAX_BYTES // 128``). A more
#: generous bound would be arithmetically defensible here, and is not taken.
MAX_ROWS = MAX_BYTES // 128

#: The widest native source lexeme the allocation join admits, and its widest
#: UTF-8 rendering. Both are transport bounds, not a claim about any source.
MAX_NATIVE_ID_CHARS = 128
MAX_NATIVE_ID_BYTES = 4 * MAX_NATIVE_ID_CHARS

#: The widest exact numerator or denominator this transport carries: 16384 bits.
#: Derived, not chosen: v1 bounds a whole row document at 4096 JSON bytes, so
#: the widest single integer v1 can carry is under 4000 decimal digits, about
#: 1620 bytes. This exceeds that, so a host switching transports cannot start
#: refusing a rational it previously emitted. Rationals reaching allocation are
#: ratios of publisher weights and declared shares, far below either figure,
#: but the bound is enforced rather than assumed.
MAX_RATIONAL_BYTES = 2048

#: The widest source codebook a payload may declare.
MAX_SOURCE_CODES = 16

_HEADER_LENGTH_BYTES = 4
_DIGEST_BYTES = 32
_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1

_KIND_INT64 = "int64-le"
_KIND_UINT8 = "uint8"
_KIND_UINT16 = "uint16-le"
_KIND_FLOAT64 = "float64-le-bits"
_KIND_LEXEME_PAYLOAD = "utf8-payload"
_KIND_INTEGER_PAYLOAD = "int-be-twos-complement-payload"

_FIXED_WIDTH = MappingProxyType(
    {_KIND_INT64: 8, _KIND_UINT8: 1, _KIND_UINT16: 2, _KIND_FLOAT64: 8}
)
_VARIABLE_ROW_MAX = MappingProxyType(
    {
        _KIND_LEXEME_PAYLOAD: MAX_NATIVE_ID_BYTES,
        _KIND_INTEGER_PAYLOAD: MAX_RATIONAL_BYTES,
    }
)

#: The four exact rational fields, in declared order. ``importance_multiplier``
#: is redundant with ``share / inclusion_probability`` and is carried anyway,
#: because the v1 document carries it; the decoder recomputes and compares it
#: rather than trusting it.
RATIONAL_FIELDS = (
    "original_anchor",
    "share",
    "inclusion_probability",
    "importance_multiplier",
)

_HEADER_KEYS = frozenset(
    {
        "protocol",
        "schema_version",
        "type",
        "rows",
        "header_length_endianness",
        "body_endianness",
        "columns",
        "source_codebook",
        "preparation_sha256",
        "input_context_sha256",
        "output_context_sha256",
        "identity_sha256",
        "weight_transition",
        "release_eligible",
        "source_authenticated",
        "descriptive_only",
    }
)
_COLUMN_KEYS = frozenset({"name", "kind", "bytes", "sha256"})

#: Fields the public manifest never reports: every one of them is, or digests,
#: a native identifier or a row value.
_PRIVATE_HEADER_KEYS = frozenset({"identity_sha256"})

#: The only keys a manifest column may carry. The header's per-column ``sha256``
#: is a digest over row values, so it is withheld; naming the permitted set here
#: lets the manifest guard cover the nested shape as well as the top level.
_MANIFEST_COLUMN_KEYS = frozenset({"name", "kind", "bytes"})

_IDENTITY_DOMAIN = b"microcosm.us.survey-population-allocation.v2/identity\0"

_WEIGHT_TRANSITION = ("design", "importance")
_HEX = frozenset("0123456789abcdef")


def _body_roster():
    roster = [
        ("household_id", _KIND_INT64),
        ("selected_receiving_household_id", _KIND_INT64),
        ("source_year", _KIND_INT64),
        ("survey_year", _KIND_INT64),
        ("source_code", _KIND_UINT8),
        ("importance_weight_float64", _KIND_FLOAT64),
        ("raw_native_id_lengths", _KIND_UINT16),
        ("raw_native_id_payload", _KIND_LEXEME_PAYLOAD),
    ]
    for field in RATIONAL_FIELDS:
        for part in ("numerator", "denominator"):
            roster.append((f"{field}_{part}_lengths", _KIND_UINT16))
            roster.append((f"{field}_{part}_payload", _KIND_INTEGER_PAYLOAD))
    return tuple(roster)


#: Every column body, in the exact order it is written and read.
BODY_ROSTER = _body_roster()
_BODY_NAMES = tuple(name for name, _ in BODY_ROSTER)
_BODY_KINDS = MappingProxyType(dict(BODY_ROSTER))


class AllocationColumnarError(ValueError):
    """A refusal code. Messages never carry a source value, lexeme or path."""


def _require(condition, code):
    if not condition:
        raise AllocationColumnarError(code)


def _sha(payload):
    return hashlib.sha256(payload).hexdigest()


def _digest64(value, code):
    _require(
        type(value) is str and len(value) == 64 and not set(value) - _HEX,
        code,
    )
    return value


def _exact_int(value, code, *, minimum=_INT64_MIN, maximum=_INT64_MAX):
    # ``type(value) is int`` rather than ``isinstance``: ``True`` is an int
    # subclass, and a boolean identity is never an allocation integer.
    _require(type(value) is int and minimum <= value <= maximum, code)
    return value


def _canonical_int_length(value):
    """The one length this transport accepts for ``value``.

    Minimal-length big-endian two's complement, except that a negative power of
    two is written one byte wider than its shortest form. The rule matters less
    than its exactness: a decoder recomputes this length from the value it read
    and refuses any other, so a padded, truncated or over-long integer is a
    refusal rather than an alternative spelling of the same number.
    """

    return max(1, (value.bit_length() + 8) // 8)


def _encode_int(value, code):
    # The width is decided from the value's bit length before anything is
    # built, so an out-of-range integer is refused without first materialising
    # an over-long encoding, and the admissible range is exactly the range that
    # round trips rather than a wider one the size check later rejects.
    _require(type(value) is int, code)
    length = _canonical_int_length(value)
    _require(length <= MAX_RATIONAL_BYTES, code)
    return value.to_bytes(length, "big", signed=True)


def _decode_int(raw, code):
    _require(0 < len(raw) <= MAX_RATIONAL_BYTES, code)
    value = int.from_bytes(raw, "big", signed=True)
    _require(_canonical_int_length(value) == len(raw), code)
    return value


def _checked_fraction(value, code):
    _require(type(value) is Fraction, code)
    # Fraction normalises on construction, so this holds for anything built
    # through the public constructor; it is asserted because the decoder
    # rebuilds fractions from two independently transported integers.
    _require(value.denominator > 0, code)
    _require(math.gcd(abs(value.numerator), value.denominator) == 1, code)
    return value


def _checked_weight(value, code):
    """Mirror ``graph_survey_population._finite_weight`` for an exact rational.

    The two implementations are deliberately independent — importing the host
    would reverse the dependency this module exists to avoid — and a parity test
    holds them to the same verdict on the same inputs.
    """

    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise AllocationColumnarError(code) from None
    _require(math.isfinite(number) and number >= 0 and (value == 0 or number > 0), code)
    return number


def _fold_identity(
    digest, *, household_id, source, source_year, survey_year, native, receiving
):
    """Fold one row's identity into the ordering digest, in a fixed field order.

    The source is folded as its own value string, not as the numeric code the
    body carries. Folding the code would leave the header's ``source_codebook``
    free to relabel every row: swapping the two entries changes no body byte and
    no column digest, so a code-only digest would still match while every
    decoded row reported the other channel. Binding the resolved string closes
    that, because the meaning of the code is then inside the digest.

    Encoder and decoder both call this, so the two can never drift apart.
    """

    digest.update(household_id.to_bytes(8, "little", signed=True))
    channel = source.value.encode("utf-8")
    digest.update(len(channel).to_bytes(2, "little"))
    digest.update(channel)
    digest.update(source_year.to_bytes(8, "little", signed=True))
    digest.update(survey_year.to_bytes(8, "little", signed=True))
    digest.update(len(native).to_bytes(2, "little"))
    digest.update(native)
    digest.update(receiving.to_bytes(8, "little", signed=True))


def _source_codebook():
    """The current ``Source`` codebook, in definition order.

    Bounded here as well as on the decode side: the source code is written as
    one byte, so a ``Source`` that ever grew past this roster must be a refusal
    rather than an ``OverflowError`` from ``int.to_bytes``.
    """

    codebook = {member.value: index for index, member in enumerate(Source)}
    _require(0 < len(codebook) <= MAX_SOURCE_CODES, "SOURCE_CODEBOOK")
    return codebook


def _checked_codebook(raw):
    _require(type(raw) is dict and 0 < len(raw) <= MAX_SOURCE_CODES, "SOURCE_CODEBOOK")
    _require(
        all(type(key) is str for key in raw)
        and all(type(code) is int for code in raw.values()),
        "SOURCE_CODEBOOK",
    )
    _require(sorted(raw.values()) == list(range(len(raw))), "SOURCE_CODEBOOK")
    members = {}
    for value, code in raw.items():
        try:
            members[code] = Source(value)
        except ValueError:
            raise AllocationColumnarError("SOURCE_CODEBOOK") from None
    return members


@dataclass(frozen=True, slots=True)
class DecodedAllocation:
    """Columnar values read back from a v2 payload. It authenticates nothing.

    The columns are parallel tuples in the payload's own row order, which the
    encoder preserved exactly. No row-shaped object is built during decoding;
    :meth:`legacy_instruction_documents` renders rows one at a time for callers
    that need the v1 document shape.
    """

    header: MappingProxyType
    household_id: tuple
    selected_receiving_household_id: tuple
    source: tuple
    source_year: tuple
    survey_year: tuple
    raw_native_id: tuple
    original_anchor: tuple
    share: tuple
    inclusion_probability: tuple
    importance_multiplier: tuple
    importance_weight: tuple

    @property
    def rows(self) -> int:
        return len(self.household_id)

    @property
    def source_authenticated(self) -> bool:
        return False

    @property
    def population_binding_authenticated(self) -> bool:
        return False

    @property
    def release_eligible(self) -> bool:
        return False

    @property
    def required_bindings(self) -> tuple[str, ...]:
        """What a caller still needs before these values may bind a population."""

        return (
            "issued_preparation_bytes",
            "producer_artifact_edge_and_key",
            "materialized_population_and_weight_kind",
            "input_and_output_frame_context_bytes",
        )

    def household_keys(self):
        """Yield the ``HouseholdKey`` for each row, in payload order."""

        for index in range(self.rows):
            yield HouseholdKey(
                self.source[index],
                self.source_year[index],
                self.survey_year[index],
                self.raw_native_id[index],
            )

    def legacy_instruction_documents(self):
        """Yield the exact v1 ``_instruction_document`` mapping for each row.

        This is the parity bridge. It renders the v1 shape on demand and never
        materialises the full list, so a caller comparing against a v1 payload
        does not pay for a second complete row tree.
        """

        for index in range(self.rows):
            yield {
                "household_id": self.household_id[index],
                "source": self.source[index].value,
                "source_year": self.source_year[index],
                "survey_year": self.survey_year[index],
                "raw_native_id": self.raw_native_id[index],
                "selected_receiving_household_id": (
                    self.selected_receiving_household_id[index]
                ),
                "original_anchor": [
                    self.original_anchor[index].numerator,
                    self.original_anchor[index].denominator,
                ],
                "share": [
                    self.share[index].numerator,
                    self.share[index].denominator,
                ],
                "inclusion_probability": [
                    self.inclusion_probability[index].numerator,
                    self.inclusion_probability[index].denominator,
                ],
                "importance_multiplier": [
                    self.importance_multiplier[index].numerator,
                    self.importance_multiplier[index].denominator,
                ],
                "importance_weight_float64_hex": self.importance_weight[index].hex(),
            }


class _Bodies:
    """Column buffers with a running total checked before every append.

    The bound covers the magic, the bodies and the trailing checksum, but not
    the header, whose size is not known until the last row has been read. The
    buffers therefore never exceed ``limit``, and the sealed payload never
    exceeds ``limit``.

    Peak process memory is a small multiple of ``limit``, not ``limit`` itself:
    the buffers, the frozen copies :meth:`frozen` takes of them, and the joined
    result are live together at the seal. A caller sizing a worker against the
    default 64 MiB ceiling should budget for that multiple.
    """

    __slots__ = ("_buffers", "_limit", "total")

    def __init__(self, limit):
        self._buffers = {name: bytearray() for name in _BODY_NAMES}
        self._limit = limit
        self.total = 0

    def append(self, name, raw):
        # Checked before the extend, so an over-long row is refused rather than
        # appended and then noticed.
        _require(
            len(MAGIC) + _HEADER_LENGTH_BYTES + self.total + len(raw) + _DIGEST_BYTES
            <= self._limit,
            "ALLOCATION_LIMIT",
        )
        self.total += len(raw)
        self._buffers[name].extend(raw)

    def frozen(self):
        return {name: bytes(buffer) for name, buffer in self._buffers.items()}


def _row_values(row):
    """Read the seven allocation values off one row, with exact types.

    The host's ``AllocationInstruction`` satisfies this structurally. It is read
    by attribute rather than by class so that the transport does not import the
    graph module that defines it; every value is still type-checked exactly, so
    a row carrying a float anchor, a boolean identifier or a plain string source
    is refused here rather than silently narrowed.
    """

    key = getattr(row, "key", None)
    _require(type(key) is HouseholdKey, "ROW_KEY")
    _require(type(key.source) is Source, "ROW_SOURCE")
    native = key.native_id
    _require(
        type(native) is str and 0 < len(native) <= MAX_NATIVE_ID_CHARS, "ROW_LEXEME"
    )
    return {
        "household_id": _exact_int(
            getattr(row, "household_id", None), "ROW_INTEGER", minimum=0
        ),
        "selected_receiving_household_id": _exact_int(
            getattr(row, "selected_receiving_household_id", None),
            "ROW_INTEGER",
            minimum=0,
        ),
        "source": key.source,
        "source_year": _exact_int(key.source_year, "ROW_INTEGER"),
        "survey_year": _exact_int(key.survey_year, "ROW_INTEGER"),
        "raw_native_id": native,
        "original_anchor": _checked_fraction(
            getattr(row, "original_anchor", None), "ROW_RATIONAL"
        ),
        "share": _checked_fraction(getattr(row, "share", None), "ROW_RATIONAL"),
        "inclusion_probability": _checked_fraction(
            getattr(row, "inclusion_probability", None), "ROW_RATIONAL"
        ),
    }


def encode_allocation(
    instructions,
    *,
    preparation_sha256,
    input_context,
    output_context,
    max_bytes=MAX_BYTES,
):
    """Stream rows into column buffers and seal them in one bounded envelope.

    ``instructions`` is any iterable of rows carrying the allocation values;
    ``graph_survey_population.AllocationInstruction`` is the intended one. The
    two context arguments are the same byte strings the v1 payload digests, so
    a v1 and a v2 payload built from one allocation report identical
    ``input_context_sha256`` and ``output_context_sha256``.

    No row-shaped intermediate is built: each row is consumed once, written into
    its columns, folded into the ordering digest and dropped.
    """

    _require(type(max_bytes) is int and 0 < max_bytes <= MAX_BYTES, "TRANSPORT_LIMIT")
    _digest64(preparation_sha256, "PREPARATION_DIGEST")
    _require(type(input_context) is bytes and input_context, "CONTEXT_BYTES")
    _require(type(output_context) is bytes and output_context, "CONTEXT_BYTES")

    codebook = _source_codebook()
    bodies = _Bodies(max_bytes)
    identity = hashlib.sha256(_IDENTITY_DOMAIN)
    seen_ids, seen_native, seen_receiving = set(), set(), set()
    rows = 0

    for row in instructions:
        rows += 1
        _require(rows <= MAX_ROWS, "ROW_LIMIT")
        values = _row_values(row)
        # A zero inclusion probability is a refusal, not a ZeroDivisionError
        # escaping this module as an unclassified exception.
        _require(values["inclusion_probability"] != 0, "ROW_RATIONAL")
        multiplier = values["share"] / values["inclusion_probability"]
        weight = _checked_weight(values["original_anchor"] * multiplier, "FLOAT_WEIGHT")
        _checked_weight(values["original_anchor"], "FLOAT_WEIGHT")

        household_id = values["household_id"]
        receiving = values["selected_receiving_household_id"]
        source = values["source"]
        try:
            native = values["raw_native_id"].encode("utf-8")
        except UnicodeEncodeError:
            # A lone surrogate - what a surrogateescape decode of malformed
            # source bytes produces - is a refusal code, not a stray
            # UnicodeEncodeError whose message would quote the lexeme.
            raise AllocationColumnarError("ROW_LEXEME") from None
        # Implied by the character bound, since UTF-8 emits at most four bytes
        # per code point and MAX_NATIVE_ID_BYTES is four times that bound. Kept
        # so the byte column's own invariant is stated where it is written, and
        # so the two constants cannot drift apart unnoticed.
        _require(len(native) <= MAX_NATIVE_ID_BYTES, "ROW_LEXEME")
        native_key = (
            source,
            values["source_year"],
            values["survey_year"],
            values["raw_native_id"],
        )
        _require(
            household_id not in seen_ids
            and native_key not in seen_native
            and (source, receiving) not in seen_receiving,
            "ROW_DUPLICATE",
        )
        seen_ids.add(household_id)
        seen_native.add(native_key)
        seen_receiving.add((source, receiving))

        code = codebook[source.value]
        bodies.append("household_id", household_id.to_bytes(8, "little", signed=True))
        bodies.append(
            "selected_receiving_household_id",
            receiving.to_bytes(8, "little", signed=True),
        )
        bodies.append(
            "source_year", values["source_year"].to_bytes(8, "little", signed=True)
        )
        bodies.append(
            "survey_year", values["survey_year"].to_bytes(8, "little", signed=True)
        )
        bodies.append("source_code", code.to_bytes(1, "little"))
        bodies.append("importance_weight_float64", struct.pack("<d", weight))
        bodies.append("raw_native_id_lengths", len(native).to_bytes(2, "little"))
        bodies.append("raw_native_id_payload", native)
        for field, value in (
            ("original_anchor", values["original_anchor"]),
            ("share", values["share"]),
            ("inclusion_probability", values["inclusion_probability"]),
            ("importance_multiplier", multiplier),
        ):
            for part, number in (
                ("numerator", value.numerator),
                ("denominator", value.denominator),
            ):
                raw = _encode_int(number, "ROW_RATIONAL")
                bodies.append(f"{field}_{part}_lengths", len(raw).to_bytes(2, "little"))
                bodies.append(f"{field}_{part}_payload", raw)

        _fold_identity(
            identity,
            household_id=household_id,
            source=source,
            source_year=values["source_year"],
            survey_year=values["survey_year"],
            native=native,
            receiving=receiving,
        )

    _require(rows > 0, "EMPTY_ALLOCATION")
    frozen = bodies.frozen()
    columns = [
        {
            "name": name,
            "kind": _BODY_KINDS[name],
            "bytes": len(frozen[name]),
            "sha256": _sha(frozen[name]),
        }
        for name in _BODY_NAMES
    ]
    header = {
        "protocol": PROTOCOL,
        "schema_version": SCHEMA_VERSION,
        "type": [ARTIFACT_TYPE_NAME, ARTIFACT_SCHEMA_VERSION],
        "rows": rows,
        "header_length_endianness": "big",
        "body_endianness": "little",
        "columns": columns,
        "source_codebook": codebook,
        "preparation_sha256": preparation_sha256,
        "input_context_sha256": _sha(input_context),
        "output_context_sha256": _sha(output_context),
        "identity_sha256": identity.hexdigest(),
        "weight_transition": list(_WEIGHT_TRANSITION),
        "release_eligible": False,
        "source_authenticated": False,
        "descriptive_only": True,
    }
    try:
        encoded = canonical_json(header)
    except (TypeError, ValueError, RecursionError):
        raise AllocationColumnarError("HEADER_ENCODING") from None
    _require(0 < len(encoded) <= HEADER_MAX_BYTES, "HEADER_LIMIT")
    parts = [
        MAGIC,
        len(encoded).to_bytes(_HEADER_LENGTH_BYTES, "big"),
        encoded,
        *(frozen[name] for name in _BODY_NAMES),
    ]
    total = sum(len(part) for part in parts) + _DIGEST_BYTES
    _require(total <= max_bytes, "ALLOCATION_LIMIT")
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part)
    return b"".join((*parts, digest.digest()))


def _parse_header(payload, *, max_bytes):
    """Validate the header and the envelope seal without interpreting a body.

    Every declared length is bounded against the row count and its own per-row
    maximum before anything is sliced, then the total is checked against the
    payload's actual length, then the trailing checksum is verified. The column
    bodies are hashed by that checksum but never decoded here.
    """

    _require(type(payload) is bytes, "PAYLOAD_TYPE")
    _require(
        len(MAGIC) + _HEADER_LENGTH_BYTES + _DIGEST_BYTES < len(payload) <= max_bytes,
        "PAYLOAD_SIZE",
    )
    _require(payload.startswith(MAGIC), "PAYLOAD_MAGIC")
    start = len(MAGIC)
    length = int.from_bytes(payload[start : start + _HEADER_LENGTH_BYTES], "big")
    start += _HEADER_LENGTH_BYTES
    _require(0 < length <= HEADER_MAX_BYTES, "HEADER_LENGTH")
    _require(len(payload) >= start + length + _DIGEST_BYTES, "HEADER_LENGTH")
    encoded = payload[start : start + length]
    try:
        header = json.loads(encoded.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError):
        raise AllocationColumnarError("HEADER_JSON") from None
    try:
        recanonical = canonical_json(header)
    except (TypeError, ValueError, RecursionError):
        raise AllocationColumnarError("HEADER_JSON") from None
    # Rejects a reordered, re-spaced or duplicate-keyed header spelling of the
    # same document, so one payload has exactly one legal byte form.
    _require(recanonical == encoded, "HEADER_NOT_CANONICAL")
    _require(type(header) is dict and set(header) == _HEADER_KEYS, "HEADER_SCHEMA")
    _require(header["protocol"] == PROTOCOL, "HEADER_PROTOCOL")
    # The type checks are exact, not just equal. ``2.0 == 2`` in Python, so a
    # float spelling would otherwise decode to the same values through a
    # different, equally canonical byte string - two legal forms of one
    # document, and two different payload digests for it.
    version = header["schema_version"]
    _require(type(version) is int and version == SCHEMA_VERSION, "HEADER_VERSION")
    declared = header["type"]
    _require(
        type(declared) is list
        and len(declared) == 2
        and declared[0] == ARTIFACT_TYPE_NAME
        and type(declared[1]) is int
        and declared[1] == ARTIFACT_SCHEMA_VERSION,
        "HEADER_TYPE",
    )
    _require(
        header["header_length_endianness"] == "big"
        and header["body_endianness"] == "little",
        "HEADER_ENDIANNESS",
    )
    _require(
        header["weight_transition"] == list(_WEIGHT_TRANSITION), "HEADER_TRANSITION"
    )
    _require(
        header["release_eligible"] is False
        and header["source_authenticated"] is False
        and header["descriptive_only"] is True,
        "HEADER_AUTHORITY",
    )
    for key in ("preparation_sha256", "input_context_sha256", "output_context_sha256"):
        _digest64(header[key], "HEADER_DIGEST")
    _digest64(header["identity_sha256"], "HEADER_DIGEST")
    rows = header["rows"]
    _require(type(rows) is int and 0 < rows <= MAX_ROWS, "ROW_LIMIT")

    raw_columns = header["columns"]
    _require(
        type(raw_columns) is list and len(raw_columns) == len(_BODY_NAMES),
        "COLUMN_ROSTER",
    )
    sizes, total = {}, 0
    for name, column in zip(_BODY_NAMES, raw_columns, strict=True):
        _require(type(column) is dict and set(column) == _COLUMN_KEYS, "COLUMN_SCHEMA")
        _require(column["name"] == name, "COLUMN_ROSTER")
        kind = _BODY_KINDS[name]
        _require(column["kind"] == kind, "COLUMN_KIND")
        _digest64(column["sha256"], "COLUMN_DIGEST")
        size = column["bytes"]
        _require(type(size) is int and size >= 0, "COLUMN_SIZE")
        width = _FIXED_WIDTH.get(kind)
        if width is not None:
            _require(size == rows * width, "COLUMN_SIZE")
        else:
            # A declared variable body is bounded before anything is sliced out
            # of it, so an inflated length is refused without allocating for it.
            _require(size <= rows * _VARIABLE_ROW_MAX[kind], "COLUMN_SIZE")
        total += size
        sizes[name] = size
    body_start = start + length
    _require(
        len(payload) == body_start + total + _DIGEST_BYTES,
        "PAYLOAD_LENGTH",
    )
    # The envelope checksum is verified here rather than in the caller, so every
    # entry point gets it. A manifest that republished this payload's
    # provenance digests without checking the seal would describe bytes a
    # decoder refuses, over bodies an attacker had rewritten.
    _require(
        hashlib.sha256(memoryview(payload)[:-_DIGEST_BYTES]).digest()
        == payload[-_DIGEST_BYTES:],
        "PAYLOAD_CHECKSUM",
    )
    return header, sizes, body_start


def _fixed_values(body, count, width, signed, code):
    _require(len(body) == count * width, code)
    return tuple(
        int.from_bytes(body[i * width : (i + 1) * width], "little", signed=signed)
        for i in range(count)
    )


def _variable_values(lengths, body, decode, code):
    values, cursor = [], 0
    for size in lengths:
        _require(cursor + size <= len(body), code)
        values.append(decode(body[cursor : cursor + size]))
        cursor += size
    _require(cursor == len(body), code)
    return tuple(values)


def decode_allocation(payload, *, max_bytes=MAX_BYTES):
    """Decode a v2 payload into columns, re-proving everything it claims.

    Every bound is checked against the header before a body is sliced, the
    trailing checksum covers the whole envelope, each column body is checked
    against its own digest, and the redundant fields — the importance
    multiplier, the float weight and the ordering digest — are recomputed from
    the values actually read rather than believed.

    The result describes bytes. It is not a source certificate, and it does not
    become one by being consistent.
    """

    _require(type(max_bytes) is int and 0 < max_bytes <= MAX_BYTES, "TRANSPORT_LIMIT")
    header, sizes, body_start = _parse_header(payload, max_bytes=max_bytes)
    members = _checked_codebook(header["source_codebook"])
    rows = header["rows"]

    # BODY_TRUNCATED and PAYLOAD_TRAILING are invariant assertions, not reachable
    # failure modes: _parse_header already proved that the declared sizes sum to
    # exactly the bytes present, so every slice below is full and the cursor
    # lands exactly on the checksum. They are kept so that a later change
    # loosening the header parse fails here instead of reading past a body.
    bodies, cursor = {}, body_start
    for name, column in zip(_BODY_NAMES, header["columns"], strict=True):
        size = sizes[name]
        body = payload[cursor : cursor + size]
        _require(len(body) == size, "BODY_TRUNCATED")
        _require(_sha(body) == column["sha256"], "BODY_DIGEST")
        bodies[name] = body
        cursor += size
    _require(cursor + _DIGEST_BYTES == len(payload), "PAYLOAD_TRAILING")

    household_id = _fixed_values(bodies["household_id"], rows, 8, True, "COLUMN_SIZE")
    receiving = _fixed_values(
        bodies["selected_receiving_household_id"], rows, 8, True, "COLUMN_SIZE"
    )
    source_year = _fixed_values(bodies["source_year"], rows, 8, True, "COLUMN_SIZE")
    survey_year = _fixed_values(bodies["survey_year"], rows, 8, True, "COLUMN_SIZE")
    codes = _fixed_values(bodies["source_code"], rows, 1, False, "COLUMN_SIZE")
    _require(all(code in members for code in codes), "SOURCE_CODE")
    sources = tuple(members[code] for code in codes)
    _require(all(value >= 0 for value in household_id), "ROW_INTEGER")
    _require(all(value >= 0 for value in receiving), "ROW_INTEGER")

    weight_body = bodies["importance_weight_float64"]
    _require(len(weight_body) == rows * 8, "COLUMN_SIZE")
    # Bit 63 of a little-endian double lives in its last byte. Refusing it here
    # rejects every negative value and negative zero before any float maths.
    _require(
        all(weight_body[i * 8 + 7] & 0x80 == 0 for i in range(rows)), "FLOAT_WEIGHT"
    )
    weights = struct.unpack(f"<{rows}d", weight_body)
    _require(all(math.isfinite(value) for value in weights), "FLOAT_WEIGHT")

    native_lengths = _fixed_values(
        bodies["raw_native_id_lengths"], rows, 2, False, "COLUMN_SIZE"
    )
    _require(
        all(0 < size <= MAX_NATIVE_ID_BYTES for size in native_lengths), "ROW_LEXEME"
    )

    def _lexeme(raw):
        try:
            value = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise AllocationColumnarError("ROW_LEXEME") from None
        _require(0 < len(value) <= MAX_NATIVE_ID_CHARS, "ROW_LEXEME")
        return value

    natives = _variable_values(
        native_lengths, bodies["raw_native_id_payload"], _lexeme, "ROW_LEXEME"
    )

    rationals = {}
    for field in RATIONAL_FIELDS:
        parts = {}
        for part in ("numerator", "denominator"):
            lengths = _fixed_values(
                bodies[f"{field}_{part}_lengths"], rows, 2, False, "COLUMN_SIZE"
            )
            _require(
                all(0 < size <= MAX_RATIONAL_BYTES for size in lengths), "ROW_RATIONAL"
            )
            parts[part] = _variable_values(
                lengths,
                bodies[f"{field}_{part}_payload"],
                lambda raw: _decode_int(raw, "ROW_RATIONAL"),
                "ROW_RATIONAL",
            )
        values = []
        for numerator, denominator in zip(
            parts["numerator"], parts["denominator"], strict=True
        ):
            _require(denominator > 0, "ROW_RATIONAL")
            _require(math.gcd(abs(numerator), denominator) == 1, "ROW_RATIONAL")
            value = Fraction(numerator, denominator)
            # Fraction renormalises; an already-reduced pair must survive it
            # unchanged, so this also refuses a legal-looking unreduced pair.
            _require(
                (value.numerator, value.denominator) == (numerator, denominator),
                "ROW_RATIONAL",
            )
            values.append(value)
        rationals[field] = tuple(values)

    identity = hashlib.sha256(_IDENTITY_DOMAIN)
    seen_ids, seen_native, seen_receiving = set(), set(), set()
    for index in range(rows):
        anchor = rationals["original_anchor"][index]
        share = rationals["share"][index]
        probability = rationals["inclusion_probability"][index]
        multiplier = rationals["importance_multiplier"][index]
        _require(probability != 0, "ROW_RATIONAL")
        _require(share / probability == multiplier, "REDUNDANT_MULTIPLIER")
        _require(
            struct.pack("<d", _checked_weight(anchor * multiplier, "FLOAT_WEIGHT"))
            == weight_body[index * 8 : index * 8 + 8],
            "REDUNDANT_WEIGHT",
        )
        _checked_weight(anchor, "FLOAT_WEIGHT")

        native_key = (
            sources[index],
            source_year[index],
            survey_year[index],
            natives[index],
        )
        _require(
            household_id[index] not in seen_ids
            and native_key not in seen_native
            and (sources[index], receiving[index]) not in seen_receiving,
            "ROW_DUPLICATE",
        )
        seen_ids.add(household_id[index])
        seen_native.add(native_key)
        seen_receiving.add((sources[index], receiving[index]))

        _fold_identity(
            identity,
            household_id=household_id[index],
            source=sources[index],
            source_year=source_year[index],
            survey_year=survey_year[index],
            native=natives[index].encode("utf-8"),
            receiving=receiving[index],
        )

    # Binds the identity columns and their order - household id, resolved
    # channel, both years, native lexeme and receiving id - to what the producer
    # sealed. It deliberately does not cover the arithmetic columns: those are
    # bound by their own per-column digests and by the envelope checksum. A
    # consumer that independently knows the expected digest detects a reordered
    # or relabelled identity; on its own this is a consistency check, not proof
    # against a writer who can rebuild the whole envelope.
    _require(identity.hexdigest() == header["identity_sha256"], "IDENTITY_DIGEST")

    return DecodedAllocation(
        header=MappingProxyType(dict(header)),
        household_id=household_id,
        selected_receiving_household_id=receiving,
        source=sources,
        source_year=source_year,
        survey_year=survey_year,
        raw_native_id=natives,
        original_anchor=rationals["original_anchor"],
        share=rationals["share"],
        inclusion_probability=rationals["inclusion_probability"],
        importance_multiplier=rationals["importance_multiplier"],
        importance_weight=weights,
    )


def allocation_manifest(payload, *, max_bytes=MAX_BYTES):
    """Describe a payload's shape and provenance digests, with no row values.

    Deliberately absent: household and receiving identifiers, native source
    lexemes, exact rationals, float weights, the ordering digest, the per-column
    digests, and the digest of the payload itself. Each of the last three is a
    digest over row values, and a digest over low-entropy row data is a
    confirmation oracle for it: the encoder is deterministic, so a holder of
    this manifest who knew all but one native lexeme could re-encode each
    candidate and compare. The source codebook is withheld for a different and
    weaker reason — it is enum-derived schema, identical in every payload, and
    a public manifest simply has no use for it. What remains is shape, protocol
    identity and the three digests the v1 metadata already reports.

    One residual disclosure is stated rather than hidden: the per-column byte
    lengths are the manifest's purpose, and they narrow row values. The native
    lexeme payload's length is the total UTF-8 length of the cohort's
    identifiers, and a rational column's length bounds the magnitude of its
    integers. For a single-row payload those are tight. A caller publishing a
    manifest for a very small cohort should treat that as disclosure.

    The envelope seal is verified before anything is reported, so this never
    describes bytes a decoder would refuse. Being a manifest of a consistent
    payload still confers no source authority; the returned mapping says so in
    its own fields.
    """

    _require(type(max_bytes) is int and 0 < max_bytes <= MAX_BYTES, "TRANSPORT_LIMIT")
    header, sizes, body_start = _parse_header(payload, max_bytes=max_bytes)
    manifest = {
        "protocol": header["protocol"],
        "schema_version": header["schema_version"],
        "type": list(header["type"]),
        "rows": header["rows"],
        "columns": [
            {"name": name, "kind": _BODY_KINDS[name], "bytes": sizes[name]}
            for name in _BODY_NAMES
        ],
        "header_bytes": body_start - len(MAGIC) - _HEADER_LENGTH_BYTES,
        "body_bytes": sum(sizes.values()),
        "total_bytes": len(payload),
        "preparation_sha256": header["preparation_sha256"],
        "input_context_sha256": header["input_context_sha256"],
        "output_context_sha256": header["output_context_sha256"],
        "weight_transition": list(header["weight_transition"]),
        "release_eligible": False,
        "source_authenticated": False,
        "descriptive_only": True,
    }
    # A real check on what is actually returned, not an ``assert`` that a ``-O``
    # run would strip: a later edit that copies a private header field into the
    # manifest is refused here rather than shipped.
    _require(
        not set(manifest) & _PRIVATE_HEADER_KEYS
        and all(set(column) == _MANIFEST_COLUMN_KEYS for column in manifest["columns"]),
        "MANIFEST_PRIVACY",
    )
    return manifest
