"""Invented exact-stream controls for bounded current-money digest batching.

The reference function is copied unchanged (except its name) from a96fc8509,
asec_current_money_source.py SHA9e6ecca118942f7a76a2ef66de22abc082d3e19ca87bca67ca01477958c5b7e2.
These tests do not load source files, native owners, a country engine or models.
"""

import hashlib
from collections import Counter

import numpy as np
import pandas as pd
import pytest

from microcosm.build.us_runtime import asec_current_money_source as source

checkpoint = source.checkpoint
_json = source._json


class RecordingDigest:
    def __init__(self):
        self.chunks = []
        self.hash = hashlib.sha256()

    def update(self, value):
        assert type(value) is bytes
        self.chunks.append(value)
        self.hash.update(value)

    @property
    def stream(self):
        return b"".join(self.chunks)


def _reference_series_digest(digest, series):
    """Use the existing checkpoint's closed scalar vocabulary, one column at a time."""
    spec = checkpoint._series_spec(series, label="authenticated source")
    digest.update(_json(spec))
    extension = series.array
    data, mask = getattr(extension, "_data", None), getattr(extension, "_mask", None)
    if isinstance(data, np.ndarray) and isinstance(mask, np.ndarray):
        for array in (data, mask):
            value = np.ascontiguousarray(array).tobytes()
            digest.update(len(value).to_bytes(8, "little"))
            digest.update(value)
    elif isinstance(series.dtype, np.dtype) and not series.dtype.hasobject:
        value = np.ascontiguousarray(series.to_numpy(copy=False)).tobytes()
        digest.update(len(value).to_bytes(8, "little"))
        digest.update(value)
    else:
        # Repeated literal strings are common in full survey source frames.
        # Cache their exact length-prefixed bytes within this column only; every
        # value is still visited and every later seal rereads the current data.
        # Both entry and payload bounds keep distinct or large strings bounded.
        string_tokens = {}
        token_bytes = 0
        for value in series.to_numpy(dtype=object, copy=False):
            if type(value) is str:
                token = string_tokens.get(value)
                if token is None:
                    encoded = checkpoint._encode_object_scalar(value)
                    token = len(encoded).to_bytes(8, "little") + encoded
                    if len(string_tokens) < 1024 and token_bytes + len(token) <= 262144:
                        string_tokens[value] = token
                        token_bytes += len(token)
                digest.update(token)
                continue
            encoded = checkpoint._encode_object_scalar(value)
            digest.update(len(encoded).to_bytes(8, "little"))
            digest.update(encoded)


def _compare(series):
    expected, actual = RecordingDigest(), RecordingDigest()
    _reference_series_digest(expected, series)
    source._series_digest(actual, series)
    assert actual.stream == expected.stream
    assert actual.hash.digest() == expected.hash.digest()
    return expected, actual


def _object_case(case):
    if case == "ascii":
        return pd.Series(["HEAD", "DEPENDENT", "HEAD"] * 2000, dtype=object)
    if case == "unicode":
        return pd.Series(["", "é", "e\u0301", "\x00", "😀"] * 200, dtype=object)
    if case == "empty":
        return pd.Series([], dtype=object)
    if case == "python_string":
        return pd.Series(["2024", None, "2024", ""] * 100, dtype="string[python]")
    if case == "arrow_string":
        return pd.Series(["2024", None, "2024", ""] * 100, dtype="string[pyarrow]")
    if case == "nan_string":
        return pd.Series(
            ["2024", None, ""], dtype=pd.StringDtype(storage="python", na_value=np.nan)
        )
    if case == "nulls":
        return pd.Series([None, pd.NA, pd.NaT, np.nan], dtype=object)
    if case == "bytes":
        return pd.Series([b"a", b"", b"\x00", None] * 100, dtype=object)
    if case == "boolean":
        return pd.Series([True, np.bool_(False), None] * 100, dtype=object)
    if case == "huge_integer":
        return pd.Series([0, 2**1000, -(2**1000), None], dtype=object)
    if case == "float":
        return pd.Series([0.0, -0.0, np.inf, -np.inf, float("nan"), None], dtype=object)
    if case == "string_subclass":

        class Literal(str):
            pass

        return pd.Series([Literal("same"), "same", Literal("same")], dtype=object)
    raise AssertionError("UNKNOWN_INVENTED_CASE")


@pytest.mark.parametrize(
    "case",
    [
        "ascii",
        "unicode",
        "empty",
        "python_string",
        "arrow_string",
        "nan_string",
        "nulls",
        "bytes",
        "boolean",
        "huge_integer",
        "float",
        "string_subclass",
    ],
)
def test_batched_object_stream_and_sha_match_frozen_reference(case):
    series = _object_case(case)
    before = series.copy(deep=True)
    expected, actual = _compare(series)
    if case == "empty":
        assert actual.chunks == expected.chunks
    pd.testing.assert_series_equal(series, before, check_exact=True)


@pytest.mark.parametrize(
    "dtype",
    [
        "int64",
        "uint64",
        "float64",
        "datetime64[ns]",
        "timedelta64[ns]",
        "boolean",
        "Int64",
        "UInt64",
    ],
)
def test_numeric_and_nullable_branches_keep_identical_update_calls(dtype):
    values = [0, 1, 2]
    if dtype == "boolean":
        values = [True, False, None]
    elif dtype in ("Int64", "UInt64"):
        values = [0, None, 2]
    series = pd.Series(values, dtype=dtype)
    expected, actual = _compare(series)
    assert actual.chunks == expected.chunks


@pytest.mark.parametrize("length", [0, 65526, 65527, 65528, 131063])
def test_buffer_never_exceeds_bound_and_oversized_tokens_bypass_it(monkeypatch, length):
    instances = []

    class CheckedBuffer(bytearray):
        def __init__(self):
            super().__init__()
            self.peak = 0
            instances.append(self)

        def extend(self, value):
            assert len(self) + len(value) <= 65536
            super().extend(value)
            self.peak = max(self.peak, len(self))

    series = pd.Series(["before", "x" * length, "after"] * 2, dtype=object)
    # Only the new local buffer constructor is instrumented; scalar encoding and
    # digest.update still execute the actual implementation on invented values.
    monkeypatch.setattr(source, "bytearray", CheckedBuffer, raising=False)
    _, actual = _compare(series)
    assert len(instances) == 1 and instances[0].peak <= 65536
    oversized = set()
    for value in series:
        encoded = checkpoint._encode_object_scalar(value)
        token = len(encoded).to_bytes(8, "little") + encoded
        if len(token) > 65536:
            oversized.add(token)
    assert all(len(chunk) <= 65536 or chunk in oversized for chunk in actual.chunks)
    assert all(actual.chunks)


def test_complete_tokens_fill_exact_chunks_without_empty_updates():
    series = pd.Series(["a" * 8183] * 16, dtype=object)
    encoded = checkpoint._encode_object_scalar(series.iloc[0])
    token = len(encoded).to_bytes(8, "little") + encoded
    assert len(token) == 8192
    expected, actual = _compare(series)
    assert actual.chunks[0] == expected.chunks[0]
    assert actual.chunks[1:] == [token * 8, token * 8]


@pytest.mark.parametrize("case", ["entry_limit", "payload_limit", "oversized"])
def test_string_cache_limits_and_encoding_call_order_are_unchanged(monkeypatch, case):
    if case == "entry_limit":
        distinct = [f"literal-{i}" for i in range(1025)]
        values = distinct * 2
        expected_calls = 1026
    elif case == "payload_limit":
        # Four exactly 65,536-byte tokens exhaust the 262,144-byte cache.
        distinct = [letter * 65527 for letter in "abcd"] + ["extra"]
        values = distinct * 2
        expected_calls = 6
    else:
        distinct = ["z" * 262136]  # The tagged token is 262,145 bytes.
        values = distinct * 2
        expected_calls = 2
    series = pd.Series(values, dtype=object)
    encode = checkpoint._encode_object_scalar
    calls = []

    def recording_encode(value):
        calls.append(hashlib.sha256(value.encode()).hexdigest())
        return encode(value)

    monkeypatch.setattr(checkpoint, "_encode_object_scalar", recording_encode)
    expected = RecordingDigest()
    _reference_series_digest(expected, series)
    before = tuple(calls)
    calls.clear()
    actual = RecordingDigest()
    source._series_digest(actual, series)
    assert tuple(calls) == before and len(calls) == expected_calls
    assert actual.stream == expected.stream
    assert actual.hash.digest() == expected.hash.digest()
    if case != "oversized":
        assert sorted(Counter(calls).values()) == [1] * (len(distinct) - 1) + [2]


@pytest.mark.parametrize("case", ["category", "timezone", "object", "extension"])
def test_unsupported_dtypes_preserve_refusal_and_digest_prefix(case):
    if case == "category":
        series = pd.Series(["a"], dtype="category")
    elif case == "timezone":
        series = pd.Series(pd.date_range("2024-01-01", periods=1, tz="UTC"))
    elif case == "object":
        series = pd.Series([object()], dtype=object)
    else:
        series = pd.Series([1.0, None], dtype="Float64")
    expected, actual = RecordingDigest(), RecordingDigest()
    with pytest.raises(TypeError) as first:
        _reference_series_digest(expected, series)
    with pytest.raises(TypeError) as second:
        source._series_digest(actual, series)
    assert str(first.value) == str(second.value)
    assert actual.stream == expected.stream == b""


@pytest.mark.parametrize("error", [TypeError, ValueError])
def test_scalar_refusal_flushes_only_prior_complete_tokens(monkeypatch, error):
    encode = checkpoint._encode_object_scalar

    def refusing_encode(value):
        if value == "refuse":
            raise error("INVENTED_SCALAR_REFUSAL")
        return encode(value)

    monkeypatch.setattr(checkpoint, "_encode_object_scalar", refusing_encode)
    series = pd.Series(["before", "same", "same", "refuse", "unvisited"], dtype=object)
    expected, actual = RecordingDigest(), RecordingDigest()
    with pytest.raises(error, match="^INVENTED_SCALAR_REFUSAL$"):
        _reference_series_digest(expected, series)
    with pytest.raises(error, match="^INVENTED_SCALAR_REFUSAL$"):
        source._series_digest(actual, series)
    assert actual.stream == expected.stream
    assert actual.hash.digest() == expected.hash.digest()


def test_later_seals_reread_mutations_order_and_nulls():
    series = pd.Series(["a", "b", "a", None], dtype="string[python]")
    _, original = _compare(series)
    series.iloc[0] = "b"
    assert _compare(series)[1].hash.digest() != original.hash.digest()
    series.iloc[0] = "a"
    assert _compare(series)[1].hash.digest() == original.hash.digest()
    series.iloc[:] = [None, "a", "b", "a"]
    assert _compare(series)[1].hash.digest() != original.hash.digest()
    series.iloc[:] = ["a", "b", "a", ""]
    assert _compare(series)[1].hash.digest() != original.hash.digest()
