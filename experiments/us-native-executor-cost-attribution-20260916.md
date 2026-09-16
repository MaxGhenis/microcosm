# Native graph executor: CPU attribution and scaling law

**Lane question (Max, 2026-09-15):** can the #893 native graph executor build a
full US dataset at all, at what cost, and what has to change for it to build one
in hours rather than days?

**Short answer.** No — not today, and the reason is not CPU. The build refuses
at roughly **96,200–96,900 source households, 6.1% of the US source**, because
the preparation receipt is a single bounded JSON document carrying one record
per household and per person against a 64 MiB limit. I demonstrated that
refusal by feeding the pilot's own preparation document, scaled, through the
repository's own encoder. Below that ceiling the architecture is not
pathological: its population-scaling work measures **43.8 CPU-s per 3,168 cloned
households**, and its dominant exponent is 1 — though one genuinely quadratic
path costs 1.9 CPU-hours at full source, 12% of the build (§6b). What makes every
run expensive regardless of sample size is a **fixed source-ingest tax paid in a
byte-at-a-time Python loop that moves 12.9 MB/s** — a tax a 1/8000 toy build pays
in full.

**Memory is the second constraint, but it binds later than the ceiling does.**
The executor snapshots a full population copy per node and this runner retains
all nineteen — a mechanism read in the code, not inferred. I measured what a
retained snapshot costs (**9.6–9.8 bytes per cell**, flat across a 16× size
range and four repeats)
rather than subtracting two RSS peaks, because that subtraction turns out to be
confounded by 1.85 GiB of ASEC source one run never loaded. On the measurement:
the largest build the payload ceiling permits needs ~**26 GiB**, and a
full-source build ~**300 GiB** (§9).

Worktree `_worktrees/microcosm-exec-profile`, detached at PR #893 head
`2bc6976a8c6fd882e503c9a1411e091e56fe82c4`. Every derived number below
regenerates from `.profile-runs/harness/final_tables.py`, which reads the
receipts and the microbenchmark constants. **That claim is narrower than it
sounds, and an earlier draft overstated it.** `final_tables.py` is 92 lines: it
regenerates §6a's node decomposition, §5's payload ceiling and encode cost, and
§6d's prediction table with its quadratic term and the naive-extrapolation ratio.
It does **not** cover §3's bucket tables, §5's second (allocation) ceiling, §8d's
per-cell table, §9's memory table — that regenerates from
`bench_observer_retention.py` instead — or §10's derived figures. Those come from
the receipts and benches named beside them, and I re-derived each by hand in the
verification pass, which is how most of §8c's corrections were found.

---

## 1. The runs

Authorization: at most three profiled runs, each `ulimit -t 1800` (30 min CPU),
≤16 GB RSS, no retry, no compute children, no engine, no network.

| run | fraction | profiler | source hh | cloned hh | people | wall | CPU | peak RSS (GiB) | outcome |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1/8000 | cProfile | — | — | — | 1,842.4 s | **1,803.3 s** | 1.72 GiB | **KILLED_AT_CPU_CAP** |
| 2 | 1/2000 | cProfile | — | — | — | *invalid (see below)* | **1,803.4 s** | 1.38 GiB | **KILLED_AT_CPU_CAP** |
| 3 | 1/8000 | 5 ms sampler | — | — | — | 935.2 s | **840.6 s** | 6.75 GiB | **PYTEST_EXIT_1 (build refused)** |
| v4 (reference, 2026-09-11, unprofiled) | 1/1000 | none | 1,584 | 3,168 | 6,928 | 5,362.1 s | 5,278.6 s | 8.67 GiB | completed |

**No run produced household or person counts, because none reached the graph.**
Runs 1 and 2 died inside ACS source ingest, at the cap; run 3 got through the
whole ACS side and was refused entering ASEC restoration verification (§3c),
still before the first node. That is itself the lane's central finding, not a
failure of the measurement: §3a proves the ingest phase is identical at every
sample fraction, so a run that dies there has measured the part of the build a
full-source run would also pay — and §3b prices that phase at **798 CPU-s**,
15.1% of the accepted v4 build, on a run that never built a single household.

Run 1's cap line, verbatim:

```
CPU CAP HIT: RLIMIT_CPU soft=1800s reached; SIGXCPU raised at cpu=1803.3s wall=1842.4s
```

Run 2's cap line, verbatim:

```
CPU CAP HIT: RLIMIT_CPU soft=1800s reached; SIGXCPU raised at cpu=1803.4s wall=2354.1s
```

**Run 3 did not hit the cap.** It spent 840.6 CPU-s of its 1,800 s budget
(823.6 user + 17.0 system, children 0.005 s) and stopped because the build
refused — `PREPARATION_ISSUANCE_REFUSED`, §3c — at 930.9 s into the run, 89.9%
CPU-bound, 96,109 samples at an effective 9.73 ms interval. No cap line was
emitted for it; its receipt is `.profile-runs/s8000r/s8000r.metrics.json` and
its refusal record `.profile-runs/s8000r/native-financial-refusal.json`.

The driver installs a SIGXCPU handler (soft 1800 s, hard 1810 s) purely so the
partial profile is written before the kernel kills the process; every partial
profile was captured. Children CPU was 0.0043 s, 0.0047 s and 0.0048 s across
the three runs — no compute children ran. Peak RSS stayed far under the 16 GB
authorization in every run; the RSS watchdog never fired.

**Two measurement hazards, both resolved rather than assumed.**

*Run 2's wall clock, and its bucket seconds, are polluted.* I found run 2's
process in state `T` (stopped) at ~1,370 CPU-s with its CPU counter frozen —
most likely SIGTTOU from the backgrounded shell's process group. The profile
puts the suspension at **~511–551 s (8.5–9.2 minutes)**: run 2's wall−CPU excess
is 2,354.14 − 1,803.41 = 550.73 s, of which run 1's ordinary wall−CPU gap
accounts for 39.1 s, and the `_records` tottime delta that locates it is
+509.2 s. (An earlier draft said "roughly 12 minutes" from an unrecorded
wall-clock impression the profile does not corroborate.) I resumed it with `kill
-CONT` and it continued
normally. A stopped process accrues no CPU, so run 2's **CPU figure and its cap
are unaffected**. But cProfile times with `perf_counter`, i.e. **wall**, not
CPU, so the suspension *is* inside its profile: 2,354.1 s of profiled time
against 1,803.4 CPU-s. Diffing per-function `tottime` between the two runs
locates it exactly — `_records` gained **+509.2 s at bit-for-bit identical call
counts** (5,054,865 in both), which is stopped time attributed to whichever
function held the interpreter, not work. §3a prints run 2 corrected onto its
measured CPU basis and says so.

*Adding two cumulative times.* §3 sums the cumtime of `_inventory` and
`_archive`, which is only legitimate if neither is an ancestor of the other. The
profile's own caller table settles it: `_inventory` is called by
`acs_population_catalogue.py:141(_preflight)`; `_archive` by `_reconstruct`
(`acs_housing_universe_source.py:563`) from
`acs_population_catalogue.py:435(issue_acs_source_catalogue)`. Sibling trees;
the sum stands.

---

## 2. Why there is no three-point log-log fit

The brief asked for cProfile runs at 1/8000, 1/4000 and 1/2000 and a log-log
slope through them. That plan cannot execute on this build, for two compounding
reasons I measured rather than assumed:

1. **The fixed cost exceeds the cap.** The v4 receipt shows 4,605.4 CPU-s inside
   the runner at 1/1000 *unprofiled*, and the dominant part does not shrink with
   the sample fraction (§4). A 1/8000 run has essentially the same fixed cost as
   a 1/1000 one.
2. **cProfile multiplies the dominant phase by 5.05x.** That phase makes one
   Python call per *byte* of source — the worst possible case for a
   deterministic profiler. Measured, not assumed: the same `_records` function
   over a real 209,715,200-byte slab of `psam_pusa.csv` takes **16.222 CPU-s
   unprofiled and 81.935 CPU-s profiled**
   (`.profile-runs/profiler-overhead-bench.json`). So 1,800 profiled CPU-s buys
   only ~357 s of pipeline.

Every fraction therefore dies in the same fixed phase at the same place, and a
log-log fit across them would be a fit through three copies of one number. Runs
1 and 2 do not merely fail to distinguish themselves — §3a shows their ACS
counters are **bit-for-bit identical**, which is the measurement that makes the
whole question well-posed.

**So run 3 was spent on reach instead of on a third fraction.** A statistical
sampler costs ~0 per call, so the same 1,800 CPU-s covers roughly five times as
much pipeline. `.profile-runs/harness/sample_run.py` replaces cProfile with a
daemon thread reading the main thread's stack every 5 ms via
`sys._current_frames()`, accumulating self-function counts, the deepest in-repo
frame, and a 10-second phase timeline. Same harness, same eight thread-env pins,
same RLIMIT_CPU, same SIGXCPU dump, same RSS watchdog. It trades exact call
counts — already measured to the unit by runs 1 and 2 — for the one thing the
deterministic runs could not buy: attribution of the runner time beyond ACS
ingest.

Alongside the runs, I measured the per-cell and per-byte constant of every
mechanism directly, with short microbenchmarks that import the repository's own
functions, and combined them with the per-node wall times the accepted v4 run
already recorded. Those benchmarks run no graph, read no staged source (except
one 200 MB slab for the profiler-overhead A/B) and take seconds; they are listed
in §11 and are not counted against the three-run authorization.

---

## 3. Bucket attribution

**Run 1 (1/8000), profiled total 1,842.4 s.** That total is cProfile's own,
which is **wall** — the run was 97.9% CPU-bound (1,803.3 CPU-s), so the two
differ by 2.1%. Shares below are of the profiled wall total; the bucket families
are the brief's.

| bucket | self | share | calls |
|---|---|---|---|
| **(c) store IO / codecs — ACS source ingest** | **1,297.7 s** | **70.4%** | 6,505,612,377 |
| (d) other — Python builtins driven per byte by that loop | 452.3 s | 24.6% | 8,869,637,843 |
| (d) other — unclassified (zipfile, io, codecs) | 65.5 s | 3.6% | 177,472,416 |
| (c) store IO — stdlib CSV / zip parse | 13.0 s | 0.7% | 24,116,910 |
| (a) identity — canonical JSON | 8.7 s | 0.5% | 14,741,553 |
| (a) identity — sha256 | 5.0 s | 0.3% | 8,737,374 |
| (d) other — pytest and imports | 0.1 s | 0.0% | 213,895 |
| **(b) numpy/pandas/sklearn/torch kernel compute** | **0.0 s** | **0.0%** | 18,126 |
| (a) identity — `_frame_identity` per-cell | 0.0 s | 0.0% | 2,756 |

Rolled up: store IO **1,310.7 s (71.1%)**, other **518.0 s (28.1%)**, identity
**13.7 s (0.7%)**, kernel compute **0.02 s (0.001%)**.

Top of the profile by self time:

| self | cum | ncalls | function |
|---|---|---|---|
| 890.4 s | 1,361.5 s | 5,054,865 | `acs_person_coverage_authentication.py:188(_records)` |
| 168.0 s | 168.0 s | **3,382,952,633** | `bytearray.append` |
| 167.0 s | 167.0 s | **4,424,967,359** | `builtins.len` |
| 160.4 s | 160.4 s | **5,418,945,835** | `acs_person_coverage_authentication.py:60(_require)` |
| 136.2 s | 221.5 s | 980,880,110 | `acs_housing_universe_source.py:257(<genexpr>)` |
| 53.2 s | 53.2 s | 980,888,715 | `str.encode` |
| 50.3 s | 296.9 s | 3,673,585 | `acs_housing_universe_source.py:236(_csv_record)` |
| 16.4 s | 94.4 s | 5,054,861 | `acs_person_coverage_authentication.py:230(_decode_record)` |
| 13.8 s | **1,473.3 s** | **2** | `acs_person_coverage_authentication.py:278(_inventory)` |
| 11.8 s | **364.0 s** | **2** | `acs_housing_universe_source.py:262(_archive)` |

Full 40-row listings, **ordered by cumulative time as the brief specified**
(`Ordered by: cumulative time / List reduced from 7544 to 40`):
`.profile-runs/f8000/f8000.top40.txt`, `.profile-runs/f2000/f2000.top40.txt`.
The in-text table above is ordered by **self** time instead, because a
cumtime ordering on this profile is dominated by the pytest and pluggy frames
that wrap the whole run — its first ten rows are `_pytest` and `pluggy` entries
at 1,842 s cumulative, which locate nothing. Self time is what distinguishes the
call sites; both orderings are on disk.

Two call sites are the entire run: `_inventory` (1,473.3 s over **two** calls)
and `_archive` (364.0 s over **two** calls) = 1,837 s of 1,842 s, siblings, so
the sum is real. pytest and collection are 1.79 s (0.1%). **Kernel compute is
zero** — the run never reached a node.

### 3a. Run 2 is the fraction control, and it is exact

Run 2 ran the identical harness at **four times** run 1's sample fraction. If
ingest scaled with the sample at all, its call counts would move. They do not:

| function | 1/8000 | 1/2000 | ratio |
|---|---|---|---|
| `acs_person_coverage_authentication.py:188(_records)` | 5,054,865 | 5,054,865 | **1.0000** |
| `bytearray.append` | 3,382,952,633 | 3,382,952,633 | **1.0000** |
| `acs_person_coverage_authentication.py:60(_require)` | 5,418,945,835 | 5,418,945,835 | **1.0000** |
| `acs_person_coverage_authentication.py:230(_decode_record)` | 5,054,861 | 5,054,861 | **1.0000** |
| `acs_person_coverage_authentication.py:278(_inventory)` | 2 | 2 | **1.0000** |
| `builtins.len` | 4,424,967,359 | 4,214,038,477 | 0.952 |
| `acs_housing_universe_source.py:236(_csv_record)` | 3,673,585 | 2,962,934 | 0.807 |

Five counters are **bit-for-bit identical** — not approximately equal, identical
— across a fourfold change in the requested sample. The two that differ are
simply where each run's cap landed inside the second `_archive` pass.

Run 2's **bucket seconds cannot be used for this comparison at all**, and an
earlier draft of this section pretended otherwise. Its profile is wall-based and
contains the ~511–551 s suspension (§1), so as printed it reads store IO
1,810.6 s / 76.9%, other 529.9 s / 22.5%, identity 13.6 s / 0.6% — visibly
distorted. The draft "corrected" that by subtracting each bucket's delta against
run 1 and renormalising onto run 2's measured 1,803.4 CPU-s, then observed that
the result agreed with run 1 "to a tenth of a percent in every bucket."

**That agreement was circular.** The correction sets run 2's buckets equal to run
1's and rescales; I checked, and run 1's values × (1,803.4138 / 1,842.3918) do
reproduce all three printed figures (1,310.709 → 1,282.98, printed 1,283.0;
518.001 → 507.04, printed 507.1). A number derived from run 1 agreeing with run 1
is not evidence of anything, and the claim is withdrawn.

**What actually carries the fraction-independence result is the call-count table
above, and it carries it easily.** Five counters are bit-for-bit identical across
a fourfold change in the requested sample — `bytearray.append` at 3,382,952,633
in both runs, `_require` at 5,418,945,835 in both. Those are integers read
straight out of two independent profiles, with no correction applied to either.
No renormalisation, no modelling, no shared derivation. That is the measured
proof of what §4 reads out of the code, and it is the single most load-bearing
result in this report: **a full-source build does exactly the same source-ingest
work as a 1/8000 toy build.** Run 3 then confirms the same shape with a wholly
different profiler (§3b).

### 3b. Run 3 confirms the shape with a profiler that costs nothing

Run 3 sampled instead of instrumenting, and got **2.3x further on less than
half the CPU**: 840.6 CPU-s to the end of the ACS side and into ASEC, against
1,803 CPU-s that did not finish ACS under cProfile. Its attribution, by deepest
in-repo frame (96,109 samples, effective 9.73 ms interval):

| bucket | share | ≈ CPU-s |
|---|---|---|
| **(c) store IO — source ingest** | **94.9%** | **798.1** |
| (a) identity — canonical JSON, digests, restoration verification | 4.2% | 35.3 |
| (d) other | 0.5% | 4.3 |
| **(b) kernel compute** | **0.4%** | **3.0** |

| heaviest in-repo frames | share | ≈ CPU-s |
|---|---|---|
| `acs_person_coverage_authentication.py:188(_records)` | 53.20% | 447.2 |
| `acs_housing_universe_source.py:262(_archive)` | 18.82% | 158.2 |
| `acs_person_coverage_columns.py:130(lines)` | 10.87% | 91.4 |
| `acs_housing_universe_source.py:497(_select)` | 3.99% | 33.5 |
| `canonical.py:18(_json_value)` | 1.87% | 15.8 |
| `acs_housing_universe_source.py:398(_tables)` | 1.57% | 13.2 |
| `acs_person_coverage_authentication.py:69(_json)` | 1.36% | 11.4 |

The sampler yields no cumulative-time ranking — it records self-frames, not call
trees — so there is no cumtime top-40 for run 3. Its full listings are on disk in
`.profile-runs/s8000r/s8000r.samples.json`: 80 self-frames and 80 in-repo frames.
The seven rows above are the whole in-repo tail above 1%.

**One thing the sampler said that I am withdrawing.** Its heaviest *self* frame
was `zipfile` at 80.7%, which an earlier draft read as "the decompression the byte
loop drives". That reading is wrong, and run 1's deterministic profile refutes it:
summing every `zipfile`/`zlib` self-time entry in `f8000.prof` gives **22.74 s of
1,842.4 — 1.23%** — with `zlib.Decompress.decompress` itself at 9.22 s. A
factor-of-65 disagreement between a deterministic per-call count and a 5 ms
sampler is the sampler's artifact, not a finding, so **decompression is single-digit
CPU-seconds and the 80.7% figure is withdrawn.**

What the two profilers *do* agree on is the bucket shape, and that is what §3b is
for: one inflating the workload 5×, one costing ~0 per call, both returning
**ingest is everything, kernel compute is nothing.** They disagree about which
frame inside ingest to name, and where they disagree I take cProfile's answer.

**This is the number the lane was missing, and it is 798 CPU-s.** Be exact about
which quantity that is, because an earlier draft rounded it to "~830" and in doing
so folded in work that is not ingest. Run 3's receipt is **840.6 CPU-s for the
whole process** — pytest import, ACS ingest, identity work, and the ASEC phase it
died in. The **store-IO "source ingest" bucket is 798.1 CPU-s**; adding the
identity bucket (35.3) gives 833.4. This report uses **798 CPU-s** for the ingest
phase and says so wherever it appears. It was measured directly, not inferred by
dividing a
profiled figure by 5.05 as the earlier draft did (which gave ~364–450 CPU-s and
was roughly half the truth, because the profiled runs never finished the phase
and the 5.05x factor applies to `_records`, not to the zipfile and pandas work
around it). **That is 15.1% of v4's entire 5,278.6 CPU-s build.**

**How much of that 798 s is *proven* fraction-independent, precisely.** §3a's
identical counters cover `_records`, `bytearray.append`, `_require`,
`_decode_record` and `_inventory` — which in run 3's attribution are `_records`
(447.2 CPU-s) plus `_archive` (158.2) = **~605 CPU-s measured fraction-independent**.
The remaining ~193 CPU-s — `acs_person_coverage_columns.py:130(lines)`, `_select`,
`_tables` and the canonical-JSON work around them — is *assumed* fraction-independent
from §4's code reading, and `_select` in particular does filter on the sampled
serialnos. The ASEC side is a code-reading claim only; no run measured it. So the
right statement is **~605 CPU-s measured fixed, ~193 CPU-s argued fixed**, and the
conclusion is unchanged at either bound.

### 3c. Run 3 also found a refusal, and it is undiagnosable by construction

Run 3 stopped because the build refused, not because the cap fired. The record on
disk is a single sorted-key line, re-wrapped here for reading, with
`elapsed_seconds` written as `930.9258635840379`:

```json
{"phase":"ACTUAL_NINETEEN_NODE_COLD_EXECUTION","exception_type":
"SurveyPopulationPreparationError","status":"INCOMPLETE","elapsed_seconds":930.93,
"automatic_retry":false,"release_eligible":false,"static_codes":[]}
```

pytest's traceback ends at `survey_population_preparation.py:1418`:

```python
    except SurveyPopulationPreparationError:
        raise
    except Exception:
        raise SurveyPopulationPreparationError("PREPARATION_ISSUANCE_REFUSED") from None
```

**A correction on what `from None` does, because an earlier draft of this section
got the Python wrong.** It does *not* discard the cause. It sets
`__cause__ = None` and `__suppress_context__ = True`, which suppresses the
chained traceback from the default display — so nothing about the original
failure reaches pytest's output — but the original exception stays attached as
`__context__`, and any caller that looks can print it. I verified that on this
interpreter rather than asserting it.

**So the reason this report cannot name the cause is my harness, not the repo.**
The refusal record is written by
`.profile-runs/harness/test_native_nineteen_node_financial.py:200-217`, which
captures `type(error).__name__` and regex-matches `str(error)` for three
prefixes — `CURRENT_SURVEY_PREDICTOR_`, `ATOMIC_SURVEY_RECONSTRUCTION_`,
`SURVEY_FINANCIAL_SUCCESSOR_`. `PREPARATION_ISSUANCE_REFUSED` matches none of
them, which is exactly why `static_codes` is `[]`. The harness had the exception
in hand, `__context__` populated, and did not look. That is a defect in this
lane's instrumentation and I record it as mine.

What remains a genuine repo-side smell is narrower: the catch-all collapses every
unexpected exception into one static code and suppresses the chain, so the
default operator experience — a pytest traceback, a CI log — shows a bare
`PREPARATION_ISSUANCE_REFUSED` with no cause, even though the cause is
recoverable in principle.

The sampler's last three timeline marks locate the failure:
`acs_population_catalogue.py:275(consume)` at t=914 s,
`asec_current_money.py:519(__post_init__)` at t=924 s, and
`asec_person_income_source.py:312(_verify)` at t=934 s — so it fell over
entering ASEC restoration verification, with the whole ACS side behind it. The
same path completed at 1/1000 in v4 on the same sources, so the difference is
the requested fraction. I did not spend a fourth run to bisect it and I am not
going to guess at the cause.

**Two things follow for a merge decision.** First, the 1/8000 fraction the brief
specified does not complete on this build at all — worth knowing independently of
cost, and I did not spend a fourth run to bisect it. Second, and more weakly than
an earlier draft of this report claimed: a build step whose default failure
display is one static code with the chain suppressed is awkward to debug at
full-source scale, where a single failed attempt costs hours. It is a
diagnosability *smell*, not a blocker — the cause survives on `__context__` for a
caller that reads it — and the first thing to fix is the harness, not the repo.

---

## 4. The fixed floor: the whole source universe is scanned byte-by-byte before sampling

I read this code rather than inferring it from the profile.

`_records` (`acs_person_coverage_authentication.py:188-227`) walks the entire
ACS person and household CSVs **one byte at a time in Python**:

```python
    while block := stream.read(4096):
        for byte in block:                                    # every byte, in Python
            ...
            _require(len(record) < cap, "CSV_RECORD_BYTES")   # a call + a len per byte
            ...
            _require(token_bytes <= MAX_TOKEN_BYTES, ...)     # another call per byte
            record.append(byte)                               # a call per byte
```

**The call counts corroborate the mechanism arithmetically.** 3,382,952,633
`bytearray.append` = one per byte = **3.38 GB scanned**, matching the staged ACS
person (2.41 GB) plus household (0.98 GB) uncompressed members. The
5,418,945,835 `_require` calls decompose as one unconditional per byte plus one
token-guard per non-comma byte, so commas = 2 × 3,382,952,633 − 5,418,945,835 =
**1,346,959,431**, i.e. **266.5 commas per record** over 5,054,865 records —
against the ACS person file's 286 fields (285 commas). The profile and the source agree.

`_decode_record` (`:230`) then builds a fresh `io.TextIOWrapper` over a fresh
`io.BytesIO` and a fresh CSV reader **per row** (5,054,861 calls). The ASEC side
does the same: `asec_coverage_authentication.py:265` is `for byte in chunk:`
with per-byte `_require`.

**The sample filter runs last — and on the dominant call there is no filter at
all.** In `_inventory` (`:278-320`) each record is `digest.update(raw)`-ed,
`_decode_record`-ed into a full CSV row, width-checked and projected to `cells` —
and only then does `if cells[0] not in serialnos: continue` discard it. The call
that dominated runs 1 and 2 comes from `acs_population_catalogue.py:152`, which
passes **`frozenset()`**: it is a whole-source gate, so the predicate is always
true and **every row is decoded and then thrown away**. That is not a sampling
inefficiency — it is the same cost at every fraction, which is precisely why §3a's
counters do not move. Independently,
`acs_housing_universe_source._reconstruct` (`:563`) builds a `full` projection
of every household and person row (`:566-572`), writes it as
`full-projection.json` (`:573-574`, 292,484,053 bytes in both the v4 tree and
run 3's) and only then calls `_select(full, serialnos)` (`:575`). In its parse
loop every row is JSON-encoded purely to accumulate a size bound —
`selected_bytes += len(_json(row))` (`:360`) — and the retained rows are encoded
again as a whole at `:573`. `_csv_record` (`:236-259`) constructs a **new
`csv.reader` per row**, scans each line three times for control characters
(`:246`), and re-encodes **every one of the ~280 parsed ACS person fields** to
length-check it (`:256-258`) in order to keep three (`_P_FIELDS`, `:56`).

**The module already blocks-hashes elsewhere, though that is a weaker precedent
than an earlier draft claimed.** `_inventory`'s *non-applicable* branch
(`:293-297`) digests members in 4 KiB blocks with no per-byte Python at all; only
the applicable branch drops into `_records`. But that branch only **hashes** — it
does no CSV record-boundary detection, no quote-parity tracking and no
token-ceiling enforcement, which is exactly what `_records` exists for (its own
docstring at `:189-193`). So it is evidence that block-wise byte handling is
idiomatic in this module, **not** evidence that the rewrite in §10 (item 2) is
drop-in. That rewrite still has to implement framing; the claim is only that it
can do so on whole blocks with `bytes.find`/`bytes.count` rather than a call per
byte.

**The scanner's measured throughput is 12.9 MB/s.** That is the single most
telling number in this section, and it is a direct measurement rather than a
derivation: the profiler-overhead A/B ran `_records` over a real 209,715,200-byte
slab of `psam_pusa.csv` in 16.222 unprofiled CPU-s, i.e.
**12,927,528 bytes/second** (`.profile-runs/profiler-overhead-bench.json`). For
scale, `hashlib.sha256` on this same machine runs at roughly 2,900 MB/s — **a
couple of hundred times faster than a loop that is merely looking for commas and
newlines**. (The 12.9 MB/s is receipted: 209,715,200 / 16.222375 = 12,927,528 B/s
is the bench file's own `unprofiled_bytes_per_second`. The sha256 rate is a
one-line reference measurement taken in this session with no committed receipt,
so I give it to one significant figure and use it only as an order-of-magnitude
contrast.) The 3.38 GB of ACS source therefore costs **~261 CPU-s in the scanner
alone** — a few minutes against the second or two the hardware is capable of —
and it costs them on every build.

**None of it varies with the requested fraction** (§3a proves this to the call).
The 1/8000 run and a full-source run do the same ACS and ASEC work, and it costs
798 CPU-s every time.

---

## 5. The hard ceiling: the build refuses at ~6% of the US source

`survey_population_preparation.py:1346` encodes the whole preparation document
with `_encode(...)`, which defaults to `MAX_PAYLOAD_BYTES = 64 * 1024**2`
(`:50`) and raises `PAYLOAD_LIMIT` at `:108`. That document embeds
`"origins": origins` and `"selection": _plan_document(plan)` — **one record per
source household and per person**. A second, independent 64 MiB budget guards
the same lists inside `_plan_document` via `_bounded_append` (`ORIGIN_LIMIT`,
`:818`).

Measured on the pilot's own exported artifact, whose sha256
`34b362d85d2f06ac…` matches the manifest's export record exactly, by re-encoding
each component with the repository's own canonical separators:

| component | bytes | n | per source hh |
|---|---|---|---|
| `origins.households` | 269,000 | 1,584 | |
| `origins.entities` | 224,755 | 6 | |
| `origins.persons` | 210,924 | 2 | |
| `origins` (incl. `storage_transitions` 13,268, age normalization 762) | **718,800** | | 453.8 B |
| `selection.selected` | **385,122** | **1,584** | 243.1 B |
| fixed (producer 21,135, `selection.excluded` 7,250, source_files, catalogues, hashes) | **32,141** | | — |
| **total** | **1,136,063** | | **696.9 B/hh marginal** (717.2 incl. the fixed 32,141) |

718,800 + 385,122 + 32,141 = 1,136,063 exactly.

Feeding that same document, scaled by replicating its per-household lists,
through the repository's own `_encode`:

| scale | source hh | payload | encode CPU | |
|---|---|---|---|---|
| ×1 | 1,584 | 1,136,063 B | 0.052 s | 717.2 B/hh |
| ×4 | 6,336 | 4,426,274 B | 0.206 s | 698.6 B/hh |
| ×16 | 25,344 | 17,587,118 B | 0.844 s | 693.9 B/hh |
| **×64** | **101,376** | — | 3.193 s | **REFUSED: `SurveyPopulationPreparationError: PAYLOAD_LIMIT`** |

**Ceiling: 96,247 source households** from the ×1 artifact's own rate, **96,867**
from the measured ×1→×16 marginal rate — so **96,200–96,900, i.e. 6.1% of the
source.** I print the range rather than a point estimate because the two
defensible rates disagree in the third digit.

**The source is 1,587,376 households**, and I take that from the pilot's own
receipt rather than from memory: `selection.supplied_households = 1587376` in
the same preparation artifact. A full-source payload is therefore
**1,048–1,055 MiB, 16.4–16.5× the limit.**

A second ceiling sits at `ALLOCATION_MAX_BYTES = 64 MiB`
(`graph_survey_population.py:62`), where `_allocation_payload` (`:344-369`)
streams one ~320-byte `_instruction_document` per household into a single
bytearray with a bound check before every append: that refuses at roughly
**200,000 households (~13%)**. One significant figure, not three — the ~320 B per
`_instruction_document` is an estimate, nothing in `.profile-runs/` measures it,
`final_tables.py` does not compute this ceiling, and the code's only hard per-row
bound is the 4,096 B of `_bounded_json`. It is an order-of-magnitude second
ceiling that sits *above* the preparation ceiling and therefore does not bind
first.

The encoding itself costs **33.3 µs per source household**, i.e. **52.8 CPU-s at
full source**. **The ceiling costs essentially nothing to raise in CPU terms.**
It is a transport-shape decision — one bounded JSON document per run carrying
one record per household — inside a system that is otherwise columnar and
content-addressed.

---

## 6. The scaling law

### 6a. What the node timings decompose into

The v4 receipt records per-node wall times, and the manifest's `wall_time` spans
the **whole** node-loop body: `node_started` is the first statement of
`for node_id in compiled.order` (`executor.py:2296-2297`) and
`wall_time=time.perf_counter() - node_started` is in the `NodeReceipt` built at
the end of the same body (`:2616`). Re-summing v4's 28 timed nodes myself:

| | prefix (9 nodes) | financial (19 nodes) | total |
|---|---|---|---|
| 4 ASEC predictor nodes | — | 957.15 s | **957.15 s** |
| `survey_population.observed_geography` | 141.93 s | 0.31 s | **142.24 s** |
| source-bound subtotal | | | **1,099.38 s** |
| **population-work nodes (22)** | 33.3 s | 10.5 s | **43.78 s** (mean 1.99 s/node) |
| of which nodes that were store **hits** and still cost time | 2.3 s | 8.7 s | 10.98 s |
| **all 28 nodes** | 175.3 s | 967.9 s | **1,143.16 s** |

**The population-scaling work of the entire 28-node graph is 43.8 CPU-s at
3,168 cloned households.** The 1,099.4 s that dominates the node timings is
source ingest that does not grow with the sample.

Two notes on that classification. The four predictor nodes are source-bound
because each one's `run()` calls `self._qualified(context)` →
`qualify_current_survey_predictors` (`graph_current_survey_predictors.py:301`),
which reads the ASEC sources — four distinct kernel classes
(`CurrentSurveyPredictorProjectionKernel` `:370`, `DonorFilterKernel` `:410`,
`DonorColumnsKernel` `:439`, `AttachKernel` `:520`), one call each, matching the
four measured node times (263.2, 242.0, 226.4, 225.6 s). `observed_geography`
(141.9 s) I classified source-bound because it loads and validates the fixed
28.9 MB national atomic support, but it also assigns geography to the sampled
population, so it is genuinely mixed and I could not split it under the cap.
Moving all of it to the scaling side would raise the full-source scaling term
from 43.8 to 185.7 CPU-s per 3,168 households — the full-source total from 15.6
to **55 CPU-hours**. That is the single largest lever inside this decomposition,
and it is unresolved.

**Cross-check against the measured per-cell constants.** One whole-frame
`_frame_identity` pass at 1/1000 is 1,700,710 cells × 0.52–0.60 µs (§8d's
constants blended by the frame's real dtype mix) = **0.89–1.02 s**. The 22
population-work nodes total 43.8 s, i.e. **43–49 whole-frame passes, about 2.0
per node** — what the static map predicts: one `_population_stamp` per node from
the observer, plus the store writes, the two `_context_digest` passes on cold
nodes and the two frame deep copies. **That is a factor-of-two consistency check
with an unexplained residual, not
agreement, and the report should not have called it agreement.** §8d's own
measured constants make the named companions negligible — two deep copies plus
validation are 2.9 ns/cell (0.005 s, ~0.5% of a ~0.95 s pass) and the pickle round
trip 2 ns/cell — so the bottom-up model accounts for roughly **1.25** whole-frame
equivalents per node against 2.3 measured. About **0.9 s per node is
unattributed**. It is the strongest check available without a profiled run that
reaches the graph, and it leaves half the per-node cost unexplained.

### 6b. The exponent

The adversarial verification pass overturned the reader pass's superlinearity
claims: of 24 flagged sites, all but two are linear in rows times a graph or
schema constant. The survivors:

- **`population.py:1270-1273`** (`_remapped_expand_memberships`) runs
  `source_person[membership] == source_group` — a full-length boolean comparison
  over the entire person table — **once per source group**. Genuinely
  O(households²). I measured the isolated loop from 500 to 128,000 groups. Its
  naive log-log slope over that range is only **1.10**, because the ~70 µs
  per-group pandas `.loc` setup dominates below ~30k households; fitting the
  two-term form the code implies, `t = groups × (c + k × P)`, gives
  **c = 66.8 µs per group** and **k = 0.188 ns per person per group** with
  P = 2.187 × source households.

  **The number of groups is not the number of households.** The measured loop is
  the *inner* one; `population.py:1266` wraps it in
  `for group in before.schema.group_entities:`, and `US_SCHEMA` has **five**
  (`microcosm/frame/units.py:45-51`: household, tax_unit, spm_unit, family,
  marital_unit). `source_person` is the **whole** person table for every one of
  them. Using the pilot's own per-household entity ratios — household 1.0,
  tax_unit 1.343, spm_unit 1.0006, family 1.0063, marital_unit 1.7513 — there are
  **6.10 groups per source household**, so the term is **6.10×** what a
  households-only model gives: **6,967 CPU-s (1.94 CPU-hours, 116 minutes) at
  full source**, not the 1,142 CPU-s an earlier draft carried. Real, and no
  longer negligible — it is **12% of the full-source build**. It is also still a
  *lower* bound: the bench times only the comparison, while the code then runs
  `for source_member in members:` (`:1274`) over every matched person, which adds
  roughly 5 × P Python iterations the bench never paid.
- **`Frame.revalidate` → `bundle.py:225 np.sort` / `:230 np.unique`** per group
  entity — an O(R log R) factor, re-run on every `put_frame` (`store.py:931`)
  and every `_validate_create` (`executor.py:1051`).

Everything else is **linear**. The law is
`CPU = FIXED + c × households + O(H²)`, with the H² term worth **1.9 CPU-hours**
at full source. That is no longer a rounding error — it is the second-largest
scaling term, behind the per-node population work and ahead of nothing else —
but it does not change the exponent story: at every size the architecture can
actually reach today (§5), the quadratic term is under a minute.

### 6c. Validation, honestly

This is where the brief's plan and what I could deliver diverge, and I will be
plain about it: **I could not validate a fitted exponent against the v4 receipt,
because no profiled run reached the graph.** What I can check is the
decomposition's internal consistency — and v4's own node timings supply the
43.8 s scaling term at the validation point itself (1/1000, 3,168 cloned
households), so the "prediction at 1/1000" and the "measurement at 1/1000" are
the same number by construction rather than by agreement. That is weaker
evidence than the brief asked for and I am not dressing it up as a validated fit.

What run 3 *did* validate is the other half: the fixed term. It measured the ACS
ingest phase directly at 798 CPU-s, unprofiled, at a fraction 8× smaller than
v4's — against a v4 build that paid the same 798 CPU-s inside its 5,278.6. The
fixed/scaling split is therefore measured on both sides, even though the
scaling exponent is not.

### 6d. Predictions

Anchored on the one complete measurement that exists — the v4 receipt's
**5,278.6 CPU-s** at 3,168 cloned households — plus the measured scaling
increment (43.8 CPU-s per 3,168 cloned households) and the measured quadratic
term. Clone ratio 2.0, from v4's own 1,584 → 3,168.

The model is **incremental**, anchored on v4's complete measurement rather than
on a reconstructed fixed term, so every row below sums exactly to its own total:
`total = 5,278.6 + (linear above v4) + (quadratic above v4)`.

| target | source hh | cloned hh | v4 base (measured) | + linear | + O(H²) | **total** |
|---|---|---|---|---|---|---|
| 1/1000 (v4, **measured**) | 1,584 | 3,168 | 5,278.6 s | — | — | **1.47 CPU-h** |
| 1/100 | 15,873 | 31,746 | 5,278.6 s | +395 s | +6.5 s | **1.58 CPU-h** |
| **ceiling (~96,557)** | **96,557** | **193,114** | 5,278.6 s | +2,625 s | +62.1 s | **2.21 CPU-h** |
| 1/10 | 158,737 | 317,474 | 5,278.6 s | +4,343 s | +127.3 s | **2.71 CPU-h** |
| **full source** | **1,587,376** | **3,174,752** | 5,278.6 s | +43,826 s | +6,966.7 s | **15.58 CPU-h** |

The v4 base already contains that build's own 43.8 CPU-s of population-scaling
work, which is why the increment columns are increments and not the absolute
terms. The absolute three-way split is the table immediately below, and it sums
to the same place: 5,234.8 + 43,870 + 6,967 = 56,072 s = 15.58 CPU-h.

Per bucket, that is the honest three-way split the brief asked for:

| bucket | 1/1000 | full source | scales? |
|---|---|---|---|
| **fixed** (residual: 5,278.6 − 43.8) — source ingest, authentication, preparation, export | **5,234.8 s** | **5,234.8 s** | **no — measured identical at 1/8000 and 1/2000; assumed so at 1/1000 and above, from §4's code** |
| **linear** — per-node population work (identity, store, copies) | 43.8 s | 43,870 s | yes, exponent 1 |
| **quadratic** — `_remapped_expand_memberships`, × 5 group entities | 0.7 s | 6,967 s | yes, exponent 2 |
| of the fixed term, ACS ingest alone (run 3, direct) | 798 s | 798 s | no |
| of the fixed term, the 4 ASEC predictor nodes (v4 receipt) | 957.2 s | 957.2 s | no |

The four-way (identity / kernel / store IO / other) split the brief named is
measured **only for the fixed term**, because that is the only part any run
reached: store IO 94.9%, identity 4.2%, other 0.5%, kernel compute 0.4% (run 3).
Its split inside the *linear* term is unmeasured; the static map predicts
identity dominates there, at ~2.3 whole-frame `_frame_identity` passes per node.

For comparison, the naive linear extrapolation the brief started from —
5,278.6 CPU-s × 1000 — gives **1,466 CPU-hours (61 CPU-days)**. It is wrong by
**94×**, because it multiplies a fixed source-ingest tax by the sample ratio.

**These are lower bounds, and the uncertainty is one-sided.** **2,664 CPU-s** of
v4's runner time sits outside both the node loop and the ACS ingest — the
manifest's runner CPU is 4,605.35, the 28 node wall times sum to 1,143.16, and
ingest is 798 — and no run reached it. (An earlier draft said "roughly 3,000",
which was 13% high and inflated the one-sided bound below.) Its known
composition is the repeated
`qualify_current_survey_predictors`, the ASEC native loads and restoration
verification (where run 3 died), and `reconstruct_atomic_survey_geography`.
Those are principally source-bound — run 3's 94.9%-ingest attribution is direct
evidence that they are — and the runner-level *population* work I can account
for from measured constants (38 whole-frame `_population_stamp` passes for the
verification loops at `graph_atomic_survey_financial.py:1895` and `:1910` at
~0.95 s each, plus `same_replayed_population` per node) comes to roughly
50–100 CPU-s at 1/1000. Scaling that band by the row ratio
3,174,752 / 3,168 = 1,002.1 and adding it to the 15.58 gives
**15.58 + 13.9 = 29.5** at the low end and **15.58 + 27.8 = 43.4** at the high
end: the realistic full-source figure is **~30–43 CPU-hours**. (An earlier draft
printed "~26–40" for this band without showing the arithmetic at all; it is now
derived in line so a reader can check it.)

If instead the *entire* unattributed remainder scaled — all 2,664 CPU-s of it —
the same ratio gives **15.58 + (2,664 × 1,002.1 − 2,664)/3,600 = 756 CPU-hours**.
Run 3's 94.9%-ingest phase attribution contradicts that reading, but I did not
measure the remainder to completion, so I name the bound rather than hide it.

**The measurement that closes this gap is one uncapped run at 1/1000 under the
sampler — about 1.5 CPU-hours**, now that run 3 has shown the sampler reaches
far enough to see it. This lane's 30-minute cap does not permit it, and 1/8000
will not do, because §3c shows 1/8000 refuses.

The 45-node graph is **not** measured here. Scaling by node count alone is an
unmeasured ratio: 45/19 = 2.4× on the node term only, which would put the
scaling term at ~30 CPU-h and the total at ~60–95 CPU-h at full source. Flagged
as unmeasured.

---

## 7. The incumbent's measured durations

`~/PolicyEngine/_buildp-runtime/logs` **does** carry durations, and the sibling
`donor/release_manifest.json` carries the certified default's. Every figure below
is quoted from the file named beside it, not from memory:

| build | scale | wall | CPU | peak RSS | source |
|---|---|---|---|---|---|
| certified default `populace_us_2024_buildp.h5` — target compilation | 57,240 hh | | 1,132.1 s | | `donor/release_manifest.json` → `build.timing` |
| — calibration | | | 1,072.4 s | | same |
| — **total build** | | | **8,161.1 s (2 h 16 m)** | | same |
| ACS-local **staging** | — | **7,829.5 s** | **99,337.7 user + 3,215.6 sys** | 37.37 GiB | `logs/acs-local/staging_run.log` |
| ACS-local **release chain** | 1,588,854 hh | **9,156.4 s** | **5,672.8 user + 302.3 sys** | 87.71 GiB | `logs/acs-local/release_chain_run.log` |

The raw lines, verbatim: `7829.54 real 99337.73 user 3215.55 sys` and
`40126742528 maximum resident set size` at `staging_run.log:12735-12736`;
`9156.43 real 5672.78 user 302.27 sys` and `94183096320 maximum resident set size`
at `release_chain_run.log:126-127`. The timing block is
`{"target_compilation_seconds": 1132.080194915994, "calibration_seconds":
1072.4242046249856, … "total_build_seconds": 8161.056042167009}` — **abridged**:
the file is pretty-printed and carries a fourth key,
`"elapsed_through_calibration_seconds": 2800.574625542009`, between the second and
third. Note also that the first three rows of the table come from
`_buildp-runtime/donor/release_manifest.json`, not from `logs/`. The staging wall
re-derives from `staging.log`'s own bracket (03:38:59Z → 05:49:28Z = 7,829 s).

Release-chain stage detail from the log: staging frame load 60.7 s; materialize
**4,149.3 s** (3,972 admin measures over 40 chunks); calibrate **1,797 s** (800
epochs); then qa, finalize, package;
`DONE stages=['materialize','calibrate','qa','finalize','package'] (9147.4s)`.

So the incumbent builds the **1.59M-household** local-area dataset in
**4.72 wall-hours and 30.15 CPU-hours**, and the 57k certified default in
2 h 16 m. Note the staging lane's 99,337.7 user-seconds against 7,829.5 s wall —
**12.7× parallelism**. The native executor's `run_graph` is a single serial
Python loop (`executor.py:2296`) in one process: the `microcosm.graph` package
imports no `threading`, `multiprocessing`, `concurrent.futures` or `joblib`
anywhere (grepped across the package), so the **executor** contributes no
parallelism of its own.

Its *kernels* are a different matter, and this is not hypothetical BLAS:
`microcosm.fit.qrf` fits quantile forests with `n_jobs=_fit_n_jobs()`
(`qrf.py:542`), and `_fit_n_jobs` returns **-1 — every core —** whenever
`POPULACE_FIT_N_JOBS` is unset (`qrf.py:435-447`). This lane pinned it to 1, as
the pilot's own `run_v2.py` does, so every measurement here is single-threaded by
construction and cannot see that parallelism. An unpinned production build would
get real concurrency inside the predictor nodes.

It does not rescue the comparison, for two reasons. The dominant measured costs
are a per-byte Python loop and a per-cell Python hashing loop, both strictly
single-threaded whatever the environment says; and kernel compute was 0.4% of
what any run reached. **So treat CPU-hours as wall-hours for this path — while
noting that the predictor nodes could go faster in wall-clock on an unpinned
build, and that this report cannot say by how much.**

**What this comparison is and is not.** The two pipelines are not the same work:
the incumbent's staging+release chain produces a calibrated, QA'd, packaged
release, while the native path measured here stops at the nineteen-node
financial graph, and the incumbent's 30.15 CPU-hours includes ~1,800 s of
calibration the native path never runs. Read it as an order-of-magnitude
reference point for what this machine already does in an evening, not as a
like-for-like benchmark.

---

## 8. Static map (line-cited)

Produced by two agent passes over the files the brief named — a 14-agent pass
(7 scope readers, 7 adversarial verifiers) over `microcosm/graph/*.py` and
`microcosm/frame/*`, then a 71-agent pass (6 module readers, 65 per-operation
verifiers, 0 errors) that closed the six modules the first pass never reached.
Every line number below was re-derived with `grep -n` and independently checked
at its line by a second agent; the load-bearing ones I opened myself. Raw
output: `.profile-runs/static-map.json`, `.profile-runs/static-rows.json`.

### 8a. The per-node path of `run_graph`

Loop at `executor.py:2296`; `node_started` at `:2297`, `wall_time` at `:2616`,
so everything here is inside the manifest's node times.

| operation | site | runs | scales with | on verify path |
|---|---|---|---|---|
| **`_apply_result` → two full frame deep copies + full constructor validation** | `executor.py:2497` → `population.py:1770`, `:2680-2683`; `bundle.py:118`, `:121-126` | **every node, cold AND cache hit** — it sits outside `if result is None:` (`:2406`) and `if not hit:` (`:2571`) | rows × columns | — |
| **observer snapshot: full pickle round trip of every table and link** | `executor.py:355`, `:372`, called `:2569` | **every node, hits included** | rows × columns | — |
| **observer stamp → `_population_stamp` → `_frame_identity` per-cell Python loop** | `survey_atomic_geography.py:230`, `:245` → `survey_population_preparation.py:641`, loops `:675-676`, `:688-689` | **every node** via the observer; again at `graph_atomic_survey_financial.py:1895`, `:1910` | rows × columns | yes |
| `_context_digest` over the node's declared input columns | `executor.py:466-495`, called `:2423` and `:2449` | **twice** per **cold** node | declared columns × rows | — |
| every column stored, then the whole frame stored again | `executor.py:1524-1533` (`put_column`), `:1547` (`put_frame`) | per structural node, cold only | rows × columns | — |
| entity-id index written and hashed **beside every column** | `store.py:848`, `:849` (write), `:895` (read) | per column | rows × columns | yes |
| **every stored object's payloads re-hashed in full on every read** | `store.py:271` (`_sha256_file`, `:132-137`) via `_verified_meta` `:227` | **every store read** (`:878`, `:969`, `:981`) and every write finding an existing object (`:735`, `:765`) | rows × columns, at C speed | yes |
| each stored object fsynced file-by-file and directory-by-directory | `store.py:754` → `:164-176`, `:756`, `:770` | per store object | objects | — |
| cache hit loads every column **and** the whole frame | `executor.py:1882`, `:1899` | per cache-hit node | rows × columns | — |
| `frame.revalidate()` before each frame write (O(R log R) per group entity) | `store.py:931` → `bundle.py:128-152`, `:225`, `:230` | per structural node | rows log rows | yes |
| **`_remapped_expand_memberships` full-table scan per source group** | `population.py:1270-1273`, inside `for group in before.schema.group_entities:` (`:1266`, **five** US entities) | per EXPAND node, **× 5 entities** | **households × people** | — |
| **DataFrame concats rebuilding full-length columns** | `population.py:1314` (`pd.concat([carried, remapped])`, per group entity), `:1552`, `:1625` (strata) | per EXPAND node, per group entity | rows | — |
| **per-cell Python in the store's series codec (string/object columns)** | `store.py:463` (write, `for missing, value in zip(...)`), `:481` (object), `:548-558` (read) | every `put_column`, and every cache-hit `load_column` | rows, for string/object columns only | yes |
| kernel module source re-read and SHA-256'd, uncached | `kernel.py:457-497`, `:509-510`, via `_all_node_keys` `executor.py:2285` | **every node, every run**, including all-cache-hit runs | not population (file bytes) | — |

**The replay path, which the brief asked about explicitly and §8a's table above
does not reach.** The executor's node loop is not the only pass over every
population. `graph_atomic_survey_financial.py:1686` opens a **second**
`for node_id in compiled.order:` loop outside the executor that reconstructs each
node's expected Population and re-patches it, and the results are compared
column-by-column by `atomic.same_replayed_population` at `:1768` and `:1915` (and
`:279`, `:847`). That is a whole second population-scaling verification pass over
the graph, it is not inside any node's `wall_time`, and it therefore sits inside
the 2,664 CPU-s §6d books as unattributed. No run reached it, so its cost is
unmeasured — but it is structural, not incidental, and a reader deciding whether
the remainder scales should know it is there.

Two placement corrections to the table above. The kernel source re-read and
SHA-256 row cites `_all_node_keys` (`executor.py:2285`), which runs **before** the
loop — it belongs under "Outside the node loop" below, not inside the per-node
path. And the `executor.py:110` canonical-encode bullet in §8b is row-sized only
on the **cache-hit** path: on a cold node `_normal_json_mapping` is called at
`:1250`, while the per-row EXPAND lineage is attached to that dict afterwards at
`:1274` and `:1286`, so a fresh full-source build — the report's own scenario —
does not pay row-sized canonical JSON there.

**Outside the node loop:** `_preflight_expand_declarations` (`:2282`),
`_source_paths_and_keys` (`:2284`), `_all_node_keys` (`:2285`), `typed_contracts`
(`:2286-2289`). `source_content_key` (`keys.py:54`) takes the **directory**
branch (`:67-68`) into `_directory_identity` (`:31`), which at `:45` does
`candidate.read_bytes()` — the entire file into memory — for every file in the
3.7 GB source tree; the graph declares the whole source directory as its single
source (`graph_survey_population.py:919`, bound at `:1082`/`:1143`). The runners
call `_source_paths_and_keys` themselves before `run_graph` calls it again
(`graph_atomic_survey_population.py:214`).

**The qualification is not memoized.** `qualify_current_survey_predictors`
(`current_survey_predictors.py:310`) carries no cache decorator, and it is
invoked **seven times per build from three distinct call sites** — an earlier
draft said "seven call sites", conflating invocations with sites: the runner
(`graph_atomic_survey_financial.py:1378`), the four predictor kernels' `run()`
via the shared `_Kernel._qualified` (`graph_current_survey_predictors.py:294`,
call at `:301`), and twice through
`verify_materialized_current_survey_predictors` (`:556`, requalifying at `:578`)
from `graph_atomic_survey_financial.py:854` and `:1811`. The code's own comment
at `:851-853` says the verifier "freshly derives current values". Three sites,
seven invocations; four of the seven are measured, at 957.2 CPU-s.

### 8b. The six modules the brief named and the first pass missed

`kernel.py`, `canonical.py`, `manifest.py`, `codecs.py`, `availability.py` and
`artifact_edges.py` had no line-cited answer until this pass. Two of the brief's
named categories — **codec encode/decode** and **identity recomputation on
read** — live here.

**Ruled out, with reasons.** `availability.py` (92 lines) is on the per-node path
four to six times per node and costs **nothing**: it imports no pandas, numpy,
hashlib, json, pickle or codec (`:3-6`), and every predicate is a dict lookup and
a string compare (`:11-16`, `:19-22`, `:44-45`, `:60`, `:74-81`).
`artifact_edges.py` is pure provenance glue; its one hash,
`opaque_artifact_key` (`:133`), is SHA-256 over canonical JSON of a 3-tuple of
short strings, and it scales with declared edges, not rows. `kernel.py` holds
every row-scaled object — `tables`, `weights`, `strata`, result columns, `Frame`
— **by reference**: `KernelContext.__post_init__` (`:372-383`) validates only the
artifact-alias mapping, and `KernelResult` (`:386-432`) has **no `__post_init__`
at all**, so nothing in the kernel surface walks a row. The row work around the
kernel call is executor's (`_project_context` slicing at `executor.py:642`, the
strata copy at `:663`).

**Identity recomputation on read: found in three places, and the store's is the
one the map was missing.** `artifact_edges.py:208` recomputes a stored artifact's
identity on every read and refuses a descriptor whose key does not match — over
short strings, so it is real but negligible. The expensive read-side
recomputation in *Python* is in `manifest.py` (below). But the one that touches
every byte of the population is in the store: `_verified_meta`
(`store.py:227-290`) **re-hashes every payload file of the object** at `:271`
(`actual_hash = _sha256_file(payload_path)`), comparing it against the digest
`_payload_table` recorded on write (`:140-152`), and it runs on **every** store
read and on every write that finds an existing object — `:721`, `:735`, `:765`,
`:878` (`load_column`), `:969` and `:981` (`load_frame`), `:1007`, `:1038`. A
cache-hit node therefore re-reads and re-hashes the whole stored frame.

It scales with rows × columns and sits on the verify path, so it belongs in the
table above, and it is now in it. It is also **cheap**, which is precisely why it
earns its place: `_sha256_file` (`:132-137`) streams 1 MiB blocks through C
hashlib, orders of magnitude more bytes per second than `_frame_identity`'s
per-cell Python loop manages over the same data. The store already demonstrates,
inside this same repository, what whole-frame content verification costs when it
is done the fast way.

**Codec encode/decode: found in two layers, and the second one IS per-cell
Python.** An earlier draft answered this brief category with `codecs.py` alone and
concluded "per-table pandas, not per-row Python." That is true of `codecs.py` and
**false** of the store's own series codec, which is the one on the per-node path:

| site | what | runs |
|---|---|---|
| `store.py:463` | `for missing, value in zip(mask, series.astype(object), strict=True)` — one Python iteration per cell, UTF-8-encoding each value, for every `StringDtype` column | every `put_column` of a string column |
| `store.py:481` | `[_encode_object_scalar(v) for v in series.to_numpy(object)]` — per-cell again, object columns | every `put_column` of an object column |
| `store.py:548-558` | the read side: a per-index loop decoding each value out of the offsets buffer | every `load_column` of a string column — i.e. **every cache hit** |

Numeric columns take the vectorized `_write_array` path and cost nothing like
this, so the penalty is confined to string and object columns — but it is paid on
every write **and** every cache-hit read, and it is the same per-cell Python shape
as `_frame_identity`. §8d's measured per-cell constants were taken on float64
only and do not price this path; I am naming the gap rather than estimating it.

**On `codecs.py` itself the earlier finding stands: per-table pandas, not per-row
Python.**
`codecs.py` is a dispatch registry (free: `:134`, `:185`) plus three loaders. The
`csv-tables` Frame loader is the hot path: a full `pd.read_csv` per entity and
link table (`:368`) inside the loop at `:367`, an optional full `astype`
copy-cast (`:372`), the strata pop (`:519`), and weights either as one JSON float
per row (`:431`, `:461`) or as a second parsed and copy-cast CSV (`:481-484`)
with a row-for-row id alignment check (`:415-419`). Eleven of its fourteen
operations scale with rows or rows × columns — but all in vectorized pandas, which
is why the measured kernel/codec cost is small.

**The real surprise is `manifest.py`.** It holds no rows of its own — no pickle,
no deepcopy, no numpy, and its only `pd` token is a type annotation — but the
executor **stuffs per-row EXPAND lineage into the node receipt**:
`receipt["expand"] = expand_lineage_receipt(result.expand)`
(`executor.py:1274`) is one `[target, source]` pair per row of the expanded
entity, and `receipt["entrant_strata"]` (`:1286`) is one pair per entrant person.
The manifest then handles that row-sized structure repeatedly:

| site | what | runs |
|---|---|---|
| `manifest.py:277` → `:124` | `NodeReceipt.__post_init__` recursively deep-copies the whole receipt into `MappingProxyType`/tuple containers — the list arm at `:124` is the per-row allocation | per node |
| `manifest.py:594` | the manifest content key canonically encodes **every node's** content payload | per manifest build |
| `manifest.py:651-664` | `to_json` embeds each node receipt **twice** and computes the content key inline | per serialization |
| `manifest.py:740-746` | `from_json` re-derives the content key from the parsed body, then **again** from the reconstructed manifest | per read-back |
| `manifest.py:772` / `:684` | `load` parses the full document, then hands the same text to `from_json`, which parses it a **second** time | per read-back |
| `manifest.py:786` | canonicalizes and hashes the whole parsed body **solely to build an error-message label** | per read-back |
| `manifest.py:909-911` | compares stored against recomputed receipts by canonically encoding **both sides** of every node | on verification |
| `manifest.py:1011-1017` | `_validate_artifacts` re-hashes every artifact's full stored bytes | on verification |

**Canonical JSON of row-level payloads: found, and this is the one that bites.**
`canonical.py` is 106 lines with no loops **over rows** — it does walk elements,
at `:31` and `:37`, which is exactly the recursive copy described next — and its
value grammar
structurally refuses a Frame, DataFrame, Series or ndarray (`:38-40`) — so no one
can accidentally hand it a table. But `canonical_json` first materializes **a
complete second Python copy of its argument through a recursive per-element
walk** (`:18-40`) before encoding, and it is called from inside row loops:

- **`randomness.py:69-75`** — `keyed_uniform` runs
  `encoded = canonical_json([_coordinate(value) for value in key])` followed by a
  `hashlib.sha256(prefix + encoded)` **once per key**, in a pure-Python `for key
  in keys:` loop. Keys are per-row coordinates. This is per-row canonical JSON
  plus a per-row SHA-256, and it is the cleanest instance of the pattern the
  brief asked about.
- `population.py:632-634` — two `canonical_json` calls **per entrant row**,
  comparing a cached entrant stratum label to its receipt.
- `native_household_origin.py:636-650` — canonical JSON of the whole population
  origin binding, one dict per household.
- `executor.py:110` — `_normal_json_mapping` canonically encodes the whole kernel
  receipt (which carries the per-row expand lineage) and immediately re-parses it.

### 8c. Corrections I am recording rather than burying

Claims that did not survive checking. Entries 1–6 are claims formed early in the
work and withdrawn during it. Entries 7 onward come from a **verification pass
run over the finished report**: eight adversarial readers, one per dimension
(citations, arithmetic, receipts, mechanism, epistemic discipline, brief
compliance, internal consistency), each finding independently refuted by a
separate agent before it was accepted, plus my own re-derivation of every
load-bearing number from its receipt.

That pass found **two errors that moved headline numbers** — the quadratic term
(11) and the memory wall (12) — and one that moved a headline in the
architecture's *favour*. It is recorded in full rather than quietly folded in,
because a report a merge decision rests on should show how much of itself it had
to withdraw.

1. The per-node source re-hash at `executor.py:2453` fires for **zero** nodes of
   this graph — no node of the financial graph declares the source. Withdrawn.
2. `_observer_snapshot`'s pickle round trip measures **0.0017–0.003 µs/cell** (a
   214-column × 32,000-row table round-trips in 11 ms) — two to three orders of
   magnitude below `_frame_identity`. Withdrawn from the *CPU* shortlist; §9
   shows it matters enormously for **memory** instead.
3. `_context_digest` does **not** hash an accumulating population. A verifier
   counted declared input columns per node from the pilot's own `graph.json`:
   `0, 24, 4, 24, 0, 0, 4, 7, 12, 245, 245, 245, 8, 8, 8, 0, 0, 0, 256` — 1,090
   column-passes over the whole graph, no growth in node index.
4. Several line numbers first taken from `sed` ranges were off by a few lines
   and are corrected throughout (e.g. `_project_context` is called at
   `executor.py:2414`, not 2413; the cache guard is `:2406`, not 2404).
5. The ACS ingest cost was first inferred as ~364–450 CPU-s by dividing the
   profiled figure by 5.05. Run 3 measured it directly at **798 CPU-s** (the
   store-IO bucket of its 840.6 CPU-s run). The
   inference was roughly half the truth; the direct measurement replaces it.
6. The draft reported the four ASEC predictor nodes as 957.5 s and the US source
   as ~1,584,000 households. Re-summed from the manifest: **957.15 s**; read from
   the preparation artifact: **1,587,376 households**.
7. **The recommendation named the wrong mechanism.** §10 said the executor
   "already derives a content-addressed `frame_key` for every stored frame
   (`keys.py:106`)" and that verification could compare stored digests instead of
   recomputing a per-cell one. `frame_key` is `_hash_parts("frame", node_key)`
   (`keys.py:106-109`) — derived from the node key alone, carrying no frame
   content, so it is recipe-addressed and comparing it would verify nothing about
   cells. Corrected in §10: the fix is to vectorize `_frame_identity`'s per-cell
   loop, and the reason a stored digest cannot be substituted is stated there
   (`_population_stamp` is documented as a pure in-process seal). Found by
   reading `keys.py` and `store.py` during the verification pass, not by a
   reviewer.
8. **A whole-frame identity recomputation on read was missing from the map.**
   `_verified_meta` (`store.py:227-290`) re-hashes every payload byte at `:271`
   on every store read and on every write that finds an existing object. It is on
   the verify path and scales with rows × columns. Added to §8a's table and §8b.
   Its omission mattered because the brief named "identity recomputation on read"
   as a category and §8b had answered it with only the cheap string-level case.
9. **§9 mixed decimal and binary gigabytes, and every memory number was ~33%
   too high.** The three profiled runs' RSS figures come from
   `peak_rss_bytes / 1024³` (binary), while v4's "9.31 GB" is
   `9,313,337,344 / 10⁹` (decimal). Subtracting one from the other gave a
   2.56 "GB" delta where the true difference is 9,313,337,344 − 7,244,562,432 =
   2,068,774,912 B = **1.93 GiB**. Corrected throughout §9, §10 and §11, now on
   binary units with the byte counts printed: per retained copy 138 MB → **103.8
   MiB**; per cell 85 B → **64.0 B**. The incumbent comparison moved the same way
   (62 KB → **57.9 KiB** per household). Found by recomputing from the raw byte
   counts during the verification pass — and then superseded entirely by
   correction 12, which showed the subtraction those numbers came from was
   confounded.
10. **§6d's prediction rows did not sum to their own totals.** The first column
    was labelled "fixed (measured)" and printed 5,234.8 s, while the `+ linear`
    and `+ O(H²)` columns are increments over the **v4 build as a whole**
    (5,278.6 s) — which is what `final_tables.py` actually computes
    (`total = V4_CPU_TOTAL + scale_inc + quad_inc`). The two decompositions were
    mixed, so each row was short by exactly 43.8 s, v4's own scaling work counted
    once instead of twice. The column is now labelled "v4 base (measured)" and
    prints 5,278.6 s, the incremental model is stated above the table, and the
    absolute split is cross-footed to the same total underneath. §10's bucket
    table likewise moved from the incremental 43,826 to the absolute **43,870**
    so its column sums to the total it states. **No total, percentage-of-total or
    CPU-hour figure changed from this correction alone** (correction 11 did move
    the totals).
11. **The quadratic term was modelled over one group entity where the code loops
    over five — it is 6.1× larger than reported.** `bench_expand_membership.py`
    measures the *inner* loop at `population.py:1270-1273` with
    `MEMBERSHIP = "household_id"`, i.e. groups = households. But
    `population.py:1266` wraps it in `for group in before.schema.group_entities:`
    and `US_SCHEMA` declares **five** (`microcosm/frame/units.py:45-51`), with
    `source_person` scanned in full for every one. At the pilot's own entity
    ratios that is **6.10 groups per source household**, so the full-source
    quadratic term is **6,967 CPU-s (1.94 CPU-h)**, not 1,142 CPU-s (19 min).
    Consequences, all now applied: full-source total **13.96 → 15.58 CPU-h**; the
    quadratic's share **2.3% → 12.4%**; the naive-extrapolation error **105× →
    94×**; the observer's share **47% → 43%**; the realistic band **28–42 → 30–43
    CPU-h**; "a rounding error against the fixed term" withdrawn. `final_tables.py`
    now carries `GROUPS_PER_HH` so the corrected figure regenerates. **This is the
    only correction in this list that moves a headline number, and it moves it
    against the architecture.** The bench remains a lower bound besides: it times
    the comparison but not the `for source_member in members:` loop at `:1274`.
12. **§9's whole memory argument rested on a confounded subtraction, and the
    corrected answer is roughly 6× smaller.** The draft subtracted run 3's peak
    RSS (0 populations) from v4's (19 retained) and attributed the 1.93 GiB
    difference to retained populations. But §3c places run 3's death at
    `asec_person_income_source.py:312(_verify)` — entering ASEC HDF5 loads whose
    three files total **1,982,625,563 B = 1.846 GiB**, i.e. nearly the entire
    difference. Rather than bound it, I measured the retention directly
    (`bench_observer_retention.py`, no graph/source/engine, seconds): **9.6–9.8
    bytes per cell per snapshot**, flat across a 16× range. Nineteen snapshots
    cost
    **0.29 GiB at 1/1000**, not 1.93 GiB. Consequences: the source floor is
    **8.38 GiB** (reconciling v4 and run 3 exactly); the ceiling build needs
    **~26 GiB**, not 124; full source needs **~300 GiB**, not 1.9 TiB; and the
    claim **"memory binds below the payload ceiling" is withdrawn** — it does not.
    The retention is still a real defect worth fixing (~300 GiB → ~24 GiB), but it
    is not what stops a full build. **This correction moves a headline number in
    the architecture's favour, and it came from an adversarial verifier, not from
    me.**
13. **§6a's cell count was right before I "fixed" it, and I broke it briefly.**
    The exact figure is **1,700,710** (536.8402778 × 3,168, and the bench's own
    `cells` field); a mid-verification edit changed it to 1,700,582 by
    multiplying by the rounded 536.8. Reverted. Nothing derived from it moved.
14. **§3a's bucket agreement was circular and is withdrawn.** The draft
    "corrected" run 2's wall-based bucket seconds by subtracting each bucket's
    delta against run 1 and renormalising, then reported that the two runs then
    agreed to a tenth of a percent. That correction sets run 2's buckets equal to
    run 1's rescaled: run 1 × (1,803.4138/1,842.3918) reproduces every printed
    figure. Withdrawn. The fraction-independence result now rests solely on the
    five bit-for-bit identical call counters, which are integers from two
    independent profiles with no correction applied — stronger evidence than the
    thing that was removed.
15. **`raise ... from None` does not discard the cause, and the missing
    diagnosis was this lane's fault.** It sets `__cause__ = None` and
    `__suppress_context__ = True`; `__context__` still holds the original
    exception. The reason §3c could not name the failure is that this lane's own
    harness (`test_native_nineteen_node_financial.py:200-217`) recorded only the
    exception type and a regex over three prefixes that
    `PREPARATION_ISSUANCE_REFUSED` cannot match. §3c and the verdict now say so
    and downgrade the repo-side claim from a diagnosability *defect* to a smell.
16. **"Roughly 12 minutes" of suspension was an unrecorded impression.** The
    profile puts it at **511–551 s (8.5–9.2 minutes)**. Corrected in §1.
17. **The sampler's "zipfile at 80.7%" was an artifact and is withdrawn.** Run 1's
    deterministic profile puts all `zipfile`+`zlib` self time at **22.74 s of
    1,842.4 = 1.23%**, `zlib.Decompress.decompress` at 9.22 s. A factor-of-65
    disagreement with a 5 ms sampler is the sampler's. The mechanism sentence it
    supported ("the decompression the byte loop drives") is gone; §3b now claims
    only that the two profilers agree on the *bucket shape*.
18. **"~830 CPU-s" was in no receipt.** Run 3's receipt is 840.6 CPU-s for the
    whole process; the store-IO ingest bucket is **798.1**, 833.4 with identity.
    The report now uses **798** throughout, and 15.7% → **15.1%** of v4.
19. **"Roughly 3,000 CPU-s unattributed" was 13% high**: 4,605.35 − 1,143.16 − 798
    = **2,664**, so the one-sided "if everything scaled" bound falls from 850 to
    **756 CPU-hours**.
20. **"~0.5 µs/cell" was an unweighted guess.** Blended by the frame's real dtype
    mix (Int64 154, float64 54, int64 30, string 28, bool 1, boolean 2) §8d's
    constants give **0.52–0.60 µs/cell** over the 241 measured columns, with the
    28 string columns unmeasured and probably dearer. Every observer figure is now
    a range, and the four-significant-figure totals are gone.
21. **§9's incumbent sanity check ran the wrong way.** ~15.4 GiB per full-source
    snapshot is **10.2 KiB per source household** against the incumbent's 57.9 —
    about **5.7× leaner**, not "the same range". The error was in a paragraph
    written during this very verification pass.
22. **Item 4's "push the sample filter above the parse" does not apply to the call
    that dominates.** `acs_population_catalogue.py:152` passes `frozenset()`
    deliberately — a whole-source gate — so there is no filter to hoist there;
    the fix on that path is to skip `_decode_record` when the selection is empty.
23. **The replay path was missing from the map entirely**, in a category the brief
    named. `graph_atomic_survey_financial.py:1686` is a second whole-graph loop
    outside the executor with `same_replayed_population` comparisons. Added, and
    flagged as unmeasured.
24. **Smaller ones, all applied:** eleven store-hit node executions cost 11.0 CPU-s,
    not nine (the nine financial-lane hits are 8.7); commas re-derived exactly as
    1,346,959,431 = 266.5 per record against 286 fields, not 1.34e9/265/~280;
    `canonical.py` is 106 lines and *does* walk elements at `:31`/`:37`; 696.9 B/hh
    is the marginal rate (717.2 including the fixed bytes); the allocation ceiling
    is "roughly 200,000 (~13%)", not 209,700 (13.2%), because the ~320 B/row is an
    estimate; §7's `release_manifest.json` quotation is marked abridged; the
    sha256 contrast is marked unreceipted; the kernel source re-hash row belongs
    outside the node loop; `executor.py:110` is row-sized only on the cache-hit
    path; §11 discloses that it is three paragraphs where the brief asked for one;
    and §7 drops the within-10%/ESS calibration-quality figures the brief excluded.

### 8d. Measured per-cell costs

Microbenchmarks importing the repository's own functions; receipts
`.profile-runs/per-cell-bench.json`, `.profile-runs/per-node-unconditional-bench.json`.

| pass | float64 | int64 | bool | Int64 (nullable) |
|---|---|---|---|---|
| `_frame_identity` per-cell | **0.74–0.83 µs** | 0.36–0.47 µs | 0.31–0.37 µs | 0.48–0.55 µs |
| `_context_digest` / `_update_series` | 0.14–0.22 µs | 0.30–0.35 µs | 0.19–0.25 µs | **0.006–0.065 µs** |
| `_storage_parts` | 0.001–0.06 µs | 0.001–0.04 µs | 0.001–0.03 µs | ~0 |
| two deep copies + linkage validation | **2.4–3.4 ns/cell, mean 2.9** (float64 only; dtype sensitivity not measured) | | | |
| pickle round trip | **2 ns/cell** | | | |

**Frame shape, read out of the pilot's own `graph.json`.** Two different column
counts matter here, and an earlier draft of this report conflated them:

- The **CREATE node declares 245 columns** — person 198, household 29,
  tax_unit 5, spm_unit 5, family 4, marital_unit 4 (sums to 245). An earlier
  draft printed "person 214, household 41, tax_unit 6, spm_unit 6, family 5,
  marital_unit 5" as this breakdown; that sums to **277** and is a different
  object, so the attribution was wrong.
- The **frame that exists in memory once every node has run is wider**: the union
  of all nineteen nodes' declared outputs is **269** columns (person 211,
  household 40, 5, 5, 4, 4), plus each entity's id column and the person table's
  five membership columns. The benches model that frame at 277 columns across the
  six entities, which is the right object for a per-cell cost and is where 536.84
  comes from.

With the entity row ratios that is **536.84 cells per cloned household** —
**1,700,710 cells** at 1/1000 and 1.70e9 at full source (536.8402778 × 3,168 =
1,700,710 exactly, and the bench's own `cells` field agrees).

**`_frame_identity` is ~170× more expensive per cell than the frame copies it is
usually blamed alongside**, and ~50× more expensive than `_context_digest` would
be if the frame used nullable dtypes throughout (`executor.py:458-460` takes the
masked-buffer fast path; plain `int64`/`float64`/`bool` fall through to
`series.to_numpy(dtype=object)` at `:462` and a per-value Python loop at `:446`).
The declared dtype set permits both (`store.py:85-87`).

---

## 9. The memory wall — which binds before CPU does

The executor's population observer is optional, but this build uses it, and what
it does is not optional once enabled. `_observer_snapshot`
(`executor.py:355-372`) does `pickle.loads(pickle.dumps((tables, frame.strata)))`
— **a full independent copy of every table and link** — and its own docstring
says so: *"this costs one full detached population and a temporary serialized
table buffer per callback. Observers may retain that snapshot."* The executor
calls it at `:2569`, **outside the `if not hit:` guard**, so every node pays,
cache hits included.

The financial runner's observer then **retains every one of them**:

```python
    def observe(node_id, population):
        require(node_id not in observed, "ATOMIC_OBSERVER_DUPLICATE")
        observed[node_id] = population
        observed_stamps[node_id] = reconstruction._population_stamp(population)

    manifest = run_graph(..., _population_observer=observe)
```

`observed` is never cleared — it is read at `graph_atomic_survey_financial.py:1768`,
`:1788`, `:1791`, `:1794`, `:1864`, `:1911`, `:1915` and finally handed out as
`node_populations=observed` at `:1941`. **Nineteen full population copies are
held simultaneously** for the financial run.

**How much it costs is measured directly, because the obvious subtraction is
confounded.** The tempting move — subtract run 3's peak RSS (it built zero
populations) from v4's (it retained nineteen) — does not work, and the report
says so rather than using it:

| run | peak RSS (bytes) | peak RSS (GiB) | populations built |
|---|---|---|---|
| run 3 (1/8000) — refused **before the graph** | 7,244,562,432 | 6.75 GiB | **0** |
| v4 (1/1000) — completed all 19 nodes | 9,313,337,344 | 8.67 GiB | **19 retained** |
| difference | 2,068,774,912 | 1.93 GiB | |

Run 3 did not merely stop before the graph — §3c locates its last frame at
`asec_person_income_source.py:312(_verify)`, i.e. it died **entering the ASEC
HDF5 loads that v4 completed**. Those three files are
`parent.h5` 653,419,922 B + `household-attachment.h5` 662,871,719 B +
`person-income-attachment.h5` 666,333,922 B = **1,982,625,563 B = 1.846 GiB**,
against a 1.93 GiB difference. Nearly the whole delta is explained by source v4
loaded and run 3 never reached, so attributing it to retained populations would
be wrong. **The subtraction is an upper bound, not a measurement.**

So the retention was measured on its own, in
`.profile-runs/harness/bench_observer_retention.py` — no graph, no source, no
engine, seconds of CPU, not one of the three authorized runs. It builds the
pilot's declared frame shape, performs `executor.py:355-372`'s exact operation
(`pickle.loads(pickle.dumps((tables, strata)))`) nineteen times, retains all of
them as `graph_atomic_survey_financial.py:1625` does, and reads RSS growth:

| cloned households | cells | 19 snapshots grew RSS by | each | per cell |
|---|---|---|---|---|
| 3,168 | 1,700,710 | 301.9 MiB | 15.9 MiB | 9.8 B |
| 12,672 | 6,803,256 | 1,198.9 MiB | 63.1 MiB | 9.7 B |
| 50,688 | 27,212,815 | 4,775.8 MiB | 251.4 MiB | 9.7 B |

**9.6–9.8 bytes per cell per retained snapshot, flat across a 16× size range and
across four repeats of the bench** (RSS measurement wobbles by ~2% run to run, so
I give the range rather than three digits) — the extrapolation below is therefore
linear on a measured constant rather than on a confounded difference. The
nineteen snapshots cost **~0.3 GiB at 1/1000**, not the 1.93 GiB the subtraction
suggested: the confound was real and it was a factor of about six.

That reconciles the two measurements. v4's 8.67 GiB minus 0.29 GiB of retention
leaves a **8.38 GiB source-handling floor**, which is run 3's ACS-only 6.75 GiB
plus most of the 1.85 GiB of ASEC that run 3 never loaded. The floor is
fraction-independent for the same reason the CPU floor is (§3a, §4).

| target | one snapshot | 19 retained | + the ~8.4 GiB floor |
|---|---|---|---|
| 1/1000 (v4) | ~16 MiB | ~0.3 GiB | **~8.7 GiB** (matches v4's measured peak) |
| **ceiling (~96,557 source hh)** | 0.93–0.95 GiB | **17.6–18.0 GiB** | **~26 GiB** |
| 1/10 (158,737 source hh) | 1.53–1.56 GiB | 29–30 GiB | ~38 GiB |
| **full source (1,587,376)** | **15.2–15.6 GiB** | **290–296 GiB** | **~300 GiB** |

**The conclusion changes from what an earlier draft of this report said, and it
changes in the architecture's favour.** Memory does **not** bind below the
payload ceiling: the largest build the transport permits today needs about
**26 GiB** — more than this lane's 16 GB authorization, but unremarkable
hardware, and well inside the 87.7 GiB the incumbent already peaks at on this same
machine. What memory does bind is **full source, at ~300 GiB**: a large machine,
but not the ~1.9 TiB the confounded subtraction implied. The retention is still worth
removing — it is the difference between ~300 GiB and roughly 24 GiB (one snapshot
plus the floor) — but it is not the thing that stops a full build. The payload
ceiling is.

Two honest limits on this measurement. It builds every column as `float64`, so
9.7 B/cell is a **lower** bound for a frame carrying string columns, and the
extrapolation assumes the per-cell constant holds at sizes 60× beyond the
largest measured. The per-snapshot footprint it implies — ~15.4 GiB for a
1.70e9-cell full-source population — is **~10 KiB per source household**, which
is about **5.7× leaner** than the incumbent's **57.9 KiB per household**
(94,183,096,320 B = 87.7 GiB peak over 1,588,854 households; the incumbent's own
log labels that peak "94.18GB", decimally). An earlier draft called these "the
same range"; they are not, and the difference runs in the native path's favour.
That is the available sanity check and it passes: the representation is lean.
**Retaining nineteen is the problem, not the
representation** — and it is a runner-level fix, not an architectural one, for
every use of `observed` except the final population and the replay comparisons.

---

## 10. The avoidable cost

**The largest overhead bucket depends on the size of the build, and the report
would be wrong to name only one.** Measured:

| | at any size that runs today (≤ the ceiling) | at full source, if the ceilings were lifted |
|---|---|---|
| total | 5,278.6 CPU-s (v4, 1/1000) | 56,072 CPU-s (15.58 CPU-h) |
| **fixed**, of which *named*: ACS ingest 798 (run 3) + 4 ASEC predictor nodes 957 = **1,755 CPU-s** | **5,234.8 CPU-s = 99.2%**, 1,755 of it named | **5,234.8 CPU-s = 9.3%**, same 1,755 named |
| **linear per-node population work** | 43.8 CPU-s, 0.8% | 43,870 CPU-s, **78.2%** |
| quadratic (`_remapped_expand_memberships` × 5 group entities) | 0.7 CPU-s | 6,967 CPU-s, **12.4%** |

Say that precisely, because the two columns tempt an overstatement. **The FIXED
term is essentially the entire cost of every build that can run on this
architecture today — 99.2% of v4 — and only 9.3% at full source, where per-node
population work takes over.** But only **1,755 CPU-s of that fixed term is
attributed** (ACS ingest 798, measured; the four ASEC predictor nodes 957.2, from
the manifest); the other 3,480 CPU-s is the unattributed remainder of §6d, which
no run reached. So "source ingest is the whole cost today" is true of the *fixed
term*, and only one third of it is measured ingest. At the payload ceiling — the
largest build that actually runs — the fixed term is 66% and per-node population
work is already 34%.

Both are avoidable. In priority order, described and not implemented:

**1. The observer — the single largest avoidable cost at scale, in CPU *and*
memory.** `_population_stamp` (`survey_atomic_geography.py:230`) calls
`_frame_identity` (`survey_population_preparation.py:641`), a ~0.5 µs-per-cell
Python loop, on the **whole frame, on every node**, from the observer at
`graph_atomic_survey_financial.py:1626` — plus again in the post-run verification
loops at `:1895` and `:1910`.

**The per-cell constant, blended properly.** An earlier draft used "~0.5 µs/cell"
and printed four-significant-figure totals off it. Weighting §8d's measured
constants by the frame's actual dtype mix — read from `graph.json`: Int64 154
columns, float64 54, int64 30, string 28, bool 1, boolean 2 — gives
**0.52–0.60 µs/cell** over the 241 measured-dtype columns, so one whole-frame pass
is **0.89–1.02 s** at 1/1000. The 28 string columns are **not** measured by §8d's
bench and are very likely *more* expensive per cell (a UTF-8 encode each), so this
is a lower bound. Every figure below is therefore a range, not a point.

The observer fires on all **28** node executions, so the stamp costs
**24.9–28.7 s** at 1/1000. Be careful which denominator that goes over: only
**22** of those executions have their time inside the 43.8 s population-scaling
term — §6a puts the other six (the four ASEC predictor nodes and both
`observed_geography` runs) in the source-bound bucket. So the stamp is
**22 passes = 19.6–22.5 s, 45–51% of the 43.8 s scaling term** — not the 54% an
earlier draft got by dividing a 28-node numerator by a 22-node denominator. The
remaining ~5 CPU-s of stamping sits inside the term §6a classified as fixed,
**which means the fixed term is not entirely fixed**: a few of its 5,234.8 CPU-s
scale with population.

At full source the stamp across all 28 executions is **24,900–28,700 CPU-s =
6.9–8.0 CPU-hours, 44–51% of the whole build.**
The fix is inside `_frame_identity` itself. Its cost is literally
`for value in series: update_cell(value)`
(`survey_population_preparation.py:688-689`, and `:675-676` over the index) —
one `_frame_cell_encode` call and two `digest.update` calls per cell — over a
quantity that is already a pure function of cell values plus dtype metadata. A
per-column vectorized hash over the column buffer and its null mask seals
exactly the same thing at C speed, and it is a one-function change. The same
callback is what retains nineteen pickled population copies (§9), so fixing it
is the memory fix too.

**What this is *not*: swapping in a digest the store already has.** I checked
that shortcut and it does not work, so the report does not recommend it.
`frame_key` (`keys.py:106-109`) is `_hash_parts("frame", node_key)` — derived
from the **node key alone**, carrying no frame content at all. It is
recipe-addressed, not content-addressed, and comparing it would verify nothing
about cells. A genuine stored content digest does exist — `_payload_table`
records `sha256` + `size` for every payload file (`store.py:140-152`, hashing
through `_sha256_file` at `:132-137`) — but `_population_stamp`'s own docstring
(`survey_atomic_geography.py:230-237`) states that it is a "pure in-process
seal" which must "never [be] persisted or compared across reconstructions",
because it deliberately folds physical storage parts beneath nullable masks. A
stored digest cannot stand in for it. Vectorizing the loop can, and that is the
recommendation.

**2. Replace the per-byte Python record scanners.**
`acs_person_coverage_authentication.py:188-227 _records` and
`asec_coverage_authentication.py:265` exist to find CSV record boundaries under
quote parity and enforce byte ceilings. Both can be done on whole 4 KiB blocks
with `bytes.count`/`bytes.find`/`memoryview` or a compiled regex, with identical
semantics: quote parity is a running count of `0x22`, record ends are `0x0A`
outside quotes, and the ceilings are comparisons on offsets rather than a call
per byte. This removes the 3.38 billion `bytearray.append`, 4.42 billion `len`
and 5.42 billion `_require` calls outright. The same module already handles bytes
in 4 KiB blocks for non-applicable members (`:293-297`) — though that branch only
hashes and does no framing, so it is a precedent for the style, not a drop-in
template (§4). Worth ~265 CPU-s per build at **every** size — the per-byte scanner alone, from
its measured 12.9 MB/s over the 3.38 GB of ACS source. The rest of the 798 CPU-s
is the `_archive`/`_csv_record`/JSON/pandas work that items 4 and 5 target; an
earlier draft credited the whole phase to this one item.

**3. Compute the qualification once per build.**
`qualify_current_survey_predictors` (`current_survey_predictors.py:310`) is not
memoized and runs seven times from three call sites (§8a); four are measured at
957.2 CPU-s, ~239 s each. Three of those four are redundant if the result is
computed once and passed: **-718 CPU-s per build, at every size.**

**4. Stop decoding rows nothing will keep.** This recommendation is narrower
than an earlier draft of this report made it, because the dominant `_inventory`
call has no sample filter to hoist. It is reached from
`acs_population_catalogue.py:152`, which passes **`frozenset()`** — an empty
selection, deliberately, because that call is a whole-source gate over
`member["rows"]`, not native's selected-row gate. So `if cells[0] not in
serialnos` is *always* true there and **every row is scanned, digested and
`_decode_record`-ed into cells, and then discarded**. The gate needs the byte
stream and the row count; it does not need the decode. Skipping `_decode_record`
when `serialnos` is empty is the fix on that path, and it is the cheaper one.

Where hoisting genuinely applies is the selection-aware path:
`acs_housing_universe_source._reconstruct` (`:563`) materializes and writes the
full 292 MB projection (`:566-574`) before calling `_select` at `:575`. Selecting
on SERIALNO first makes a 1/8000 build cost 1/8000 of that work instead of all of
it.

Together with item 2 these are most of the ~798 CPU-s, but note the correction in
item 2: no single one of items 2–5 is worth the whole phase.

**5. Stop re-encoding rows to measure them.** `acs_housing_universe_source.py:360`
computes `len(_json(row))` per row and discards the JSON; `:256-258` re-encodes
all ~280 parsed fields to length-check them when three are kept (`_P_FIELDS`,
`:56`); `:249-254` builds a new `csv.reader` per row.

**6. Guard `_apply_result` on the cache-hit path.** `executor.py:2497` sits
outside both `if result is None:` (`:2406`) and `if not hit:` (`:2571`), so the
**eleven** node executions that hit the store in v4 (two in the prefix lane, nine
in the financial lane) still paid two full frame deep copies and a complete
constructor revalidation — **11.0 CPU-s across all eleven**, of which the nine
financial-lane hits are 8.7 CPU-s. An earlier draft paired the nine-node count
with the eleven-node total.

**7. Stop re-encoding the manifest to build an error label** (`manifest.py:786`),
parsing it twice (`:772`/`:684`) and embedding each receipt twice (`:651-664`) —
all of which handle the per-row EXPAND lineage the executor puts in the receipt
at `executor.py:1274`.

**8. Raise the payload ceilings by changing the transport, not the number** (§5).
Costs ~53 CPU-s at full source to encode; the ceiling is the only reason a full
build is impossible today.

### What the same runs would cost if the bucket went to zero

- **Ingest to zero** (items 2–5): v4's 1/1000 build drops from 5,278.6 CPU-s to
  **~3,763 CPU-s, 71% of today** — counting only what I measured (798 s of ACS
  ingest, 718 s of duplicate qualification). Run 1 would have spent most of its
  1,842 profiled seconds *on the graph* rather than never reaching it. It would
  **not** have completed: ~3,763 CPU-s still exceeds the 1,800 s cap, so the runs
  would have died in a later phase instead of in ingest. The brief's
  three-fraction plan needs this fix **and** a larger cap.
- **Observer to zero** (item 1): at full source the build drops from **15.58 to
  7.6–8.7 CPU-hours** (the stamp is 6.9–8.0 of the 15.58), and the memory
  requirement falls from **~300 GiB to ~24 GiB** (one snapshot plus the ~8.4 GiB
  floor).
- **Both**: full source at **~7.2–8.3 CPU-hours** — and with the 12.7× parallelism
  the incumbent already demonstrates on this machine, that is a wall-clock
  afternoon rather than a day.

---

## 11. Verdict

*The brief asked for a one-paragraph verdict answering exactly two questions.
This is three paragraphs: one per question, plus a third on the merge decision,
because the lane was chartered off a merge question and the answer does not fit
inside either of the two. The deviation is deliberate and this note is the
disclosure; the first two paragraphs answer the two questions on their own.*

**Can this executor, as it stands, build a full US dataset, and at what cost?**
No, and CPU is not the reason. It refuses at **96,200–96,900 source households —
6.1% of the 1,587,376-household source** — with `PAYLOAD_LIMIT`, because the
preparation receipt is a single 64 MiB-bounded JSON document holding one record
per household and per person (`survey_population_preparation.py:1346` → `:108`),
and a full-source payload would be 1,048–1,055 MiB; I did not infer that, I fed
the pilot's own preparation document, scaled, through the repository's own
encoder and watched it refuse at 101,376 households. Memory is the second
constraint but a looser one than an earlier draft of this report claimed: the
observer pickles a full population copy per node and the runner retains all
nineteen, which I measured at 9.6–9.8 bytes per cell per snapshot, putting the
largest build the transport permits at **~26 GiB of RAM** and a full-source build
at **~300 GiB**. And at 1/8000 the build refuses outright, and neither this
lane's receipt nor the default traceback says why.
Where cost *is* the question,
the naive extrapolation is wrong by **94×**: only **43.8 CPU-s** of v4's
5,278.6 CPU-s is population-scaling node work and the rest is a fixed
source-ingest tax that a 1/8000 toy build pays in full — proven by two profilers
of different construction and by ACS call counts that are bit-for-bit identical
across a fourfold change in sample. The dominant exponent is **1**, not 2, though
the one genuinely quadratic path (`population.py:1270-1273`, run once per group
entity over five of them) costs **1.9 CPU-hours — 12% — at full source**, which
is more than an earlier draft of this report said. So the honest cost, if the
ceilings and the memory retention were lifted and nothing else changed, is
**~15.6 CPU-hours on the terms I could measure, plausibly ~30–43 once the
unattributed runner time is included (§6d derives that band)** — against the incumbent's
measured **30.15 CPU-hours** for a 1.59M-household dataset. The catch is that the
incumbent reaches that in **4.72 wall-hours at 12.7× parallelism** while
`run_graph` is one serial loop in one process (`executor.py:2296`), so for the
native path CPU-hours *are* wall-hours: **a day or two, not weeks — but also not
hours, and today, not at all.**

**What has to change for it to build one in hours rather than days?** Four
things, in this order. **(1) Change the transport of the whole-roster receipts** —
preparation and allocation — from one bounded JSON document per run to something
per-shard or columnar. Nothing else matters until this is done, because nothing
else runs; it costs ~53 CPU-s of encoding at full source, so it is a design
decision, not a performance trade-off. **(2) Stop retaining every node's
population** and stop stamping the whole frame on every node: one callback
(`executor.py:2569` → `graph_atomic_survey_financial.py:1625-1626`) is both the
memory wall and **44–51% of the full-source CPU**, and the per-cell Python loop
it runs (`survey_population_preparation.py:688-689`) seals a quantity a
vectorized per-column pass seals identically. **(3) Replace the
byte-at-a-time source scanners** and push the sample filter above the row decode
— that is the whole cost of every build that can run today, it is fixed at every
size, and the fast pattern already exists three lines away in the same file.
**(4) Then parallelise.** After the first three the remaining serial per-node
work is small enough that the honest next question is concurrency, which this
executor does not have and which the incumbent uses to turn 30 CPU-hours into
4.7 wall-hours.

**On the merge decision.** The architectural risk in #893 is real, but it is not
the one the lane was chartered to find. It is *not* that the graph executor is
superlinear — it is linear, and its per-node overhead is modest. It is that
(a) the build refuses above ~96,200–96,900 source households, (b) memory binds below
even that, (c) every build of any size pays several minutes of per-byte Python
scanning over the full source, and (d) a 1/8000 build fails, and neither this
lane's receipt nor the default traceback says why. All four are bounded, local,
and fixable without touching the graph model — but (d) should be understood
before anyone spends a full-source build on this path, because a failure at that
scale costs hours. Part of (d) is my own instrumentation's fault: §3c shows the
cause survives on `__context__` and this lane's harness did not read it. What I
could not establish under a 30-minute CPU cap is the scaling of the runner time
outside the node loop; **one uncapped 1/1000 run under the sampler, about
1.5 CPU-hours, would settle it and the memory slope at the same time**, and I
would not merge on the strength of this report alone without it.
