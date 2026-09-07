"""The 2015 PUF statistical reference period, as a documentary interpretation.

The 2015 IRS SOI Public Use File delivers mixed reported accounting periods.
That alone does not leave its statistical reference period unknown: the
publisher states that the records "are intended to represent all returns filed
for Tax Year 2015", and that returns for prior years "were used in place of
2015 returns received and processed after December 31, 2016". This module
carries that reading — tax year 2015 as the statistical reference period, each
reported ``FLPDYR``/``FLPDMO`` preserved verbatim, calendar 2016 as the
processing window, national-only meaning — as a versioned, portable resource
with an explicit validator.

**This module grants no growth authority.** Revision 1 of the schema accepts
only a *proposed* convention with a null review, and
:func:`growth_admission` refuses growth unconditionally for every input,
including a value labelled ``reviewed_modeling_convention`` and including
well-formed self-supplied hashes and review fields. A future positive-admission
path would need a separately reviewed schema revision that canonically defines
a review fingerprint, an external caller trust channel and an exact
comparison-evidence binding; none of that is defined or implemented here.

Three properties are structural rather than documentary, so they cannot be
asserted away by an edited resource:

* ``GrowthAdmission.admitted`` is a read-only property returning ``False``.
* ``DocumentaryVerification`` is issued only by :func:`verify_documentary_pins`,
  from re-authenticated bytes, and authenticates only the exact interpretation
  object it was issued for together with the complete pin roster it covered.
  The resource may not carry a serialized verified flag at all, and a caller
  cannot assemble a verdict.
* The interpretation binds the frozen raw source definition by identity and
  hash only. It never imports it, never rewrites it, and never touches its
  ``period_semantics`` value of ``unresolved_raw_FLPDYR``.

What that does **not** claim: a caller who fabricates a
:class:`StatisticalPeriodInterpretation` outside :func:`load_interpretation`,
or edits one with ``dataclasses.replace``, and then verifies *that* against
bytes it resolves itself, is describing its own fabrication. No verdict is
reused and nothing is forged — the display simply reports the view it was
handed. The guarantees above are about verdicts, not about the provenance of a
view a caller built; use :func:`load_interpretation` for that.

The module is deliberately stdlib-only and lives outside
``microcosm.build.us_runtime``, whose package initialization eagerly imports
the whole US stage graph. Documentary interpretation must be loadable without
starting a build. Callers resolve document bytes themselves: the resource holds
logical document IDs and hashes, never filesystem paths.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from importlib.resources import files
from types import MappingProxyType
from typing import Any, Final, NoReturn

__all__ = [
    "ACCEPTED_CONVENTION_REVIEW",
    "ACCEPTED_CONVENTION_STATUS",
    "AuthorityRefusedError",
    "ConventionProposal",
    "DOCUMENT_HASH_METHOD_ID",
    "DocumentPin",
    "DocumentaryVerification",
    "GROWTH_REFUSED_UNCONDITIONALLY",
    "GrowthAdmission",
    "GrowthRefusedError",
    "InterpretationError",
    "InterpretationRefusalError",
    "NO_POSITIVE_ADMISSION_PATH",
    "PAGE_SEPARATOR",
    "PAGE_TEXT_HASH_METHOD_ID",
    "PRESERVED_PERIOD_FIELDS",
    "PROCESSING_CALENDAR_YEAR",
    "PageLocator",
    "PageTextHashError",
    "PinCheck",
    "RAW_PERIOD_SEMANTICS",
    "REFUSED_AUTHORITIES",
    "RESOURCE_SCHEMA_ID",
    "RESOURCE_SCHEMA_VERSION",
    "RawSourceBinding",
    "RenderPin",
    "ReportedPeriodAnnotation",
    "Resolver",
    "ResourceValidationError",
    "RetainedText",
    "STATISTICAL_REFERENCE_TAX_YEAR",
    "StatisticalPeriodInterpretation",
    "VerificationIssuanceError",
    "annotate_reported_period",
    "canonical_resource_sha256",
    "classify_convention_status",
    "documentary_display",
    "documentary_pin_roster",
    "grants_authority",
    "graph_annotations",
    "growth_admission",
    "load_interpretation",
    "load_packaged_interpretation",
    "package_resource_bytes",
    "package_schema",
    "page_text_sha256",
    "refuse_growth",
    "require_authority",
    "verify_documentary_pins",
]

# --------------------------------------------------------------------------
# Declared identities and constants
# --------------------------------------------------------------------------

RESOURCE_SCHEMA_ID: Final = "microcosm.us.puf_2015_statistical_period_interpretation"
RESOURCE_SCHEMA_VERSION: Final = 1

_RESOURCE_PACKAGE: Final = "microcosm.build"
_RESOURCE_DIRECTORY: Final = "us_source_interpretation"
_RESOURCE_FILENAME: Final = "puf_2015_statistical_period_interpretation.json"
_SCHEMA_FILENAME: Final = "puf_2015_statistical_period_interpretation.schema.json"

#: The publisher's statistical reference period for the delivered file.
STATISTICAL_REFERENCE_TAX_YEAR: Final = 2015
#: The calendar year whose processed returns were sampled.
PROCESSING_CALENDAR_YEAR: Final = 2016
#: Reported accounting-period fields that are preserved exactly as delivered.
PRESERVED_PERIOD_FIELDS: Final = ("FLPDYR", "FLPDMO")
#: The delivered raw period semantics recorded by the frozen predecessor.
RAW_PERIOD_SEMANTICS: Final = "unresolved_raw_FLPDYR"

#: The only convention status revision 1 accepts.
ACCEPTED_CONVENTION_STATUS: Final = "proposed"
#: The only convention review value revision 1 accepts.
ACCEPTED_CONVENTION_REVIEW: Final = None

PAGE_TEXT_HASH_METHOD_ID: Final = "retained_utf8_formfeed_pdf_page_sha256.v1"
DOCUMENT_HASH_METHOD_ID: Final = "exact_file_bytes_sha256.v1"
#: Literal U+000C. Retained booklet text joins pages with this separator.
PAGE_SEPARATOR: Final = "\f"

#: Every top-level key revision 1 knows about. An unreviewed field cannot ride
#: along in a versioned contract, so anything else is refused.
_ALLOWED_TOP_LEVEL: Final = frozenset(
    {
        "schema",
        "schema_version",
        "interpretation_id",
        "authority",
        "grants",
        "scope",
        "alternatives_considered",
        "raw_source_binding",
        "statistical_reference_period",
        "reported_period_preservation",
        "processing_window",
        "publisher_disclosure_avoidance",
        "geographic_meaning",
        "distinct_items",
        "convention",
        "growth_contract",
        "future_positive_admission",
        "documentary_pins",
        "documents",
        "renders",
        "page_text_hash_method",
        "document_and_render_hash_method",
        "canonical_resource_hash_method",
        "extraction_provenance",
        "disagreement_record",
        "page40_weighted_tabulation",
        "deferred_required_work",
        "unchanged_historical_records",
        "public_references",
        "non_claims",
    }
)

#: Keys that would serialize a verification verdict. The verdict is computed.
_FORBIDDEN_VERIFIED_KEYS: Final = frozenset(
    {"documentary_pins_verified", "pins_verified"}
)

#: The publisher disclosure-avoidance treatments the adjudication enumerates.
#: Blurring is listed explicitly: a later audit must state its treatment rather
#: than assume it away.
_REQUIRED_DISCLOSURE_TREATMENTS: Final = frozenset(
    {
        "fiscal_period_conversion",
        "extreme_value_aggregation",
        "multivariate_blurring",
    }
)

#: Keys the convention block may carry. An unreviewed extra field -- a
#: "review_record" riding along, say -- cannot enter through a versioned
#: contract that only accepts a proposal.
_ALLOWED_CONVENTION_KEYS: Final = frozenset(
    {
        "convention_id",
        "convention_status",
        "convention_review",
        "growth_admitted",
        "label",
        "basis",
        "description",
        "treats",
        "does_not_claim",
        "compounding_with_row_specific_price_conversion",
        "review_required_before_any_use",
    }
)

#: Convention statuses that assert a review this revision cannot honour.
_REVIEW_CLAIMING_TOKENS: Final = ("review", "approv", "accept", "admit", "sign")

_SHA256_LENGTH: Final = 64
_HEX_DIGITS: Final = frozenset("0123456789abcdef")


# --------------------------------------------------------------------------
# Errors and refusals
# --------------------------------------------------------------------------


class InterpretationError(ValueError):
    """A resource or a declared method could not be honoured as written."""


class ResourceValidationError(InterpretationError):
    """The interpretation resource violates revision 1 of the schema."""

    def __init__(self, reason: str, location: str, detail: str = "") -> None:
        message = f"{location}: {reason}"
        if detail:
            message = f"{message} ({detail})"
        super().__init__(message)
        self.reason = reason
        self.location = location
        self.detail = detail


class PageTextHashError(InterpretationError):
    """The declared page-text hash method refused the inputs it was given."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


class InterpretationRefusalError(RuntimeError):
    """A caller asked this documentary artifact for authority it does not hold."""


class GrowthRefusedError(InterpretationRefusalError):
    """Growth was requested. Revision 1 refuses growth unconditionally."""

    def __init__(self, admission: GrowthAdmission) -> None:
        super().__init__(
            "growth refused by "
            f"{RESOURCE_SCHEMA_ID} v{RESOURCE_SCHEMA_VERSION}: "
            + ", ".join(admission.reasons)
        )
        self.admission = admission


class VerificationIssuanceError(InterpretationRefusalError):
    """A documentary verdict was assembled outside the verifier.

    :class:`DocumentaryVerification` is what :func:`verify_documentary_pins`
    returns, never something a caller builds: a verdict that nobody issued has
    re-authenticated nothing, whatever its checks say.
    """

    def __init__(self) -> None:
        super().__init__(
            "DocumentaryVerification is issued by verify_documentary_pins from "
            "resolved bytes; a directly constructed verdict authenticates nothing"
        )


class AuthorityRefusedError(InterpretationRefusalError):
    """A non-documentary authority was requested of a documentary artifact."""

    def __init__(self, use: str) -> None:
        super().__init__(
            f"{RESOURCE_SCHEMA_ID} is a documentary interpretation and grants "
            f"no {use} authority"
        )
        self.use = use


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def _is_int(value: object) -> bool:
    """True for a genuine integer. ``bool`` is a subclass and is excluded."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _SHA256_LENGTH
        and set(value) <= _HEX_DIGITS
    )


def _freeze(value: Any) -> Any:
    """Deep-freeze a decoded JSON value so a loaded resource cannot be edited."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value: Any) -> Any:
    """Inverse of :func:`_freeze`, for canonical serialization."""
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def canonical_resource_sha256(payload: Mapping[str, Any]) -> str:
    """Canonical identity of an interpretation payload.

    Sorted keys, tight separators, ASCII-escaped, NaN refused — the same
    canonicalization the frozen raw source definition declares for its header
    hash, so the two artifacts are identified the same way.
    """
    encoded = json.dumps(
        _plain(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


# --------------------------------------------------------------------------
# The declared page-text hash method
# --------------------------------------------------------------------------


def page_text_sha256(
    container_bytes: bytes,
    *,
    expected_container_sha256: str,
    pdf_page: int,
    expected_segment_count: int,
) -> str:
    """Hash one PDF page of a retained booklet text, exactly as declared.

    ``retained_utf8_formfeed_pdf_page_sha256.v1``: authenticate the retained
    text file against its full-container SHA-256, decode strict UTF-8, split on
    the literal U+000C formfeed, require exactly the declared segment count,
    require a non-boolean integer locator in ``1 <= pdf_page <= segment_count``,
    select that one-based segment, refuse an empty selected segment, retain
    every header, footer, space and newline unchanged, encode UTF-8 and hash
    those segment bytes excluding the formfeed separators.

    Nothing is trimmed, normalized or appended, and no PDF is freshly
    extracted: this method reads the retained bytes the caller supplies and
    nothing else.

    Raises:
        PageTextHashError: with a stable ``reason`` for every refusal.
    """
    if not _is_int(expected_segment_count):
        raise PageTextHashError(
            "declared_segment_count_not_integer", repr(expected_segment_count)
        )
    if expected_segment_count < 1:
        raise PageTextHashError(
            "declared_segment_count_not_positive", repr(expected_segment_count)
        )
    if isinstance(pdf_page, bool):
        raise PageTextHashError("locator_is_boolean", repr(pdf_page))
    if not _is_int(pdf_page):
        raise PageTextHashError("locator_not_integer", repr(pdf_page))
    if not _is_sha256(expected_container_sha256):
        raise PageTextHashError(
            "declared_container_hash_malformed", repr(expected_container_sha256)
        )
    if not isinstance(container_bytes, (bytes, bytearray)):
        raise PageTextHashError("container_not_bytes", type(container_bytes).__name__)

    actual = hashlib.sha256(bytes(container_bytes)).hexdigest()
    if actual != expected_container_sha256:
        raise PageTextHashError(
            "container_hash_mismatch",
            f"declared {expected_container_sha256}, actual {actual}",
        )

    try:
        text = bytes(container_bytes).decode("utf-8")
    except UnicodeDecodeError as error:  # pragma: no cover - defensive
        raise PageTextHashError("container_not_strict_utf8", str(error)) from None

    segments = text.split(PAGE_SEPARATOR)
    if len(segments) != expected_segment_count:
        raise PageTextHashError(
            "segment_count_mismatch",
            f"declared {expected_segment_count}, actual {len(segments)}",
        )
    if not 1 <= pdf_page <= expected_segment_count:
        raise PageTextHashError(
            "locator_out_of_range",
            f"pdf_page {pdf_page} outside 1..{expected_segment_count}",
        )

    segment = segments[pdf_page - 1]
    if segment == "":
        raise PageTextHashError("empty_page_segment", f"pdf_page {pdf_page}")

    return hashlib.sha256(segment.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Typed view of a validated resource
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PageLocator:
    """One pinned page of a retained booklet text."""

    pdf_page: int
    printed_page: int
    text_sha256: str
    role: str
    cross_edition_text_identical: bool


@dataclass(frozen=True, slots=True)
class RetainedText:
    """The retained full-text container for one booklet edition."""

    text_id: str
    sha256: str
    bytes_: int
    segment_count: int


@dataclass(frozen=True, slots=True)
class DocumentPin:
    """A primary public IRS document and its retained text."""

    document_id: str
    edition: str
    role: str
    pdf_sha256: str
    pdf_bytes: int
    retained_text: RetainedText
    pages: tuple[PageLocator, ...]

    def page(self, pdf_page: int) -> PageLocator:
        for locator in self.pages:
            if locator.pdf_page == pdf_page:
                return locator
        raise KeyError(f"{self.document_id}: no pinned pdf_page {pdf_page}")


@dataclass(frozen=True, slots=True)
class RenderPin:
    """A retained page render. A byte pin, never a pixel hash."""

    render_id: str
    document_id: str
    pdf_page: int
    sha256: str
    bytes_: int
    visually_inspected: bool


@dataclass(frozen=True, slots=True)
class RawSourceBinding:
    """Identity-and-hash binding to the frozen raw source definition."""

    definition_schema: str
    definition_schema_version: int
    definition_sha256: str
    definition_bytes: int
    preserved_period_semantics: str

    @property
    def imports_predecessor_module(self) -> bool:
        """Always ``False``. The binding is by identity, never by import."""
        return False

    @property
    def retroactive_mutation(self) -> bool:
        """Always ``False``. The predecessor and older receipts stand as written."""
        return False


@dataclass(frozen=True, slots=True)
class ConventionProposal:
    """The proposed modeling convention. A proposal is not an approval."""

    convention_id: str
    convention_status: str
    convention_review: None
    description: str

    @property
    def growth_admitted(self) -> bool:
        """Always ``False`` in revision 1."""
        return False


@dataclass(frozen=True, slots=True)
class StatisticalPeriodInterpretation:
    """A validated interpretation resource."""

    interpretation_id: str
    schema_version: int
    statistical_reference_tax_year: int
    processing_calendar_year: int
    preserved_period_fields: tuple[str, ...]
    delivered_flpdyr_domain: tuple[int, ...]
    delivered_flpdmo_domain: tuple[int, ...]
    national_only: bool
    convention: ConventionProposal
    raw_source_binding: RawSourceBinding
    documents: tuple[DocumentPin, ...]
    renders: tuple[RenderPin, ...]
    payload: Mapping[str, Any]

    @property
    def schema(self) -> str:
        return RESOURCE_SCHEMA_ID

    @property
    def resource_sha256(self) -> str:
        """Canonical identity of this resource, recomputed from the payload.

        Derived rather than stored, so it cannot be carried over unchanged onto
        an edited copy of this view. :func:`load_interpretation` proves the
        payload is canonically encodable before returning, so this cannot raise
        for a loaded view.
        """
        return canonical_resource_sha256(self.payload)

    @property
    def documentary_pins_status(self) -> str:
        """Always ``"declared"``. Verification is computed, never serialized."""
        return "declared"

    def document(self, document_id: str) -> DocumentPin:
        for pin in self.documents:
            if pin.document_id == document_id:
                return pin
        raise KeyError(f"no pinned document {document_id!r}")

    @property
    def page40(self) -> Mapping[str, Any]:
        return self.payload["page40_weighted_tabulation"]


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def _require(condition: bool, reason: str, location: str, detail: str = "") -> None:
    if not condition:
        raise ResourceValidationError(reason, location, detail)


def _mapping(payload: Mapping[str, Any], key: str, location: str) -> Mapping[str, Any]:
    value = payload.get(key)
    _require(isinstance(value, Mapping), "object_required", f"{location}/{key}")
    return value  # type: ignore[return-value]


def _reject_serialized_verification(payload: Any, location: str = "") -> None:
    """Refuse any resource that serializes a verification verdict.

    The verdict must be recomputed from bytes on every load, so a resource is
    not allowed to carry one at all — a forged ``true`` never reaches a caller
    because the key cannot survive validation.
    """
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            here = f"{location}/{key}" if location else key
            if key in _FORBIDDEN_VERIFIED_KEYS:
                raise ResourceValidationError(
                    "serialized_verification_flag", here, repr(value)
                )
            if key == "verified" and location.endswith("documentary_pins"):
                raise ResourceValidationError(
                    "serialized_verification_flag", here, repr(value)
                )
            _reject_serialized_verification(value, here)
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            _reject_serialized_verification(value, f"{location}/{index}")


def _validate_convention(payload: Mapping[str, Any]) -> ConventionProposal:
    convention = _mapping(payload, "convention", "")
    unknown = sorted(set(convention) - _ALLOWED_CONVENTION_KEYS)
    _require(not unknown, "unknown_convention_key", "convention", ", ".join(unknown))
    _require(
        "convention_status" in convention,
        "convention_status_missing",
        "convention/convention_status",
    )
    status = convention["convention_status"]
    _require(
        status == ACCEPTED_CONVENTION_STATUS,
        f"convention_status_{classify_convention_status(status)}",
        "convention/convention_status",
        repr(status),
    )
    _require(
        "convention_review" in convention,
        "convention_review_missing",
        "convention/convention_review",
    )
    _require(
        convention["convention_review"] is ACCEPTED_CONVENTION_REVIEW,
        "convention_review_claimed",
        "convention/convention_review",
        repr(convention["convention_review"]),
    )
    _require(
        convention.get("growth_admitted") is False,
        "growth_admitted_must_be_false",
        "convention/growth_admitted",
        repr(convention.get("growth_admitted")),
    )
    convention_id = convention.get("convention_id")
    _require(
        isinstance(convention_id, str) and convention_id.strip() != "",
        "convention_id_ambiguous",
        "convention/convention_id",
        repr(convention_id),
    )
    _require(
        convention.get("label") == "proposed_modeling_convention",
        "convention_label_must_mark_a_proposal",
        "convention/label",
        repr(convention.get("label")),
    )
    _require(
        convention.get("basis") == "modeling_choice_not_publisher_documented",
        "convention_basis_must_not_claim_publisher_documentation",
        "convention/basis",
        repr(convention.get("basis")),
    )
    description = convention.get("description")
    _require(
        isinstance(description, str) and description.strip() != "",
        "convention_description_required",
        "convention/description",
    )
    return ConventionProposal(
        convention_id=convention_id,
        convention_status=ACCEPTED_CONVENTION_STATUS,
        convention_review=None,
        description=description,
    )


def _validate_documents(
    payload: Mapping[str, Any],
) -> tuple[DocumentPin, ...]:
    rows = payload.get("documents")
    _require(
        isinstance(rows, (list, tuple)) and len(rows) >= 1,
        "documents_required",
        "documents",
    )
    pins: list[DocumentPin] = []
    seen_documents: set[str] = set()
    seen_texts: set[str] = set()
    for index, row in enumerate(rows):
        at = f"documents/{index}"
        _require(isinstance(row, Mapping), "object_required", at)
        document_id = row.get("document_id")
        _require(
            isinstance(document_id, str) and document_id.strip() != "",
            "document_id_required",
            f"{at}/document_id",
        )
        _require(
            document_id not in seen_documents,
            "duplicate_document_id",
            f"{at}/document_id",
        )
        seen_documents.add(document_id)
        _require(
            row.get("role") == "primary_public_irs_document",
            "document_role_must_be_primary_public",
            f"{at}/role",
            repr(row.get("role")),
        )

        pdf = _mapping(row, "pdf", at)
        _require(
            _is_sha256(pdf.get("sha256")), "pdf_sha256_malformed", f"{at}/pdf/sha256"
        )
        _require(
            _is_int(pdf.get("bytes")) and pdf["bytes"] > 0,
            "pdf_bytes_invalid",
            f"{at}/pdf/bytes",
        )

        text = _mapping(row, "retained_text", at)
        text_id = text.get("text_id")
        _require(
            isinstance(text_id, str) and text_id.strip() != "",
            "text_id_required",
            f"{at}/retained_text/text_id",
        )
        _require(
            text_id not in seen_texts,
            "duplicate_text_id",
            f"{at}/retained_text/text_id",
        )
        seen_texts.add(text_id)
        _require(
            _is_sha256(text.get("sha256")),
            "text_sha256_malformed",
            f"{at}/retained_text/sha256",
        )
        segment_count = text.get("segment_count")
        _require(
            _is_int(segment_count) and segment_count > 0,
            "segment_count_invalid",
            f"{at}/retained_text/segment_count",
            repr(segment_count),
        )
        _require(
            _is_int(text.get("bytes")) and text["bytes"] > 0,
            "text_bytes_invalid",
            f"{at}/retained_text/bytes",
        )

        page_rows = row.get("pages")
        _require(
            isinstance(page_rows, (list, tuple)) and len(page_rows) >= 1,
            "pages_required",
            f"{at}/pages",
        )
        locators: list[PageLocator] = []
        seen_pages: set[int] = set()
        for page_index, page_row in enumerate(page_rows):
            page_at = f"{at}/pages/{page_index}"
            _require(isinstance(page_row, Mapping), "object_required", page_at)
            pdf_page = page_row.get("pdf_page")
            _require(
                not isinstance(pdf_page, bool),
                "locator_is_boolean",
                f"{page_at}/pdf_page",
            )
            _require(_is_int(pdf_page), "locator_not_integer", f"{page_at}/pdf_page")
            _require(
                1 <= pdf_page <= segment_count,
                "locator_out_of_range",
                f"{page_at}/pdf_page",
                f"{pdf_page} outside 1..{segment_count}",
            )
            _require(
                pdf_page not in seen_pages, "duplicate_pdf_page", f"{page_at}/pdf_page"
            )
            seen_pages.add(pdf_page)
            printed_page = page_row.get("printed_page")
            _require(
                _is_int(printed_page) and printed_page >= 1,
                "printed_page_invalid",
                f"{page_at}/printed_page",
            )
            _require(
                _is_sha256(page_row.get("text_sha256")),
                "page_text_sha256_malformed",
                f"{page_at}/text_sha256",
            )
            role = page_row.get("role")
            _require(
                isinstance(role, str) and role.strip() != "",
                "page_role_required",
                f"{page_at}/role",
            )
            identical = page_row.get("cross_edition_text_identical")
            _require(
                isinstance(identical, bool),
                "cross_edition_flag_invalid",
                f"{page_at}/cross_edition_text_identical",
            )
            locators.append(
                PageLocator(
                    pdf_page=pdf_page,
                    printed_page=printed_page,
                    text_sha256=page_row["text_sha256"],
                    role=role,
                    cross_edition_text_identical=identical,
                )
            )

        edition = row.get("edition")
        _require(
            isinstance(edition, str) and edition.strip() != "",
            "edition_required",
            f"{at}/edition",
        )
        pins.append(
            DocumentPin(
                document_id=document_id,
                edition=edition,
                role="primary_public_irs_document",
                pdf_sha256=pdf["sha256"],
                pdf_bytes=pdf["bytes"],
                retained_text=RetainedText(
                    text_id=text_id,
                    sha256=text["sha256"],
                    bytes_=text["bytes"],
                    segment_count=segment_count,
                ),
                pages=tuple(locators),
            )
        )
    return tuple(pins)


def _validate_renders(
    payload: Mapping[str, Any], documents: tuple[DocumentPin, ...]
) -> tuple[RenderPin, ...]:
    rows = payload.get("renders", ())
    _require(isinstance(rows, (list, tuple)), "renders_must_be_a_list", "renders")
    by_id = {pin.document_id: pin for pin in documents}
    pins: list[RenderPin] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        at = f"renders/{index}"
        _require(isinstance(row, Mapping), "object_required", at)
        render_id = row.get("render_id")
        _require(
            isinstance(render_id, str) and render_id.strip() != "",
            "render_id_required",
            f"{at}/render_id",
        )
        _require(render_id not in seen, "duplicate_render_id", f"{at}/render_id")
        seen.add(render_id)
        document_id = row.get("document_id")
        _require(
            document_id in by_id,
            "render_document_unknown",
            f"{at}/document_id",
            repr(document_id),
        )
        pdf_page = row.get("pdf_page")
        _require(not isinstance(pdf_page, bool), "locator_is_boolean", f"{at}/pdf_page")
        _require(_is_int(pdf_page), "locator_not_integer", f"{at}/pdf_page")
        _require(
            1 <= pdf_page <= by_id[document_id].retained_text.segment_count,
            "locator_out_of_range",
            f"{at}/pdf_page",
            repr(pdf_page),
        )
        _require(
            _is_sha256(row.get("sha256")), "render_sha256_malformed", f"{at}/sha256"
        )
        _require(
            _is_int(row.get("bytes")) and row["bytes"] > 0,
            "render_bytes_invalid",
            f"{at}/bytes",
        )
        _require(
            isinstance(row.get("visually_inspected"), bool),
            "visually_inspected_invalid",
            f"{at}/visually_inspected",
        )
        pins.append(
            RenderPin(
                render_id=render_id,
                document_id=document_id,
                pdf_page=pdf_page,
                sha256=row["sha256"],
                bytes_=row["bytes"],
                visually_inspected=row["visually_inspected"],
            )
        )
    return tuple(pins)


def _validate_page40(payload: Mapping[str, Any]) -> None:
    """Check the published page-40 integers reconcile exactly as recorded.

    Exact integer arithmetic only, on the publisher's displayed counts. This is
    documentary reconciliation of the printed table, not a calibration
    objective and not a weighted audit: no microdata is involved.
    """
    table = _mapping(payload, "page40_weighted_tabulation", "")
    at = "page40_weighted_tabulation"
    _require(
        table.get("column") == "2015 Public Use Sample",
        "page40_column_must_be_the_public_use_sample",
        f"{at}/column",
        repr(table.get("column")),
    )
    _require(
        "FLPDMO_less_than_12_displayed" in table
        and table["FLPDMO_less_than_12_displayed"] is None,
        "blank_cell_must_not_be_quoted_as_zero",
        f"{at}/FLPDMO_less_than_12_displayed",
        repr(table.get("FLPDMO_less_than_12_displayed")),
    )
    _require(
        "rounding_operator" in table and table["rounding_operator"] is None,
        "rounding_operator_must_stay_unestablished",
        f"{at}/rounding_operator",
        repr(table.get("rounding_operator")),
    )
    _require(
        table.get("is_a_calibration_objective") is False,
        "page40_must_not_be_a_calibration_objective",
        f"{at}/is_a_calibration_objective",
    )

    flpdyr = _mapping(table, "FLPDYR", at)
    for key, value in flpdyr.items():
        _require(
            _is_int(value) and value >= 0,
            "displayed_count_not_a_nonnegative_integer",
            f"{at}/FLPDYR/{key}",
            repr(value),
        )
    declared_sum = table.get("positive_period_displayed_sum")
    _require(
        _is_int(declared_sum),
        "displayed_sum_not_an_integer",
        f"{at}/positive_period_displayed_sum",
    )
    actual_sum = sum(value for value in flpdyr.values() if value > 0)
    _require(
        actual_sum == declared_sum,
        "positive_period_sum_mismatch",
        f"{at}/positive_period_displayed_sum",
        f"declared {declared_sum}, exact sum {actual_sum}",
    )

    flpdmo_12 = table.get("FLPDMO_12_displayed")
    _require(
        _is_int(flpdmo_12), "flpdmo_12_not_an_integer", f"{at}/FLPDMO_12_displayed"
    )

    discrepancy = _mapping(table, "displayed_total_discrepancy", at)
    declared_gap = discrepancy.get("value")
    _require(
        _is_int(declared_gap),
        "displayed_gap_not_an_integer",
        f"{at}/displayed_total_discrepancy/value",
    )
    _require(
        declared_gap == flpdmo_12 - declared_sum,
        "displayed_gap_mismatch",
        f"{at}/displayed_total_discrepancy/value",
        f"declared {declared_gap}, exact {flpdmo_12 - declared_sum}",
    )
    _require(
        discrepancy.get("proves") is None,
        "displayed_gap_must_not_prove_a_rounding_operator",
        f"{at}/displayed_total_discrepancy/proves",
    )

    aggregates = _mapping(table, "aggregate_records", at)
    recids = aggregates.get("RECID")
    _require(
        isinstance(recids, (list, tuple))
        and list(recids) == [999996, 999997, 999998, 999999],
        "aggregate_recids_unexpected",
        f"{at}/aggregate_records/RECID",
        repr(recids),
    )
    _require(
        aggregates.get("sampled_returns_before_aggregation") == 1124,
        "sampled_return_count_unexpected",
        f"{at}/aggregate_records/sampled_returns_before_aggregation",
    )
    _require(
        aggregates.get("represented_population_returns") == 1233,
        "represented_population_count_unexpected",
        f"{at}/aggregate_records/represented_population_returns",
    )
    fded = aggregates.get("FDED_public_counts")
    _require(
        isinstance(fded, (list, tuple)) and all(_is_int(value) for value in fded),
        "fded_counts_invalid",
        f"{at}/aggregate_records/FDED_public_counts",
    )
    fded_total = aggregates.get("FDED_displayed_total")
    _require(
        _is_int(fded_total),
        "fded_total_not_an_integer",
        f"{at}/aggregate_records/FDED_displayed_total",
    )
    _require(
        sum(fded) == fded_total,
        "fded_column_sum_mismatch",
        f"{at}/aggregate_records/FDED_displayed_total",
        f"declared {fded_total}, exact sum {sum(fded)}",
    )
    _require(
        fded_total == flpdmo_12,
        "fded_total_does_not_match_flpdmo_12",
        f"{at}/aggregate_records/FDED_displayed_total",
        f"FDED {fded_total}, FLPDMO=12 {flpdmo_12}",
    )
    _require(
        aggregates.get("FDED_0_weighted_public_count")
        == aggregates.get("represented_population_returns"),
        "fded_zero_cell_must_match_the_published_population_returns",
        f"{at}/aggregate_records/FDED_0_weighted_public_count",
    )


def _validate_methods(payload: Mapping[str, Any]) -> None:
    page_method = _mapping(payload, "page_text_hash_method", "")
    _require(
        page_method.get("id") == PAGE_TEXT_HASH_METHOD_ID,
        "page_text_hash_method_unknown",
        "page_text_hash_method/id",
        repr(page_method.get("id")),
    )
    _require(
        page_method.get("fresh_pdf_extraction") is False,
        "fresh_extraction_repair_not_permitted",
        "page_text_hash_method/fresh_pdf_extraction",
    )
    _require(
        page_method.get("append_separator") is False,
        "separator_must_not_be_appended",
        "page_text_hash_method/append_separator",
    )

    file_method = _mapping(payload, "document_and_render_hash_method", "")
    _require(
        file_method.get("id") == DOCUMENT_HASH_METHOD_ID,
        "document_hash_method_unknown",
        "document_and_render_hash_method/id",
        repr(file_method.get("id")),
    )
    _require(
        file_method.get("normalization") is None,
        "document_bytes_must_not_be_normalized",
        "document_and_render_hash_method/normalization",
    )
    _require(
        file_method.get("pixel_hash") is False,
        "render_pin_must_not_claim_a_pixel_hash",
        "document_and_render_hash_method/pixel_hash",
    )
    _require(
        file_method.get("bit_identical_render_regeneration_claimed") is False,
        "render_pin_must_not_claim_bit_identical_regeneration",
        "document_and_render_hash_method/bit_identical_render_regeneration_claimed",
    )


def _validate_disclosure_avoidance(payload: Mapping[str, Any]) -> None:
    """Every page-4 treatment the adjudication enumerates must be recorded.

    Blurring in particular: the later audit is required to state blurring and
    aggregate-record treatment, so a resource that quietly drops it would let
    that obligation disappear.
    """
    block = _mapping(payload, "publisher_disclosure_avoidance", "")
    at = "publisher_disclosure_avoidance"
    _require(
        block.get("basis") == "publisher_documented",
        "disclosure_avoidance_basis_must_be_publisher_documented",
        f"{at}/basis",
        repr(block.get("basis")),
    )
    treatments = block.get("treatments")
    _require(
        isinstance(treatments, (list, tuple)) and len(treatments) >= 1,
        "disclosure_treatments_required",
        f"{at}/treatments",
    )
    identifiers = set()
    for index, row in enumerate(treatments):
        _require(
            isinstance(row, Mapping), "object_required", f"{at}/treatments/{index}"
        )
        identifier = row.get("id")
        _require(
            isinstance(identifier, str) and identifier.strip() != "",
            "disclosure_treatment_id_required",
            f"{at}/treatments/{index}/id",
        )
        statement = row.get("publisher_statement")
        _require(
            isinstance(statement, str) and statement.strip() != "",
            "disclosure_treatment_statement_required",
            f"{at}/treatments/{index}/publisher_statement",
        )
        identifiers.add(identifier)
    missing = sorted(_REQUIRED_DISCLOSURE_TREATMENTS - identifiers)
    _require(
        not missing,
        "disclosure_treatment_missing",
        f"{at}/treatments",
        ", ".join(missing),
    )
    obligation = block.get("later_audit_obligation")
    _require(
        isinstance(obligation, str) and "blurring" in obligation,
        "later_audit_must_state_blurring_treatment",
        f"{at}/later_audit_obligation",
        repr(obligation),
    )


def _validate_disagreement_record(payload: Mapping[str, Any]) -> None:
    """The recorded contradictions must stay recorded, exactly as published.

    Revision 1 of the schema constrains this block: the printed code-page
    domain disagrees with the delivered domain, that disagreement stays
    ``unresolved_and_recorded_verbatim``, and ``corrected`` stays ``False``.
    The loader enforces the schema's own contract so a resource cannot declare
    the conflict away and still load.

    Nothing here decides *which* domain is right. The publisher's printed
    wording and the delivered domain are required to be present and separate,
    and are never compared, reconciled or repaired.
    """
    at = "disagreement_record"
    record = _mapping(payload, at, "")
    for block in (
        "code_page_printed_domain",
        "two_edition_evidence",
        "page3_page4_edition_difference",
    ):
        _require(block in record, "disagreement_block_required", f"{at}/{block}")

    code_page = _mapping(record, "code_page_printed_domain", at)
    where = f"{at}/code_page_printed_domain"
    for field in ("printed_text", "delivered_domain", "status", "corrected"):
        _require(field in code_page, "conflict_field_required", f"{where}/{field}")
    printed = code_page["printed_text"]
    _require(
        isinstance(printed, str) and printed.strip() != "",
        "printed_code_page_text_required",
        f"{where}/printed_text",
        repr(printed),
    )
    delivered = code_page["delivered_domain"]
    _require(
        isinstance(delivered, (list, tuple))
        and len(delivered) >= 1
        and all(_is_int(year) for year in delivered),
        "delivered_domain_invalid",
        f"{where}/delivered_domain",
        repr(delivered),
    )
    _require(
        code_page["status"] == "unresolved_and_recorded_verbatim",
        "code_page_conflict_must_remain_unresolved",
        f"{where}/status",
        repr(code_page["status"]),
    )
    _require(
        code_page["corrected"] is False,
        "code_page_conflict_must_not_be_corrected",
        f"{where}/corrected",
        repr(code_page["corrected"]),
    )

    difference = _mapping(record, "page3_page4_edition_difference", at)
    where = f"{at}/page3_page4_edition_difference"
    _require(
        difference.get("byte_pins_normalized") is False,
        "edition_difference_must_not_normalize_byte_pins",
        f"{where}/byte_pins_normalized",
        repr(difference.get("byte_pins_normalized")),
    )
    _require(
        difference.get("substantive_wording_change") is False,
        "edition_difference_must_not_claim_a_wording_change",
        f"{where}/substantive_wording_change",
        repr(difference.get("substantive_wording_change")),
    )


def _validate_public_references(
    payload: Mapping[str, Any], documents: tuple[DocumentPin, ...]
) -> None:
    """A pinned prior receipt must attest the document identity it claims to."""
    by_id = {pin.document_id: pin for pin in documents}
    for index, row in enumerate(payload.get("public_references", ())):
        _require(
            isinstance(row, Mapping), "object_required", f"public_references/{index}"
        )
        receipt = row.get("prior_url_match_receipt")
        if receipt is None:
            continue
        at = f"public_references/{index}/prior_url_match_receipt"
        _require(isinstance(receipt, Mapping), "object_required", at)
        _require(
            _is_sha256(receipt.get("sha256")),
            "receipt_sha256_malformed",
            f"{at}/sha256",
        )
        _require(
            _is_int(receipt.get("bytes")) and receipt["bytes"] > 0,
            "receipt_bytes_invalid",
            f"{at}/bytes",
        )
        document_id = receipt.get("attests_document_id")
        _require(
            document_id in by_id,
            "receipt_attests_unknown_document",
            f"{at}/attests_document_id",
            repr(document_id),
        )
        pin = by_id[document_id]
        _require(
            receipt.get("attests_sha256") == pin.pdf_sha256,
            "receipt_attestation_does_not_match_the_document_pin",
            f"{at}/attests_sha256",
            f"receipt {receipt.get('attests_sha256')}, document {pin.pdf_sha256}",
        )
        _require(
            receipt.get("attests_bytes") == pin.pdf_bytes,
            "receipt_attestation_does_not_match_the_document_pin",
            f"{at}/attests_bytes",
            f"receipt {receipt.get('attests_bytes')}, document {pin.pdf_bytes}",
        )


def load_interpretation(payload: Mapping[str, Any]) -> StatisticalPeriodInterpretation:
    """Validate a payload against revision 1 and return a frozen view.

    Raises:
        ResourceValidationError: with a stable ``reason`` for every refusal.
    """
    _require(isinstance(payload, Mapping), "object_required", "")
    _require(
        payload.get("schema") == RESOURCE_SCHEMA_ID,
        "unknown_schema",
        "schema",
        repr(payload.get("schema")),
    )
    _require(
        payload.get("schema_version") == RESOURCE_SCHEMA_VERSION,
        "unsupported_schema_version",
        "schema_version",
        repr(payload.get("schema_version")),
    )
    _require(
        payload.get("authority") == "documentary_interpretation_only",
        "authority_must_be_documentary_only",
        "authority",
        repr(payload.get("authority")),
    )
    unknown = sorted(set(payload) - _ALLOWED_TOP_LEVEL)
    _require(not unknown, "unknown_top_level_key", "", ", ".join(unknown))
    missing = sorted(_ALLOWED_TOP_LEVEL - set(payload))
    _require(not missing, "missing_top_level_key", "", ", ".join(missing))
    _reject_serialized_verification(payload)

    interpretation_id = payload.get("interpretation_id")
    _require(
        isinstance(interpretation_id, str) and interpretation_id.strip() != "",
        "interpretation_id_required",
        "interpretation_id",
    )

    grants = _mapping(payload, "grants", "")
    for key, value in grants.items():
        _require(
            value is False,
            "granted_authority_not_permitted",
            f"grants/{key}",
            repr(value),
        )

    non_claims = _mapping(payload, "non_claims", "")
    for key, value in non_claims.items():
        _require(
            value is False, "non_claim_must_be_false", f"non_claims/{key}", repr(value)
        )

    pins = _mapping(payload, "documentary_pins", "")
    _require(
        pins.get("status") == "declared",
        "documentary_pins_must_start_declared",
        "documentary_pins/status",
        repr(pins.get("status")),
    )
    _require(
        pins.get("silent_fresh_extraction_repair") is False,
        "fresh_extraction_repair_not_permitted",
        "documentary_pins/silent_fresh_extraction_repair",
    )

    growth = _mapping(payload, "growth_contract", "")
    _require(
        growth.get("first_revision_refuses_all_growth") is True,
        "growth_contract_must_refuse_all_growth",
        "growth_contract/first_revision_refuses_all_growth",
    )
    _require(
        list(growth.get("accepted_convention_status", ()))
        == [ACCEPTED_CONVENTION_STATUS],
        "growth_contract_accepts_more_than_a_proposal",
        "growth_contract/accepted_convention_status",
        repr(growth.get("accepted_convention_status")),
    )
    _require(
        growth.get("refusal_is_unconditional") is True,
        "growth_refusal_must_be_unconditional",
        "growth_contract/refusal_is_unconditional",
    )

    future = _mapping(payload, "future_positive_admission", "")
    for key in (
        "implemented",
        "review_fingerprint_mechanism_defined",
        "external_caller_trust_channel_defined",
        "comparison_evidence_binding_defined",
    ):
        _require(
            future.get(key) is False,
            "future_admission_path_must_not_be_claimed",
            f"future_positive_admission/{key}",
            repr(future.get(key)),
        )

    reference = _mapping(payload, "statistical_reference_period", "")
    _require(
        reference.get("tax_year") == STATISTICAL_REFERENCE_TAX_YEAR,
        "statistical_reference_year_unexpected",
        "statistical_reference_period/tax_year",
        repr(reference.get("tax_year")),
    )
    _require(
        reference.get("basis") == "publisher_documented",
        "statistical_reference_basis_must_be_publisher_documented",
        "statistical_reference_period/basis",
        repr(reference.get("basis")),
    )

    processing = _mapping(payload, "processing_window", "")
    _require(
        processing.get("calendar_year") == PROCESSING_CALENDAR_YEAR,
        "processing_window_unexpected",
        "processing_window/calendar_year",
        repr(processing.get("calendar_year")),
    )

    preservation = _mapping(payload, "reported_period_preservation", "")
    _require(
        tuple(preservation.get("fields", ())) == PRESERVED_PERIOD_FIELDS,
        "preserved_period_fields_unexpected",
        "reported_period_preservation/fields",
        repr(preservation.get("fields")),
    )
    _require(
        preservation.get("automatic_row_year_repair") is False,
        "row_year_repair_not_permitted",
        "reported_period_preservation/automatic_row_year_repair",
    )
    _require(
        preservation.get("inference_from_statistical_reference_period") is False,
        "reported_period_must_not_be_inferred",
        "reported_period_preservation/inference_from_statistical_reference_period",
    )
    flpdyr_domain = preservation.get("delivered_FLPDYR_domain")
    _require(
        isinstance(flpdyr_domain, (list, tuple))
        and len(flpdyr_domain) >= 1
        and all(_is_int(year) for year in flpdyr_domain),
        "delivered_flpdyr_domain_invalid",
        "reported_period_preservation/delivered_FLPDYR_domain",
        repr(flpdyr_domain),
    )
    flpdmo_domain = preservation.get("delivered_FLPDMO_domain")
    _require(
        isinstance(flpdmo_domain, (list, tuple))
        and len(flpdmo_domain) >= 1
        and all(_is_int(month) for month in flpdmo_domain),
        "delivered_flpdmo_domain_invalid",
        "reported_period_preservation/delivered_FLPDMO_domain",
        repr(flpdmo_domain),
    )

    geography = _mapping(payload, "geographic_meaning", "")
    _require(
        geography.get("national_only") is True,
        "national_only_meaning_required",
        "geographic_meaning/national_only",
        repr(geography.get("national_only")),
    )

    binding_row = _mapping(payload, "raw_source_binding", "")
    _require(
        binding_row.get("definition_schema")
        == "microcosm.us.puf_2015_raw_source_definition",
        "raw_source_binding_schema_unexpected",
        "raw_source_binding/definition_schema",
        repr(binding_row.get("definition_schema")),
    )
    _require(
        _is_sha256(binding_row.get("definition_sha256")),
        "raw_source_binding_hash_malformed",
        "raw_source_binding/definition_sha256",
    )
    _require(
        _is_int(binding_row.get("definition_bytes"))
        and binding_row["definition_bytes"] > 0,
        "raw_source_binding_bytes_invalid",
        "raw_source_binding/definition_bytes",
    )
    _require(
        binding_row.get("preserved_period_semantics") == RAW_PERIOD_SEMANTICS,
        "predecessor_period_semantics_must_be_preserved",
        "raw_source_binding/preserved_period_semantics",
        repr(binding_row.get("preserved_period_semantics")),
    )
    _require(
        binding_row.get("retroactive_mutation") is False,
        "retroactive_mutation_not_permitted",
        "raw_source_binding/retroactive_mutation",
    )
    _require(
        binding_row.get("imports_predecessor_module") is False,
        "predecessor_must_be_bound_by_identity_not_import",
        "raw_source_binding/imports_predecessor_module",
    )
    _require(
        _is_int(binding_row.get("definition_schema_version")),
        "raw_source_binding_version_invalid",
        "raw_source_binding/definition_schema_version",
    )

    for row in payload.get("deferred_required_work", ()):
        _require(isinstance(row, Mapping), "object_required", "deferred_required_work")
        _require(
            row.get("implemented") is False and row.get("calculated_here") is False,
            "deferred_work_must_not_be_claimed_here",
            f"deferred_required_work/{row.get('id')}",
        )

    _validate_methods(payload)
    _validate_page40(payload)
    _validate_disclosure_avoidance(payload)
    _validate_disagreement_record(payload)
    convention = _validate_convention(payload)
    documents = _validate_documents(payload)
    renders = _validate_renders(payload, documents)
    _validate_public_references(payload, documents)

    frozen = _freeze(payload)
    try:
        # Proved here, not stored: a resource that cannot be canonically
        # identified cannot be bound to a verdict either, so it is refused with
        # a stable reason rather than escaping as a bare ValueError from the
        # JSON encoder later, when ``resource_sha256`` recomputes it.
        canonical_resource_sha256(frozen)
    except ValueError as error:
        raise ResourceValidationError(
            "resource_is_not_canonically_identifiable", "", str(error)
        ) from error

    return StatisticalPeriodInterpretation(
        interpretation_id=interpretation_id,
        schema_version=RESOURCE_SCHEMA_VERSION,
        statistical_reference_tax_year=STATISTICAL_REFERENCE_TAX_YEAR,
        processing_calendar_year=PROCESSING_CALENDAR_YEAR,
        preserved_period_fields=PRESERVED_PERIOD_FIELDS,
        delivered_flpdyr_domain=tuple(flpdyr_domain),
        delivered_flpdmo_domain=tuple(flpdmo_domain),
        national_only=True,
        convention=convention,
        raw_source_binding=RawSourceBinding(
            definition_schema=binding_row["definition_schema"],
            definition_schema_version=binding_row["definition_schema_version"],
            definition_sha256=binding_row["definition_sha256"],
            definition_bytes=binding_row["definition_bytes"],
            preserved_period_semantics=RAW_PERIOD_SEMANTICS,
        ),
        documents=documents,
        renders=renders,
        payload=frozen,
    )


def package_resource_bytes() -> bytes:
    """The exact packaged resource bytes."""
    return (
        files(_RESOURCE_PACKAGE)
        .joinpath(_RESOURCE_DIRECTORY)
        .joinpath(_RESOURCE_FILENAME)
        .read_bytes()
    )


def package_schema() -> Mapping[str, Any]:
    """The packaged JSON Schema for revision 1, as a frozen mapping."""
    raw = (
        files(_RESOURCE_PACKAGE)
        .joinpath(_RESOURCE_DIRECTORY)
        .joinpath(_SCHEMA_FILENAME)
        .read_bytes()
    )
    return _freeze(json.loads(raw.decode("utf-8")))


def load_packaged_interpretation() -> StatisticalPeriodInterpretation:
    """Load and validate the packaged interpretation resource."""
    return load_interpretation(json.loads(package_resource_bytes().decode("utf-8")))


# --------------------------------------------------------------------------
# Documentary verification, computed from resolved bytes
# --------------------------------------------------------------------------

#: A caller-supplied resolver: logical ID in, exact bytes out, ``None`` if absent.
Resolver = Callable[[str], "bytes | None"]


@dataclass(frozen=True, slots=True)
class PinCheck:
    """One documentary pin, checked against bytes the caller resolved."""

    logical_id: str
    kind: str
    ok: bool
    reason: str | None
    detail: str = ""


def documentary_pin_roster(
    interpretation: StatisticalPeriodInterpretation,
) -> tuple[str, ...]:
    """Every documentary pin the resource declares, in verification order.

    The roster is the completeness contract. A verdict covers this exact list
    or it covers nothing, so a subset of passing checks can never stand in for
    a whole resource.
    """
    roster: list[str] = []
    for document in interpretation.documents:
        roster.append(document.document_id)
        roster.append(document.retained_text.text_id)
        roster.extend(
            f"{document.retained_text.text_id}#{locator.pdf_page}"
            for locator in document.pages
        )
    roster.extend(render.render_id for render in interpretation.renders)
    return tuple(roster)


#: Handed to :class:`DocumentaryVerification` by the verifier and by nothing
#: else, so a verdict exists only where bytes were actually re-authenticated.
_VERIFIER_ISSUANCE: Final = object()


class DocumentaryVerification:
    """The computed verdict over one interpretation's documentary pins.

    Only :func:`verify_documentary_pins` issues one, and every verdict holds
    the exact interpretation it was issued for together with the complete pin
    roster it covered. ``verified`` says the whole roster was re-authenticated;
    :meth:`authenticates` additionally requires the verdict to be presented
    with that same interpretation. A serialized flag, a hand-built check, a
    copy of a genuine verdict's checks, a partial roster, an edited copy of the
    view and a verdict issued for another resource therefore all authenticate
    nothing.

    A verdict is deliberately not copyable, picklable or comparable by value:
    a copy of a verdict is a verdict nobody issued.
    """

    __slots__ = (
        "_checks",
        "_interpretation",
        "_interpretation_id",
        "_pin_roster",
        "_resource_sha256",
    )

    def __init__(
        self,
        checks: Sequence[PinCheck],
        *,
        interpretation: StatisticalPeriodInterpretation,
        pin_roster: Sequence[str],
        issued_by: object = None,
    ) -> None:
        if issued_by is not _VERIFIER_ISSUANCE:
            raise VerificationIssuanceError()
        object.__setattr__(self, "_checks", tuple(checks))
        object.__setattr__(self, "_interpretation", interpretation)
        object.__setattr__(self, "_interpretation_id", interpretation.interpretation_id)
        object.__setattr__(self, "_resource_sha256", interpretation.resource_sha256)
        object.__setattr__(self, "_pin_roster", tuple(pin_roster))

    def __setattr__(self, name: str, value: object) -> NoReturn:
        raise AttributeError("DocumentaryVerification is immutable")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("DocumentaryVerification is immutable")

    def __repr__(self) -> str:
        return (
            f"DocumentaryVerification(interpretation_id="
            f"{self._interpretation_id!r}, status={self.status!r}, "
            f"checks={len(self._checks)})"
        )

    @property
    def checks(self) -> tuple[PinCheck, ...]:
        return self._checks

    @property
    def interpretation_id(self) -> str:
        """The ``interpretation_id`` this verdict was issued for."""
        return self._interpretation_id

    @property
    def resource_sha256(self) -> str:
        """Canonical identity of the exact resource this verdict was issued for."""
        return self._resource_sha256

    @property
    def pin_roster(self) -> tuple[str, ...]:
        """The complete pin roster this verdict covered."""
        return self._pin_roster

    @property
    def verified(self) -> bool:
        return (
            bool(self._pin_roster)
            and tuple(check.logical_id for check in self._checks) == self._pin_roster
            and all(check.ok for check in self._checks)
        )

    @property
    def status(self) -> str:
        return "verified" if self.verified else "unverified"

    @property
    def failures(self) -> tuple[PinCheck, ...]:
        return tuple(check for check in self._checks if not check.ok)

    @property
    def reasons(self) -> tuple[str, ...]:
        seen: list[str] = []
        for check in self.failures:
            if check.reason and check.reason not in seen:
                seen.append(check.reason)
        return tuple(seen)

    def binding_failures(
        self, interpretation: StatisticalPeriodInterpretation
    ) -> tuple[str, ...]:
        """Why this verdict does not belong to ``interpretation``.

        Empty when it does. The load-bearing clause is the first: the verdict
        authenticates the exact object the verifier was handed, so an edited
        copy of that view — ``dataclasses.replace`` produces one, and it is a
        public stdlib call — is a different interpretation and is refused even
        though it inherited every value the verdict recorded.

        The remaining clauses are not redundant. ``resource_sha256`` is
        recomputed from the payload on every read rather than compared against
        a stored copy, so they also catch a view edited in place after the
        verdict was issued, and they say which binding moved.
        """
        reasons: list[str] = []
        if interpretation is not self._interpretation:
            reasons.append("verification_issued_for_a_different_interpretation")
        if self._interpretation_id != interpretation.interpretation_id:
            reasons.append("verification_issued_for_another_interpretation_id")
        if self._resource_sha256 != interpretation.resource_sha256:
            reasons.append("verification_issued_for_other_resource_bytes")
        if self._pin_roster != documentary_pin_roster(interpretation):
            reasons.append("verification_roster_is_not_this_resource_roster")
        return tuple(reasons)

    def authenticates(self, interpretation: StatisticalPeriodInterpretation) -> bool:
        """True only for the exact interpretation this verdict was issued for."""
        return self.verified and not self.binding_failures(interpretation)


def _check_bytes(
    logical_id: str,
    kind: str,
    resolved: object,
    expected_sha256: str,
    expected_bytes: int,
) -> PinCheck:
    if resolved is None:
        return PinCheck(logical_id, kind, False, "unresolved_bytes")
    if not isinstance(resolved, (bytes, bytearray)):
        return PinCheck(
            logical_id,
            kind,
            False,
            "resolver_returned_non_bytes",
            type(resolved).__name__,
        )
    raw = bytes(resolved)
    if not raw:
        return PinCheck(logical_id, kind, False, "empty_bytes")
    if len(raw) != expected_bytes:
        return PinCheck(
            logical_id,
            kind,
            False,
            "byte_length_mismatch",
            f"declared {expected_bytes}, actual {len(raw)}",
        )
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        return PinCheck(
            logical_id,
            kind,
            False,
            "hash_mismatch",
            f"declared {expected_sha256}, actual {actual}",
        )
    return PinCheck(logical_id, kind, True, None)


def verify_documentary_pins(
    interpretation: StatisticalPeriodInterpretation, resolve: Resolver
) -> DocumentaryVerification:
    """Re-authenticate every documentary pin from bytes the caller resolves.

    The resource's pins are only *declared* until this runs. Missing, mutated
    or empty bytes leave the verdict unverified — they are never repaired by a
    fresh extraction, and an unverified verdict still permits an explicitly
    unverified documentary display while refusing every growth use.

    The verdict is issued against *this* interpretation: it carries the
    resource's canonical identity and its complete pin roster, so it cannot be
    carried across to a different interpretation later.
    """
    checks: list[PinCheck] = []
    for document in interpretation.documents:
        checks.append(
            _check_bytes(
                document.document_id,
                "pdf",
                resolve(document.document_id),
                document.pdf_sha256,
                document.pdf_bytes,
            )
        )
        text = document.retained_text
        container = resolve(text.text_id)
        checks.append(
            _check_bytes(
                text.text_id, "retained_text", container, text.sha256, text.bytes_
            )
        )
        container_ok = checks[-1].ok
        for locator in document.pages:
            logical = f"{text.text_id}#{locator.pdf_page}"
            if not container_ok:
                checks.append(
                    PinCheck(logical, "page_text", False, "container_unavailable")
                )
                continue
            try:
                actual = page_text_sha256(
                    bytes(container),  # type: ignore[arg-type]
                    expected_container_sha256=text.sha256,
                    pdf_page=locator.pdf_page,
                    expected_segment_count=text.segment_count,
                )
            except PageTextHashError as error:
                checks.append(
                    PinCheck(logical, "page_text", False, error.reason, error.detail)
                )
                continue
            if actual != locator.text_sha256:
                checks.append(
                    PinCheck(
                        logical,
                        "page_text",
                        False,
                        "hash_mismatch",
                        f"declared {locator.text_sha256}, actual {actual}",
                    )
                )
            else:
                checks.append(PinCheck(logical, "page_text", True, None))

    for render in interpretation.renders:
        checks.append(
            _check_bytes(
                render.render_id,
                "render",
                resolve(render.render_id),
                render.sha256,
                render.bytes_,
            )
        )
    return DocumentaryVerification(
        checks,
        interpretation=interpretation,
        pin_roster=documentary_pin_roster(interpretation),
        issued_by=_VERIFIER_ISSUANCE,
    )


# --------------------------------------------------------------------------
# The shared growth-refusal guard
# --------------------------------------------------------------------------

#: The unconditional refusal reason carried by every admission decision.
GROWTH_REFUSED_UNCONDITIONALLY: Final = "first_schema_revision_refuses_all_growth"
NO_POSITIVE_ADMISSION_PATH: Final = "no_positive_admission_path_implemented"


def classify_convention_status(status: object) -> str:
    """Classify a convention status for reporting. Every class refuses growth."""
    if status is None:
        return "missing"
    if not isinstance(status, str):
        return "unknown"
    stripped = status.strip()
    if stripped == "":
        return "missing"
    if stripped == ACCEPTED_CONVENTION_STATUS:
        return "proposed"
    lowered = stripped.lower()
    if any(token in lowered for token in _REVIEW_CLAIMING_TOKENS):
        return "claimed_reviewed"
    return "unknown"


@dataclass(frozen=True, slots=True)
class GrowthAdmission:
    """A growth decision. ``admitted`` is a property and is always ``False``."""

    reasons: tuple[str, ...]
    convention_class: str
    documentary_status: str

    @property
    def admitted(self) -> bool:
        return False


def growth_admission(
    *,
    convention_status: object = None,
    convention_review: object = None,
    documentary_verification: DocumentaryVerification | None = None,
    already_applied_factors: Sequence[str] | Iterable[str] = (),
    requested_use: str = "growth",
) -> GrowthAdmission:
    """Decide whether growth may be applied. Revision 1 always refuses.

    The refusal is unconditional: a proposed convention refuses because a
    proposal is not an approval, and every other state — missing, unknown, or
    claiming a review — is invalid in this revision. Well-formed self-supplied
    hashes and review fields change nothing, and no fingerprint mechanism that
    could grant admission is defined here.
    """
    reasons: list[str] = [GROWTH_REFUSED_UNCONDITIONALLY, NO_POSITIVE_ADMISSION_PATH]
    convention_class = classify_convention_status(convention_status)
    if convention_class == "proposed":
        reasons.append("convention_status_proposed_is_not_an_approval")
    else:
        reasons.append(f"convention_status_{convention_class}_is_invalid")
    if convention_review is not None:
        reasons.append("claimed_convention_review_not_honoured")
    if documentary_verification is None:
        reasons.append("documentary_pins_unverified")
        documentary_status = "unverified"
    else:
        documentary_status = documentary_verification.status
        if not documentary_verification.verified:
            reasons.append("documentary_pins_unverified")
    applied = tuple(already_applied_factors)
    if applied:
        reasons.append("double_growth_would_compound")
    if requested_use != "growth":
        reasons.append(f"requested_use_{requested_use}_not_granted")
    return GrowthAdmission(
        reasons=tuple(reasons),
        convention_class=convention_class,
        documentary_status=documentary_status,
    )


def refuse_growth(**kwargs: Any) -> NoReturn:
    """Refuse a growth request. Always raises :class:`GrowthRefusedError`."""
    raise GrowthRefusedError(growth_admission(**kwargs))


#: Authorities this documentary artifact never grants.
REFUSED_AUTHORITIES: Final = (
    "growth",
    "factor_generation",
    "calibration",
    "scientific_admission",
    "release_admission",
    "tax_law",
    "congressional_district_estimation",
    "period_repair",
)


def grants_authority(use: str) -> bool:
    """Always ``False``. This artifact is a documentary interpretation."""
    return False


def require_authority(use: str) -> NoReturn:
    """Refuse a non-documentary authority. Always raises."""
    raise AuthorityRefusedError(use)


# --------------------------------------------------------------------------
# Consuming the interpretation
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReportedPeriodAnnotation:
    """A row's reported period, echoed verbatim beside the shared reference."""

    raw_flpdyr: Any
    raw_flpdmo: Any
    statistical_reference_tax_year: int
    processing_calendar_year: int
    period_semantics: str
    within_delivered_flpdyr_domain: bool

    @property
    def growth_admitted(self) -> bool:
        return False


def annotate_reported_period(
    interpretation: StatisticalPeriodInterpretation,
    *,
    flpdyr: Any,
    flpdmo: Any,
    repair_to_statistical_reference: bool = False,
) -> ReportedPeriodAnnotation:
    """Annotate one reported period without changing it.

    The raw tokens come back exactly as they went in — the same objects, not
    coerced, not repaired, not inferred from the statistical reference period.
    Asking for repair is refused rather than performed.
    """
    if repair_to_statistical_reference:
        require_authority("period_repair")
    return ReportedPeriodAnnotation(
        raw_flpdyr=flpdyr,
        raw_flpdmo=flpdmo,
        statistical_reference_tax_year=interpretation.statistical_reference_tax_year,
        processing_calendar_year=interpretation.processing_calendar_year,
        period_semantics=RAW_PERIOD_SEMANTICS,
        within_delivered_flpdyr_domain=flpdyr in interpretation.delivered_flpdyr_domain,
    )


def documentary_display(
    interpretation: StatisticalPeriodInterpretation,
    verification: DocumentaryVerification | None = None,
    *,
    resolve: Resolver | None = None,
) -> Mapping[str, Any]:
    """A display record that states its own verification status.

    Provenance is reported as authenticated only when a verdict issued by
    :func:`verify_documentary_pins` *for this exact resource and its complete
    pin roster* passed every check. Pass ``resolve`` instead of a verdict to
    have the display re-authenticate the resolved bytes itself.

    With no verification, a failed one, or one issued for another
    interpretation, the record is explicitly labelled unverified, reports
    ``provenance_authenticated`` as ``False`` and keeps every refusal reason.
    It never reports authenticated documentary provenance on the strength of
    the resource's own assertions.
    """
    if resolve is not None:
        if verification is not None:
            raise InterpretationError(
                "documentary_display takes either a verification or a resolver, "
                "not both"
            )
        verification = verify_documentary_pins(interpretation, resolve)
    if verification is None:
        verified = False
        reasons: tuple[str, ...] = ()
    else:
        binding = verification.binding_failures(interpretation)
        verified = verification.verified and not binding
        reasons = verification.reasons + binding
    return _freeze(
        {
            "interpretation_id": interpretation.interpretation_id,
            "schema": RESOURCE_SCHEMA_ID,
            "schema_version": interpretation.schema_version,
            "authority": "documentary_interpretation_only",
            "statistical_reference_tax_year": interpretation.statistical_reference_tax_year,
            "processing_calendar_year": interpretation.processing_calendar_year,
            "preserved_period_fields": list(interpretation.preserved_period_fields),
            "period_semantics": RAW_PERIOD_SEMANTICS,
            "national_only": interpretation.national_only,
            "convention_id": interpretation.convention.convention_id,
            "convention_status": interpretation.convention.convention_status,
            "convention_review": interpretation.convention.convention_review,
            "documentary_pins_status": "declared" if not verified else "verified",
            "documentary_pins_verified": verified,
            "provenance_authenticated": verified,
            "unverified_reasons": list(reasons),
            "growth_admitted": False,
            "scientific_admission": False,
            "release_admission": False,
        }
    )


def graph_annotations(
    interpretation: StatisticalPeriodInterpretation,
) -> Mapping[str, Mapping[str, Any]]:
    """Machine annotations that keep documentary facts apart from the proposal.

    Every entry carries a ``basis``: ``publisher_documented`` for what the IRS
    booklet states, ``delivered_source`` for what the frozen raw definition
    recorded, and ``proposed_modeling_convention`` for the modeling choice that
    is not yet reviewed and grants nothing.
    """
    return _freeze(
        {
            "statistical_reference_tax_year": {
                "value": interpretation.statistical_reference_tax_year,
                "basis": "publisher_documented",
            },
            "processing_calendar_year": {
                "value": interpretation.processing_calendar_year,
                "basis": "publisher_documented",
            },
            "national_only": {
                "value": interpretation.national_only,
                "basis": "publisher_documented",
            },
            "reported_period_semantics": {
                "value": RAW_PERIOD_SEMANTICS,
                "basis": "delivered_source",
            },
            "delivered_flpdyr_domain": {
                "value": list(interpretation.delivered_flpdyr_domain),
                "basis": "delivered_source",
            },
            "modeling_convention": {
                "value": interpretation.convention.convention_id,
                "basis": "proposed_modeling_convention",
                "convention_status": interpretation.convention.convention_status,
                "convention_review": interpretation.convention.convention_review,
                "growth_admitted": False,
            },
        }
    )
