"""The PUF 2015 statistical-period interpretation: source-only contracts.

Everything here is synthetic or invented. No genuine PUF record, amount,
weight, factor table, calibration target, model or graph is loaded, and the
retained IRS booklets are never read: the declared hash method is exercised
against synthetic multi-page text whose hashes are *recomputed* in the test
rather than compared against pinned strings.

The suite is built from one minimal valid payload that each test mutates, so a
refusal is demonstrated by a single deliberate change rather than by a fixture
that mirrors the implementation.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from microcosm.build import puf_2015_statistical_period_interpretation as period
from microcosm.build.puf_2015_statistical_period_interpretation import (
    ACCEPTED_CONVENTION_STATUS,
    PAGE_SEPARATOR,
    PROCESSING_CALENDAR_YEAR,
    RAW_PERIOD_SEMANTICS,
    RESOURCE_SCHEMA_ID,
    RESOURCE_SCHEMA_VERSION,
    STATISTICAL_REFERENCE_TAX_YEAR,
    AuthorityRefusedError,
    DocumentaryVerification,
    GrowthRefusedError,
    PageTextHashError,
    ResourceValidationError,
    annotate_reported_period,
    canonical_resource_sha256,
    classify_convention_status,
    documentary_display,
    grants_authority,
    graph_annotations,
    growth_admission,
    load_interpretation,
    load_packaged_interpretation,
    package_resource_bytes,
    package_schema,
    page_text_sha256,
    refuse_growth,
    require_authority,
    verify_documentary_pins,
)

# ---------------------------------------------------------------------------
# Synthetic fixtures: invented bytes, hashes recomputed here
# ---------------------------------------------------------------------------

SYNTHETIC_PAGE_COUNT = 6


def synthetic_pages() -> list[str]:
    """Invented booklet pages with headers, footers and deliberate whitespace."""
    return [
        f"INVENTED BOOKLET \n{index} \n\n  section {index}  body text \nfooter {index} \n"
        for index in range(1, SYNTHETIC_PAGE_COUNT + 1)
    ]


def synthetic_container(pages: list[str] | None = None) -> bytes:
    """Join invented pages with the literal formfeed, exactly as declared."""
    return PAGE_SEPARATOR.join(
        pages if pages is not None else synthetic_pages()
    ).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def synthetic_payload() -> dict[str, Any]:
    """A minimal payload that satisfies revision 1, with real computed hashes."""
    container = synthetic_container()
    pages = synthetic_pages()
    pdf_bytes = b"%PDF-1.7 invented main document\n"
    render_bytes = b"\x89PNG\r\n\x1a\n invented render\n"
    return {
        "schema": RESOURCE_SCHEMA_ID,
        "schema_version": RESOURCE_SCHEMA_VERSION,
        "interpretation_id": "invented_interpretation.v1",
        "authority": "documentary_interpretation_only",
        "grants": {
            "growth_authority": False,
            "scientific_admission": False,
            "release_admission": False,
            "tax_law_authority": False,
            "district_estimation_authority": False,
            "calibration_authority": False,
        },
        "scope": {"question": "invented", "answer": "invented"},
        "alternatives_considered": [{"alternative": "invented", "status": "invented"}],
        "raw_source_binding": {
            "definition_schema": "microcosm.us.puf_2015_raw_source_definition",
            "definition_schema_version": 1,
            "definition_sha256": sha256(b"invented raw source definition"),
            "definition_bytes": 30,
            "preserved_period_semantics": RAW_PERIOD_SEMANTICS,
            "binding_kind": "identity_and_hash_only",
            "imports_predecessor_module": False,
            "retroactive_mutation": False,
        },
        "statistical_reference_period": {
            "tax_year": STATISTICAL_REFERENCE_TAX_YEAR,
            "basis": "publisher_documented",
            "does_not_establish": ["invented"],
        },
        "reported_period_preservation": {
            "fields": ["FLPDYR", "FLPDMO"],
            "delivered_FLPDYR_domain": [2012, 2013, 2014, 2015],
            "delivered_FLPDMO_domain": [12],
            "automatic_row_year_repair": False,
            "inference_from_statistical_reference_period": False,
        },
        "processing_window": {
            "calendar_year": PROCESSING_CALENDAR_YEAR,
            "basis": "publisher_documented",
        },
        "publisher_disclosure_avoidance": {
            "basis": "publisher_documented",
            "pdf_page": 4,
            "printed_page": 3,
            "treatments": [
                {"id": "fiscal_period_conversion", "publisher_statement": "invented"},
                {"id": "extreme_value_aggregation", "publisher_statement": "invented"},
                {"id": "multivariate_blurring", "publisher_statement": "invented"},
            ],
            "later_audit_obligation": "State blurring and aggregate-record treatment.",
        },
        "geographic_meaning": {"national_only": True, "basis": "publisher_documented"},
        "distinct_items": [{"item": "invented"}],
        "convention": {
            "convention_id": "invented_convention.proposed.v1",
            "convention_status": ACCEPTED_CONVENTION_STATUS,
            "convention_review": None,
            "growth_admitted": False,
            "label": "proposed_modeling_convention",
            "basis": "modeling_choice_not_publisher_documented",
            "description": "An invented proposal used only by this test suite.",
            "review_required_before_any_use": True,
        },
        "growth_contract": {
            "first_revision_refuses_all_growth": True,
            "accepted_convention_status": ["proposed"],
            "accepted_convention_review": [None],
            "invalid_convention_states": ["missing", "unknown", "claimed_reviewed"],
            "refusal_is_unconditional": True,
        },
        "future_positive_admission": {
            "implemented": False,
            "review_fingerprint_mechanism_defined": False,
            "external_caller_trust_channel_defined": False,
            "comparison_evidence_binding_defined": False,
            "requires": ["invented"],
        },
        "documentary_pins": {
            "status": "declared",
            "resolver": "caller_supplied_by_logical_id",
            "silent_fresh_extraction_repair": False,
        },
        "documents": [
            {
                "document_id": "invented-doc",
                "edition": "invented-edition",
                "role": "primary_public_irs_document",
                "pdf": {"sha256": sha256(pdf_bytes), "bytes": len(pdf_bytes)},
                "retained_text": {
                    "text_id": "invented-doc-text",
                    "sha256": sha256(container),
                    "bytes": len(container),
                    "segment_count": SYNTHETIC_PAGE_COUNT,
                },
                "pages": [
                    {
                        "pdf_page": number,
                        "printed_page": number - 1,
                        "text_sha256": sha256(pages[number - 1].encode("utf-8")),
                        "role": f"invented_role_{number}",
                        "cross_edition_text_identical": True,
                    }
                    for number in (2, 3, 5)
                ],
            }
        ],
        "renders": [
            {
                "render_id": "invented-render",
                "document_id": "invented-doc",
                "pdf_page": 3,
                "sha256": sha256(render_bytes),
                "bytes": len(render_bytes),
                "visually_inspected": True,
            }
        ],
        "page_text_hash_method": {
            "id": period.PAGE_TEXT_HASH_METHOD_ID,
            "decode": "utf-8 strict",
            "split": "literal U+000C formfeed",
            "index": "one-based",
            "locator_validation": "invented",
            "preserve": "invented",
            "encode": "utf-8 strict",
            "hash": "invented",
            "append_separator": False,
            "fresh_pdf_extraction": False,
        },
        "document_and_render_hash_method": {
            "id": period.DOCUMENT_HASH_METHOD_ID,
            "hash": "invented",
            "normalization": None,
            "pixel_hash": False,
            "bit_identical_render_regeneration_claimed": False,
        },
        "canonical_resource_hash_method": "invented",
        "extraction_provenance": {
            "historical_receipt": {
                "receipt_id": "invented-receipt",
                "sha256": sha256(b"invented receipt"),
                "bytes": 16,
                "extract_text_kwargs": None,
                "mutated_by_this_resource": False,
            },
            "independent_reproduction": {
                "reproduction_id": "invented-reproduction",
                "sha256": sha256(b"invented reproduction"),
                "bytes": 21,
                "label": "separately_pinned_independent_reproduction",
                "rewrites_historical_receipt": False,
                "replaces_retained_evidence": False,
            },
        },
        "disagreement_record": {
            "code_page_printed_domain": {
                "printed_text": "invented printed domain",
                "delivered_domain": [2012, 2013, 2014, 2015],
                "status": "unresolved_and_recorded_verbatim",
                "corrected": False,
            },
            "two_edition_evidence": {"editions": ["invented-doc"]},
            "page3_page4_edition_difference": {
                "byte_pins_normalized": False,
                "substantive_wording_change": False,
            },
        },
        "page40_weighted_tabulation": {
            "column": "2015 Public Use Sample",
            "kind": "published_rounded_weighted_counts",
            "FLPDYR": {"2012": 10, "2013": 20, "2014": 30, "2015": 40, "2016": 0},
            "positive_period_displayed_sum": 100,
            "FLPDMO_12_displayed": 101,
            "FLPDMO_less_than_12_displayed": None,
            "missing_cell_semantics": "blank on the rendered page",
            "displayed_total_discrepancy": {
                "value": 1,
                "units": "one displayed weighted return",
                "proves": None,
            },
            "aggregate_records": {
                "RECID": [999996, 999997, 999998, 999999],
                "sampled_returns_before_aggregation": 1124,
                "represented_population_returns": 1233,
                "FDED_0_weighted_public_count": 1233,
                "FDED_public_counts": [1233, 50, 51, 98667],
                "FDED_displayed_total": 101,
            },
            "rounding_operator": None,
            "comparison_units": {
                "delivered_S006": "int64 hundredths, never divided",
                "published_counts": "integer returns multiplied by 100",
                "residuals_and_tolerances": "hundredths of a weighted return",
            },
            "is_a_calibration_objective": False,
        },
        "deferred_required_work": [
            {
                "id": "invented_later_work",
                "implemented": False,
                "calculated_here": False,
                "requires_separate_authorization": True,
                "description": "invented",
            }
        ],
        "unchanged_historical_records": {"invented": True},
        "public_references": [],
        "non_claims": {"growth_factor_admission": False},
    }


@pytest.fixture
def payload() -> dict[str, Any]:
    body = synthetic_payload()
    # The invented FDED column must reconcile exactly, like the real one.
    body["page40_weighted_tabulation"]["aggregate_records"]["FDED_public_counts"] = [
        1233,
        50,
        51,
        101 - 1233 - 50 - 51,
    ]
    return body


@pytest.fixture
def resolver_bytes() -> dict[str, bytes]:
    return {
        "invented-doc": b"%PDF-1.7 invented main document\n",
        "invented-doc-text": synthetic_container(),
        "invented-render": b"\x89PNG\r\n\x1a\n invented render\n",
    }


def resolver_from(mapping: dict[str, bytes]):
    def resolve(logical_id: str) -> bytes | None:
        return mapping.get(logical_id)

    return resolve


# ---------------------------------------------------------------------------
# The exported source API
# ---------------------------------------------------------------------------


def test_exported_api_is_sorted_complete_and_resolvable() -> None:
    assert period.__all__ == sorted(period.__all__)
    for name in period.__all__:
        assert hasattr(period, name), name
    public = {
        name
        for name in vars(period)
        if not name.startswith("_") and name not in {"annotations"}
    }
    module_owned = {
        name
        for name in public
        if getattr(vars(period)[name], "__module__", period.__name__) == period.__name__
        or not hasattr(vars(period)[name], "__module__")
    }
    imported = {"hashlib", "json", "dataclass", "files", "MappingProxyType"}
    assert module_owned - imported <= set(period.__all__)


def test_module_imports_only_the_standard_library() -> None:
    """The interpretation must load without starting a build."""
    source = Path(period.__file__).read_text(encoding="utf-8")
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    assert roots <= {
        "__future__",
        "collections",
        "dataclasses",
        "hashlib",
        "importlib",
        "json",
        "types",
        "typing",
    }, sorted(roots)
    assert "microcosm" not in roots
    assert "numpy" not in roots and "pandas" not in roots


def test_module_lives_outside_eager_us_runtime_initialization() -> None:
    location = Path(period.__file__)
    assert location.parent.name == "build"
    assert "us_runtime" not in location.parts

    # It also loads standalone, straight from the file, with no package import.
    spec = importlib.util.spec_from_file_location("_puf_period_standalone", location)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        assert module.STATISTICAL_REFERENCE_TAX_YEAR == 2015
        assert module.load_interpretation is not None
    finally:
        sys.modules.pop(spec.name, None)
    assert "microcosm.build.us_runtime" not in sys.modules


# ---------------------------------------------------------------------------
# The packaged resource
# ---------------------------------------------------------------------------


def test_packaged_resource_states_the_adjudicated_period() -> None:
    interpretation = load_packaged_interpretation()
    assert interpretation.statistical_reference_tax_year == 2015
    assert interpretation.processing_calendar_year == 2016
    assert interpretation.preserved_period_fields == ("FLPDYR", "FLPDMO")
    assert interpretation.delivered_flpdyr_domain == (2012, 2013, 2014, 2015)
    assert interpretation.delivered_flpdmo_domain == (12,)
    assert interpretation.national_only is True
    assert interpretation.documentary_pins_status == "declared"
    assert interpretation.convention.convention_status == "proposed"
    assert interpretation.convention.convention_review is None
    assert interpretation.convention.growth_admitted is False


def test_packaged_resource_preserves_the_predecessor_raw_definition() -> None:
    binding = load_packaged_interpretation().raw_source_binding
    assert binding.definition_schema == "microcosm.us.puf_2015_raw_source_definition"
    assert binding.preserved_period_semantics == "unresolved_raw_FLPDYR"
    assert binding.retroactive_mutation is False
    assert binding.imports_predecessor_module is False


def test_packaged_resource_pins_both_editions_and_their_page_locators() -> None:
    interpretation = load_packaged_interpretation()
    assert {pin.document_id for pin in interpretation.documents} == {
        "main-2022",
        "main-2023",
    }
    for pin in interpretation.documents:
        assert pin.retained_text.segment_count == 88
        assert {locator.pdf_page for locator in pin.pages} == {3, 4, 28, 29, 30, 40, 14}
        for locator in pin.pages:
            assert 1 <= locator.pdf_page <= pin.retained_text.segment_count
            assert locator.printed_page == locator.pdf_page - 1

    # The code-page discrepancy and the page-40 tabulation agree across editions;
    # the two cited wording pages do not, and the resource says so.
    by_edition = {pin.document_id: pin for pin in interpretation.documents}
    for page in (14, 28, 29, 30, 40):
        assert (
            by_edition["main-2022"].page(page).text_sha256
            == by_edition["main-2023"].page(page).text_sha256
        )
        assert by_edition["main-2022"].page(page).cross_edition_text_identical is True
    for page in (3, 4):
        assert (
            by_edition["main-2022"].page(page).text_sha256
            != by_edition["main-2023"].page(page).text_sha256
        )
        assert by_edition["main-2022"].page(page).cross_edition_text_identical is False


def test_packaged_resource_records_the_unresolved_code_page_discrepancy() -> None:
    record = load_packaged_interpretation().payload["disagreement_record"][
        "code_page_printed_domain"
    ]
    assert "2011-2014" in record["printed_text"]
    assert tuple(record["delivered_domain"]) == (2012, 2013, 2014, 2015)
    assert record["status"] == "unresolved_and_recorded_verbatim"
    assert record["corrected"] is False


def test_packaged_resource_validates_against_the_packaged_json_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(json.dumps(period._plain(package_schema())))
    resource = json.loads(package_resource_bytes().decode("utf-8"))
    validator = jsonschema.validators.validator_for(schema)
    validator.check_schema(schema)
    jsonschema.validate(resource, schema, cls=validator)


def test_canonical_hash_is_deterministic_and_content_sensitive(payload) -> None:
    first = canonical_resource_sha256(payload)
    assert first == canonical_resource_sha256(copy.deepcopy(payload))
    changed = copy.deepcopy(payload)
    changed["interpretation_id"] = "invented_interpretation.v1 "
    assert canonical_resource_sha256(changed) != first


# ---------------------------------------------------------------------------
# Reported periods: invented 2012-2015 rows stay exactly as delivered
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("year", [2012, 2013, 2014, 2015])
def test_invented_reported_years_are_preserved_while_the_reference_stays_2015(
    payload, year
) -> None:
    interpretation = load_interpretation(payload)
    annotation = annotate_reported_period(interpretation, flpdyr=year, flpdmo=12)
    assert annotation.raw_flpdyr == year
    assert annotation.raw_flpdmo == 12
    assert annotation.statistical_reference_tax_year == 2015
    assert annotation.processing_calendar_year == 2016
    assert annotation.period_semantics == "unresolved_raw_FLPDYR"
    assert annotation.within_delivered_flpdyr_domain is True
    assert annotation.growth_admitted is False


def test_out_of_domain_and_non_integer_tokens_are_echoed_not_coerced(payload) -> None:
    interpretation = load_interpretation(payload)
    token = "2015"
    annotation = annotate_reported_period(interpretation, flpdyr=token, flpdmo=None)
    assert annotation.raw_flpdyr is token
    assert annotation.raw_flpdmo is None
    assert annotation.within_delivered_flpdyr_domain is False
    assert annotation.statistical_reference_tax_year == 2015

    older = annotate_reported_period(interpretation, flpdyr=2011, flpdmo=12)
    assert older.raw_flpdyr == 2011
    assert older.within_delivered_flpdyr_domain is False


def test_automatic_row_year_repair_is_refused(payload) -> None:
    interpretation = load_interpretation(payload)
    with pytest.raises(AuthorityRefusedError) as error:
        annotate_reported_period(
            interpretation, flpdyr=2012, flpdmo=12, repair_to_statistical_reference=True
        )
    assert error.value.use == "period_repair"


def test_graph_annotations_keep_the_proposal_apart_from_documentary_fact(
    payload,
) -> None:
    annotations = graph_annotations(load_interpretation(payload))
    assert (
        annotations["statistical_reference_tax_year"]["basis"] == "publisher_documented"
    )
    assert annotations["processing_calendar_year"]["basis"] == "publisher_documented"
    assert annotations["national_only"]["basis"] == "publisher_documented"
    assert annotations["reported_period_semantics"]["basis"] == "delivered_source"
    assert annotations["modeling_convention"]["basis"] == "proposed_modeling_convention"
    assert annotations["modeling_convention"]["convention_status"] == "proposed"
    assert annotations["modeling_convention"]["convention_review"] is None
    assert annotations["modeling_convention"]["growth_admitted"] is False


# ---------------------------------------------------------------------------
# The declared page-text hash method, on synthetic multi-page text
# ---------------------------------------------------------------------------


def test_page_text_hash_matches_an_independent_recomputation() -> None:
    pages = synthetic_pages()
    container = synthetic_container(pages)
    for number in range(1, SYNTHETIC_PAGE_COUNT + 1):
        computed = page_text_sha256(
            container,
            expected_container_sha256=sha256(container),
            pdf_page=number,
            expected_segment_count=SYNTHETIC_PAGE_COUNT,
        )
        expected = hashlib.sha256(pages[number - 1].encode("utf-8")).hexdigest()
        assert computed == expected


@pytest.mark.parametrize(
    ("description", "mutate"),
    [
        ("one space removed", lambda page: page.replace("  section", " section", 1)),
        (
            "trailing space removed",
            lambda page: page.replace("BOOKLET \n", "BOOKLET\n", 1),
        ),
        (
            "header renamed",
            lambda page: page.replace("INVENTED BOOKLET", "INVENTED BOOK", 1),
        ),
        ("footer renamed", lambda page: page.replace("footer", "footnote", 1)),
        ("newline removed", lambda page: page.replace("\n\n", "\n", 1)),
    ],
)
def test_whitespace_header_and_footer_changes_change_the_page_hash(
    description, mutate
) -> None:
    pages = synthetic_pages()
    original = page_text_sha256(
        synthetic_container(pages),
        expected_container_sha256=sha256(synthetic_container(pages)),
        pdf_page=3,
        expected_segment_count=SYNTHETIC_PAGE_COUNT,
    )
    mutated_pages = list(pages)
    mutated_pages[2] = mutate(mutated_pages[2])
    assert mutated_pages[2] != pages[2], description
    mutated = synthetic_container(mutated_pages)
    assert (
        page_text_sha256(
            mutated,
            expected_container_sha256=sha256(mutated),
            pdf_page=3,
            expected_segment_count=SYNTHETIC_PAGE_COUNT,
        )
        != original
    ), description


def test_a_change_on_any_other_page_fails_container_authentication_first() -> None:
    pages = synthetic_pages()
    declared = sha256(synthetic_container(pages))
    mutated_pages = list(pages)
    mutated_pages[5] = mutated_pages[5].replace("body", "BODY", 1)
    with pytest.raises(PageTextHashError) as error:
        page_text_sha256(
            synthetic_container(mutated_pages),
            expected_container_sha256=declared,
            pdf_page=3,
            expected_segment_count=SYNTHETIC_PAGE_COUNT,
        )
    assert error.value.reason == "container_hash_mismatch"


@pytest.mark.parametrize(
    ("locator", "reason"),
    [
        (0, "locator_out_of_range"),
        (-1, "locator_out_of_range"),
        (SYNTHETIC_PAGE_COUNT + 1, "locator_out_of_range"),
        (True, "locator_is_boolean"),
        (False, "locator_is_boolean"),
        (3.0, "locator_not_integer"),
        ("3", "locator_not_integer"),
        (None, "locator_not_integer"),
    ],
)
def test_locator_validation_refuses_bad_page_numbers(locator, reason) -> None:
    container = synthetic_container()
    with pytest.raises(PageTextHashError) as error:
        page_text_sha256(
            container,
            expected_container_sha256=sha256(container),
            pdf_page=locator,
            expected_segment_count=SYNTHETIC_PAGE_COUNT,
        )
    assert error.value.reason == reason


def test_segment_count_mismatch_is_refused() -> None:
    container = synthetic_container()
    with pytest.raises(PageTextHashError) as error:
        page_text_sha256(
            container,
            expected_container_sha256=sha256(container),
            pdf_page=3,
            expected_segment_count=SYNTHETIC_PAGE_COUNT + 1,
        )
    assert error.value.reason == "segment_count_mismatch"


@pytest.mark.parametrize(
    ("declared", "reason"),
    [
        (0, "declared_segment_count_not_positive"),
        (-3, "declared_segment_count_not_positive"),
        (True, "declared_segment_count_not_integer"),
        (6.0, "declared_segment_count_not_integer"),
    ],
)
def test_declared_segment_count_must_be_a_positive_integer(declared, reason) -> None:
    container = synthetic_container()
    with pytest.raises(PageTextHashError) as error:
        page_text_sha256(
            container,
            expected_container_sha256=sha256(container),
            pdf_page=3,
            expected_segment_count=declared,
        )
    assert error.value.reason == reason


def test_an_empty_selected_segment_is_refused() -> None:
    pages = synthetic_pages()
    pages[2] = ""
    container = synthetic_container(pages)
    with pytest.raises(PageTextHashError) as error:
        page_text_sha256(
            container,
            expected_container_sha256=sha256(container),
            pdf_page=3,
            expected_segment_count=SYNTHETIC_PAGE_COUNT,
        )
    assert error.value.reason == "empty_page_segment"
    # A non-empty page of the same container still hashes.
    assert page_text_sha256(
        container,
        expected_container_sha256=sha256(container),
        pdf_page=2,
        expected_segment_count=SYNTHETIC_PAGE_COUNT,
    )


def test_the_method_never_freshly_extracts_or_normalizes(payload) -> None:
    method = load_interpretation(payload).payload["page_text_hash_method"]
    assert method["fresh_pdf_extraction"] is False
    assert method["append_separator"] is False
    file_method = load_interpretation(payload).payload[
        "document_and_render_hash_method"
    ]
    assert file_method["normalization"] is None
    assert file_method["pixel_hash"] is False
    assert file_method["bit_identical_render_regeneration_claimed"] is False


# ---------------------------------------------------------------------------
# Documentary verification is computed from resolved bytes
# ---------------------------------------------------------------------------


def test_verification_passes_only_on_the_exact_bytes(payload, resolver_bytes) -> None:
    interpretation = load_interpretation(payload)
    verification = verify_documentary_pins(
        interpretation, resolver_from(resolver_bytes)
    )
    assert verification.verified is True
    assert verification.status == "verified"
    assert verification.failures == ()
    # Every declared page was recomputed, not taken on trust.
    assert sum(1 for check in verification.checks if check.kind == "page_text") == 3


@pytest.mark.parametrize(
    ("logical_id", "replacement", "reason"),
    [
        ("invented-doc", b"%PDF-1.7 invented main documenT\n", "hash_mismatch"),
        ("invented-render", b"\x89PNG\r\n\x1a\n invented rendeR\n", "hash_mismatch"),
        ("invented-doc", b"", "empty_bytes"),
        ("invented-render", b"short", "byte_length_mismatch"),
        ("invented-doc", "not bytes", "resolver_returned_non_bytes"),
    ],
)
def test_mutated_or_wrong_bytes_leave_verification_unverified(
    payload, resolver_bytes, logical_id, replacement, reason
) -> None:
    interpretation = load_interpretation(payload)
    corrupted = dict(resolver_bytes)
    corrupted[logical_id] = replacement
    verification = verify_documentary_pins(interpretation, resolver_from(corrupted))
    assert verification.verified is False
    assert reason in verification.reasons
    assert growth_admission(documentary_verification=verification).admitted is False


def test_a_mutated_page_inside_an_authentic_looking_container_is_caught(
    payload, resolver_bytes
) -> None:
    """The container hash moves with the page, so both checks refuse."""
    pages = synthetic_pages()
    pages[2] = pages[2].replace("body", "BODY", 1)
    corrupted = dict(resolver_bytes)
    corrupted["invented-doc-text"] = synthetic_container(pages)
    verification = verify_documentary_pins(
        load_interpretation(payload), resolver_from(corrupted)
    )
    assert verification.verified is False
    assert "hash_mismatch" in verification.reasons
    assert "container_unavailable" in verification.reasons


def test_absent_resolver_bytes_leave_verification_unverified_and_refuse_growth(
    payload,
) -> None:
    interpretation = load_interpretation(payload)
    verification = verify_documentary_pins(interpretation, lambda logical_id: None)
    assert verification.verified is False
    assert "unresolved_bytes" in verification.reasons

    display = documentary_display(interpretation, verification)
    assert display["documentary_pins_verified"] is False
    assert display["provenance_authenticated"] is False
    assert display["documentary_pins_status"] == "declared"
    assert display["growth_admitted"] is False

    with pytest.raises(GrowthRefusedError):
        refuse_growth(
            convention_status=interpretation.convention.convention_status,
            convention_review=interpretation.convention.convention_review,
            documentary_verification=verification,
        )


def test_a_display_without_any_verification_is_explicitly_unverified(payload) -> None:
    display = documentary_display(load_interpretation(payload))
    assert display["documentary_pins_verified"] is False
    assert display["provenance_authenticated"] is False
    assert display["unverified_reasons"] == ()


def test_an_empty_verification_is_not_verified() -> None:
    assert DocumentaryVerification(checks=()).verified is False


# ---------------------------------------------------------------------------
# A serialized verification flag can never reach a caller
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "place",
    [
        "top_level",
        "inside_documentary_pins",
        "nested_in_a_document",
        "as_pins_verified",
    ],
)
def test_a_forged_documentary_pins_verified_flag_is_refused(payload, place) -> None:
    forged = copy.deepcopy(payload)
    if place == "top_level":
        forged["documentary_pins_verified"] = True
    elif place == "inside_documentary_pins":
        forged["documentary_pins"]["verified"] = True
    elif place == "nested_in_a_document":
        forged["documents"][0]["documentary_pins_verified"] = True
    else:
        forged["pins_verified"] = True
    with pytest.raises(ResourceValidationError) as error:
        load_interpretation(forged)
    assert error.value.reason in {
        "serialized_verification_flag",
        "unknown_top_level_key",
    }


def test_self_asserted_provenance_cannot_grant_growth_or_authentication(
    payload,
) -> None:
    """Well-formed self-supplied hashes prove nothing without resolvable bytes."""
    interpretation = load_interpretation(payload)
    verification = verify_documentary_pins(interpretation, lambda logical_id: None)
    admission = growth_admission(
        convention_status="proposed",
        convention_review=None,
        documentary_verification=verification,
    )
    assert admission.admitted is False
    assert "documentary_pins_unverified" in admission.reasons
    assert (
        documentary_display(interpretation, verification)["provenance_authenticated"]
        is False
    )


# ---------------------------------------------------------------------------
# The shared growth-refusal guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "expected_class"),
    [
        ("proposed", "proposed"),
        (None, "missing"),
        ("", "missing"),
        ("   ", "missing"),
        ("unknown", "unknown"),
        ("draft", "unknown"),
        (42, "unknown"),
        ("reviewed", "claimed_reviewed"),
        ("reviewed_modeling_convention", "claimed_reviewed"),
        ("APPROVED", "claimed_reviewed"),
        ("accepted_by_root", "claimed_reviewed"),
    ],
)
def test_every_convention_state_refuses_growth(status, expected_class) -> None:
    assert classify_convention_status(status) == expected_class
    admission = growth_admission(convention_status=status)
    assert admission.admitted is False
    assert admission.convention_class == expected_class
    assert period.GROWTH_REFUSED_UNCONDITIONALLY in admission.reasons
    assert period.NO_POSITIVE_ADMISSION_PATH in admission.reasons
    with pytest.raises(GrowthRefusedError) as error:
        refuse_growth(convention_status=status)
    assert error.value.admission.admitted is False


def test_growth_is_refused_even_with_verified_pins_and_a_claimed_review(
    payload, resolver_bytes
) -> None:
    interpretation = load_interpretation(payload)
    verification = verify_documentary_pins(
        interpretation, resolver_from(resolver_bytes)
    )
    assert verification.verified is True
    admission = growth_admission(
        convention_status="reviewed_modeling_convention",
        convention_review={
            "reviewer": "invented",
            "fingerprint": sha256(b"invented well-formed review fingerprint"),
        },
        documentary_verification=verification,
    )
    assert admission.admitted is False
    assert "claimed_convention_review_not_honoured" in admission.reasons
    assert "convention_status_claimed_reviewed_is_invalid" in admission.reasons


def test_double_growth_is_refused_with_synthetic_factor_stubs() -> None:
    admission = growth_admission(
        convention_status="proposed",
        already_applied_factors=("invented_row_price_factor", "invented_cpi_stub"),
    )
    assert admission.admitted is False
    assert "double_growth_would_compound" in admission.reasons


def test_no_input_combination_admits_growth(payload, resolver_bytes) -> None:
    interpretation = load_interpretation(payload)
    verified = verify_documentary_pins(interpretation, resolver_from(resolver_bytes))
    unverified = verify_documentary_pins(interpretation, lambda logical_id: None)
    for status in (
        "proposed",
        "reviewed",
        "reviewed_modeling_convention",
        "unknown",
        None,
    ):
        for review in (None, {"fingerprint": sha256(b"invented")}, "signed"):
            for verification in (None, verified, unverified):
                for factors in ((), ("invented_stub",)):
                    admission = growth_admission(
                        convention_status=status,
                        convention_review=review,
                        documentary_verification=verification,
                        already_applied_factors=factors,
                    )
                    assert admission.admitted is False


def test_growth_admission_cannot_be_flipped_by_a_caller() -> None:
    admission = growth_admission(convention_status="proposed")
    with pytest.raises((AttributeError, TypeError)):
        admission.admitted = True  # type: ignore[misc]
    assert admission.admitted is False


# ---------------------------------------------------------------------------
# Authority refusals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "use",
    [
        "tax_law",
        "congressional_district_estimation",
        "calibration",
        "release_admission",
        "scientific_admission",
        "factor_generation",
    ],
)
def test_non_documentary_authority_is_refused(use) -> None:
    assert grants_authority(use) is False
    with pytest.raises(AuthorityRefusedError) as error:
        require_authority(use)
    assert error.value.use == use


def test_the_packaged_resource_grants_nothing() -> None:
    grants = load_packaged_interpretation().payload["grants"]
    assert set(grants) == {
        "growth_authority",
        "scientific_admission",
        "release_admission",
        "tax_law_authority",
        "district_estimation_authority",
        "calibration_authority",
    }
    assert all(value is False for value in grants.values())


# ---------------------------------------------------------------------------
# Resource validation refusals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda body: body.__setitem__("schema", "other"), "unknown_schema"),
        (
            lambda body: body.__setitem__("schema_version", 2),
            "unsupported_schema_version",
        ),
        (
            lambda body: body.__setitem__("authority", "growth"),
            "authority_must_be_documentary_only",
        ),
        (lambda body: body.__setitem__("invented_extra", 1), "unknown_top_level_key"),
        (lambda body: body.pop("convention"), "missing_top_level_key"),
        (
            lambda body: body["convention"].__setitem__(
                "convention_status", "reviewed_modeling_convention"
            ),
            "convention_status_claimed_reviewed",
        ),
        (
            lambda body: body["convention"].__setitem__("convention_status", "unknown"),
            "convention_status_unknown",
        ),
        (
            lambda body: body["convention"].pop("convention_status"),
            "convention_status_missing",
        ),
        (
            lambda body: body["convention"].pop("convention_review"),
            "convention_review_missing",
        ),
        (
            lambda body: body["convention"].__setitem__(
                "convention_review", {"reviewer": "invented"}
            ),
            "convention_review_claimed",
        ),
        (
            lambda body: body["convention"].__setitem__("growth_admitted", True),
            "growth_admitted_must_be_false",
        ),
        (
            lambda body: body["convention"].__setitem__("convention_id", "  "),
            "convention_id_ambiguous",
        ),
        (
            lambda body: body["convention"].__setitem__("convention_id", None),
            "convention_id_ambiguous",
        ),
        (
            lambda body: body["growth_contract"].__setitem__(
                "first_revision_refuses_all_growth", False
            ),
            "growth_contract_must_refuse_all_growth",
        ),
        (
            lambda body: body["growth_contract"].__setitem__(
                "accepted_convention_status", ["proposed", "reviewed"]
            ),
            "growth_contract_accepts_more_than_a_proposal",
        ),
        (
            lambda body: body["future_positive_admission"].__setitem__(
                "review_fingerprint_mechanism_defined", True
            ),
            "future_admission_path_must_not_be_claimed",
        ),
        (
            lambda body: body["grants"].__setitem__("growth_authority", True),
            "granted_authority_not_permitted",
        ),
        (
            lambda body: body["documentary_pins"].__setitem__("status", "verified"),
            "documentary_pins_must_start_declared",
        ),
        (
            lambda body: body["documentary_pins"].__setitem__(
                "silent_fresh_extraction_repair", True
            ),
            "fresh_extraction_repair_not_permitted",
        ),
        (
            lambda body: body["statistical_reference_period"].__setitem__(
                "tax_year", 2016
            ),
            "statistical_reference_year_unexpected",
        ),
        (
            lambda body: body["statistical_reference_period"].__setitem__(
                "basis", "modeling_choice"
            ),
            "statistical_reference_basis_must_be_publisher_documented",
        ),
        (
            lambda body: body["processing_window"].__setitem__("calendar_year", 2015),
            "processing_window_unexpected",
        ),
        (
            lambda body: body["reported_period_preservation"].__setitem__(
                "automatic_row_year_repair", True
            ),
            "row_year_repair_not_permitted",
        ),
        (
            lambda body: body["reported_period_preservation"].__setitem__(
                "inference_from_statistical_reference_period", True
            ),
            "reported_period_must_not_be_inferred",
        ),
        (
            lambda body: body["reported_period_preservation"].__setitem__(
                "fields", ["FLPDYR"]
            ),
            "preserved_period_fields_unexpected",
        ),
        (
            lambda body: body["geographic_meaning"].__setitem__("national_only", False),
            "national_only_meaning_required",
        ),
        (
            lambda body: body["raw_source_binding"].__setitem__(
                "preserved_period_semantics", "resolved_2015"
            ),
            "predecessor_period_semantics_must_be_preserved",
        ),
        (
            lambda body: body["raw_source_binding"].__setitem__(
                "retroactive_mutation", True
            ),
            "retroactive_mutation_not_permitted",
        ),
        (
            lambda body: body["raw_source_binding"].__setitem__(
                "imports_predecessor_module", True
            ),
            "predecessor_must_be_bound_by_identity_not_import",
        ),
        (
            lambda body: body["raw_source_binding"].__setitem__(
                "definition_sha256", "not-a-hash"
            ),
            "raw_source_binding_hash_malformed",
        ),
        (
            lambda body: body["page_text_hash_method"].__setitem__(
                "fresh_pdf_extraction", True
            ),
            "fresh_extraction_repair_not_permitted",
        ),
        (
            lambda body: body["page_text_hash_method"].__setitem__("id", "invented.v9"),
            "page_text_hash_method_unknown",
        ),
        (
            lambda body: body["document_and_render_hash_method"].__setitem__(
                "pixel_hash", True
            ),
            "render_pin_must_not_claim_a_pixel_hash",
        ),
        (
            lambda body: body["document_and_render_hash_method"].__setitem__(
                "bit_identical_render_regeneration_claimed", True
            ),
            "render_pin_must_not_claim_bit_identical_regeneration",
        ),
        (
            lambda body: body["documents"][0]["pdf"].__setitem__("sha256", "abc"),
            "pdf_sha256_malformed",
        ),
        (
            lambda body: body["documents"][0]["retained_text"].__setitem__(
                "segment_count", 0
            ),
            "segment_count_invalid",
        ),
        (
            lambda body: body["documents"][0]["pages"][0].__setitem__("pdf_page", True),
            "locator_is_boolean",
        ),
        (
            lambda body: body["documents"][0]["pages"][0].__setitem__("pdf_page", 99),
            "locator_out_of_range",
        ),
        (
            lambda body: body["documents"][0]["pages"][0].__setitem__("pdf_page", 0),
            "locator_out_of_range",
        ),
        (
            lambda body: body["documents"][0]["pages"][0].__setitem__(
                "text_sha256", "deadbeef"
            ),
            "page_text_sha256_malformed",
        ),
        (
            lambda body: body["documents"][0].__setitem__("role", "invented"),
            "document_role_must_be_primary_public",
        ),
        (
            lambda body: body["renders"][0].__setitem__("document_id", "missing-doc"),
            "render_document_unknown",
        ),
        (
            lambda body: body["deferred_required_work"][0].__setitem__(
                "implemented", True
            ),
            "deferred_work_must_not_be_claimed_here",
        ),
        (
            lambda body: body["non_claims"].__setitem__(
                "growth_factor_admission", True
            ),
            "non_claim_must_be_false",
        ),
    ],
)
def test_resource_validation_refusals(payload, mutate, reason) -> None:
    broken = copy.deepcopy(payload)
    mutate(broken)
    with pytest.raises(ResourceValidationError) as error:
        load_interpretation(broken)
    assert error.value.reason == reason


def test_duplicate_logical_identifiers_are_refused(payload) -> None:
    broken = copy.deepcopy(payload)
    broken["documents"].append(copy.deepcopy(broken["documents"][0]))
    with pytest.raises(ResourceValidationError) as error:
        load_interpretation(broken)
    assert error.value.reason == "duplicate_document_id"


def test_duplicate_page_locators_are_refused(payload) -> None:
    broken = copy.deepcopy(payload)
    broken["documents"][0]["pages"].append(
        copy.deepcopy(broken["documents"][0]["pages"][0])
    )
    with pytest.raises(ResourceValidationError) as error:
        load_interpretation(broken)
    assert error.value.reason == "duplicate_pdf_page"


def test_a_validated_resource_cannot_be_mutated_in_place(payload) -> None:
    interpretation = load_interpretation(payload)
    with pytest.raises(TypeError):
        interpretation.payload["schema"] = "other"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Page 40: exact integer documentary reconciliation
# ---------------------------------------------------------------------------


def test_packaged_page40_integers_reconcile_exactly() -> None:
    table = load_packaged_interpretation().page40
    positives = [value for value in table["FLPDYR"].values() if value > 0]
    assert sum(positives) == table["positive_period_displayed_sum"] == 150827846
    assert table["FLPDMO_12_displayed"] == 150827847
    assert table["displayed_total_discrepancy"]["value"] == 1
    assert (
        table["FLPDMO_12_displayed"] - table["positive_period_displayed_sum"]
        == table["displayed_total_discrepancy"]["value"]
    )
    aggregates = table["aggregate_records"]
    assert sum(aggregates["FDED_public_counts"]) == aggregates["FDED_displayed_total"]
    assert aggregates["FDED_displayed_total"] == table["FLPDMO_12_displayed"]
    assert aggregates["FDED_0_weighted_public_count"] == 1233
    assert aggregates["sampled_returns_before_aggregation"] == 1124


def test_packaged_page40_leaves_the_blank_cell_and_operator_unstated() -> None:
    table = load_packaged_interpretation().page40
    assert table["FLPDMO_less_than_12_displayed"] is None
    assert table["rounding_operator"] is None
    assert table["displayed_total_discrepancy"]["proves"] is None
    assert table["is_a_calibration_objective"] is False
    assert table["column"] == "2015 Public Use Sample"


def test_published_counts_scale_to_hundredths_in_exact_integer_arithmetic() -> None:
    """The later audit's declared unit conversion, checked as pure arithmetic."""
    table = load_packaged_interpretation().page40
    assert table["comparison_units"]["delivered_S006"].startswith("int64 hundredths")
    for value in table["FLPDYR"].values():
        scaled = value * 100
        assert isinstance(scaled, int)
        assert scaled // 100 == value


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (
            lambda table: table.__setitem__("FLPDMO_less_than_12_displayed", 0),
            "blank_cell_must_not_be_quoted_as_zero",
        ),
        (
            lambda table: table.__setitem__("rounding_operator", "round_half_up"),
            "rounding_operator_must_stay_unestablished",
        ),
        (
            lambda table: table.__setitem__("positive_period_displayed_sum", 99),
            "positive_period_sum_mismatch",
        ),
        (
            lambda table: table["displayed_total_discrepancy"].__setitem__("value", 0),
            "displayed_gap_mismatch",
        ),
        (
            lambda table: table["displayed_total_discrepancy"].__setitem__(
                "proves", "round_half_even"
            ),
            "displayed_gap_must_not_prove_a_rounding_operator",
        ),
        (
            lambda table: table["aggregate_records"].__setitem__(
                "FDED_public_counts", [1233, 50, 51, 1]
            ),
            "fded_column_sum_mismatch",
        ),
        (
            lambda table: table["aggregate_records"].__setitem__(
                "represented_population_returns", 1124
            ),
            "represented_population_count_unexpected",
        ),
        (
            lambda table: table.__setitem__("is_a_calibration_objective", True),
            "page40_must_not_be_a_calibration_objective",
        ),
        (
            lambda table: table.__setitem__(
                "column", "2015 Full SOI Individual Sample"
            ),
            "page40_column_must_be_the_public_use_sample",
        ),
    ],
)
def test_page40_documentary_refusals(payload, mutate, reason) -> None:
    broken = copy.deepcopy(payload)
    mutate(broken["page40_weighted_tabulation"])
    with pytest.raises(ResourceValidationError) as error:
        load_interpretation(broken)
    assert error.value.reason == reason


def test_the_full_soi_column_is_never_the_reconciliation_target() -> None:
    table = load_packaged_interpretation().page40
    assert (
        "substitute the full SOI Individual Sample column as the PUF reconciliation target"
        in list(table["must_not"])
    )


def test_a_page_pin_that_disagrees_with_an_authentic_container_is_caught(
    payload, resolver_bytes
) -> None:
    """The container authenticates; one page pin points at another page's hash."""
    broken = copy.deepcopy(payload)
    pages = broken["documents"][0]["pages"]
    pages[0]["text_sha256"], pages[2]["text_sha256"] = (
        pages[2]["text_sha256"],
        pages[0]["text_sha256"],
    )
    verification = verify_documentary_pins(
        load_interpretation(broken), resolver_from(resolver_bytes)
    )
    assert verification.verified is False
    assert verification.reasons == ("hash_mismatch",)
    container_checks = [
        check for check in verification.checks if check.kind == "retained_text"
    ]
    assert all(check.ok for check in container_checks)
    failed_pages = {check.logical_id for check in verification.failures}
    assert failed_pages == {"invented-doc-text#2", "invented-doc-text#5"}


def test_packaged_resource_records_every_page4_disclosure_treatment() -> None:
    block = load_packaged_interpretation().payload["publisher_disclosure_avoidance"]
    identifiers = {treatment["id"] for treatment in block["treatments"]}
    assert {
        "fiscal_period_conversion",
        "extreme_value_aggregation",
        "multivariate_blurring",
    } <= identifiers
    assert block["basis"] == "publisher_documented"
    assert block["pdf_page"] == 4 and block["printed_page"] == 3
    assert "blurring" in block["later_audit_obligation"]
    blurring = next(
        treatment
        for treatment in block["treatments"]
        if treatment["id"] == "multivariate_blurring"
    )
    assert "wages and salaries" in blurring["publisher_statement"]


def test_the_deferred_audit_must_state_blurring_treatment() -> None:
    audit = next(
        row
        for row in load_packaged_interpretation().payload["deferred_required_work"]
        if row["id"] == "source_period_audit"
    )
    assert "blurring" in audit["description"]
    assert "aggregate-record treatment" in audit["description"]
    assert audit["implemented"] is False


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (
            lambda body: body["publisher_disclosure_avoidance"]["treatments"].pop(2),
            "disclosure_treatment_missing",
        ),
        (
            lambda body: body["publisher_disclosure_avoidance"].__setitem__(
                "later_audit_obligation", "State aggregate-record treatment."
            ),
            "later_audit_must_state_blurring_treatment",
        ),
        (
            lambda body: body["publisher_disclosure_avoidance"].__setitem__(
                "basis", "modeling_choice"
            ),
            "disclosure_avoidance_basis_must_be_publisher_documented",
        ),
        (
            lambda body: body["convention"].__setitem__(
                "review_record", {"reviewer": "invented"}
            ),
            "unknown_convention_key",
        ),
    ],
)
def test_disclosure_and_convention_refusals(payload, mutate, reason) -> None:
    broken = copy.deepcopy(payload)
    mutate(broken)
    with pytest.raises(ResourceValidationError) as error:
        load_interpretation(broken)
    assert error.value.reason == reason


def test_the_packaged_prior_url_receipt_attests_the_2022_document() -> None:
    interpretation = load_packaged_interpretation()
    reference = next(
        row
        for row in interpretation.payload["public_references"]
        if "prior_url_match_receipt" in row
    )
    receipt = reference["prior_url_match_receipt"]
    document = interpretation.document(receipt["attests_document_id"])
    assert receipt["attests_sha256"] == document.pdf_sha256
    assert receipt["attests_bytes"] == document.pdf_bytes
    assert len(receipt["sha256"]) == 64


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        (
            "attests_sha256",
            "0" * 64,
            "receipt_attestation_does_not_match_the_document_pin",
        ),
        ("attests_bytes", 1, "receipt_attestation_does_not_match_the_document_pin"),
        ("attests_document_id", "no-such-doc", "receipt_attests_unknown_document"),
        ("sha256", "short", "receipt_sha256_malformed"),
    ],
)
def test_a_prior_receipt_that_attests_the_wrong_bytes_is_refused(
    payload, field, value, reason
) -> None:
    broken = copy.deepcopy(payload)
    broken["public_references"] = [
        {
            "id": "invented-archive-copy",
            "prior_url_match_receipt": {
                "receipt_id": "invented-receipt",
                "sha256": sha256(b"invented url receipt"),
                "bytes": 20,
                "attests_document_id": "invented-doc",
                "attests_sha256": broken["documents"][0]["pdf"]["sha256"],
                "attests_bytes": broken["documents"][0]["pdf"]["bytes"],
            },
        }
    ]
    broken["public_references"][0]["prior_url_match_receipt"][field] = value
    with pytest.raises(ResourceValidationError) as error:
        load_interpretation(broken)
    assert error.value.reason == reason


# ---------------------------------------------------------------------------
# Nothing genuine is loaded
# ---------------------------------------------------------------------------


def test_no_rules_engine_is_imported_by_this_suite() -> None:
    assert "policyengine_us" not in sys.modules
    assert "policyengine_uk" not in sys.modules
