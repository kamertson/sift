# Sift Case Study: Werkzeug vs. httpie

**A code-quality scoring pipeline, two real repositories, and two scoring bugs
caught by checking whether the results actually made sense.**

## The problem

Code models are typically fine-tuned on large, unfiltered scrapes of public
code. Public code skews mediocre — for every well-designed, well-tested
function, there are many rushed or undocumented ones. Sift is a tool that
scores and filters code by quality *before* it becomes training data, so a
team fine-tuning on their own codebase (or curating a public dataset) can
train on their best code instead of their average code.

This case study runs Sift against two real, well-known Python repositories —
[Werkzeug](https://github.com/pallets/werkzeug) (the WSGI toolkit underlying
Flask) and [HTTPie](https://github.com/httpie/cli) (a popular command-line
HTTP client) — to validate the scoring approach and see what it actually
surfaces.

## Methodology

Sift ingests a repository, parses each file with Python's `ast` module, and
extracts one chunk per top-level function or method. Each chunk is scored on
two signals:

- **Complexity** (via `radon`): cyclomatic complexity and maintainability
  index, normalized to 0–100.
- **Lint** (via `ruff`): violation count, normalized to 0–100.

The two signals are averaged into a `final_score`, and the report surfaces
score distribution statistics plus the five highest- and lowest-scoring
chunks with explanations. All numbers in this write-up come directly from
`sift scan` output, cross-checked with `sift compare` for the side-by-side
table below — nothing here was hand-calculated.

## What we found — and fixed

The first scan of Werkzeug (1,903 chunks) produced a result that looked
plausible at a glance but fell apart under inspection. Two distinct scoring
bugs surfaced this way, both because the *lowest-scoring* code didn't
actually look bad when read by hand.

### Bug 1: Lint scoring lost context

The lint scorer ran `ruff` on each chunk in isolation — a function's source
code copied into a bare temp file, stripped of its imports, its class, and
everything else in the module. Ruff then flagged references to names that
were only "undefined" because the surrounding file had been removed, not
because the code was actually wrong. Every chunk with 10+ such false
positives hit a hard floor of `0.0`.

This produced a systematic bias toward brevity: a two-line `__repr__` sailed
through with nothing to reference and scored 100, while a 95-line WSGI
environment builder (`EnvironBuilder.__init__`) — legitimately complex but
*correct* — scored near zero, purely because ruff couldn't see the imports
and class context it depended on.

**Fix:** run `ruff` once per whole file (with full context intact), then
attribute each diagnostic to whichever chunk's line range it falls inside.

**Effect:** every chunk previously stuck at `lint_score: 0.0` moved to
`100.0`. Werkzeug's mean score rose from 78.6 to 92.4 and its minimum score
rose from 9.8 to 59.8 — confirming those were false positives, not real
issues.

### Bug 2: Complexity scoring penalized test code

After the lint fix, every chunk remaining in the "lowest scoring" list was
either a test function or a many-parameter builder/`__init__`. This wasn't
noise — it was a consistent pattern: `radon`'s complexity metric penalizes
length and branching, and test functions are conventionally long and linear
(many assertions, straightforward setup) by design, not by poor engineering.

This mattered beyond individual chunk scores — it distorted the
repo-to-repo comparison. In an earlier comparison run against a different,
smaller community-maintained repository, that project scored slightly
*higher* than Werkzeug overall — directly contrary to what a human familiar
with both projects would expect: Werkzeug is a rigorously maintained,
widely-depended-upon framework component. The distortion traced back to
test-function chunks dragging down whichever repo had proportionally more
of them relative to how "clean" that repo's tests happened to look under a
naive complexity metric.

**Fix:** detect test code (`test_*.py` / `*_test.py` files, files under a
`tests/`/`test/` directory, `test_*` functions, `Test*` classes) and exclude
it from scoring by default, with a `--include-tests` flag to opt back in.

## Results after both fixes

| Metric | Werkzeug | httpie |
|---|---|---|
| Total chunks extracted | 1,903 | 1,022 |
| Test chunks excluded | 621 | 524 |
| **Test chunk ratio** | **32.6%** | **51.3%** |
| Chunks scored (production code) | 1,282 | 498 |
| Mean score | 94.5 | 93.3 |
| Median score | 97.5 | 97.5 |
| Min score | 59.8 | 61.3 |

Once test-function noise was removed, both projects land close together —
identical medians (97.5), with Werkzeug slightly ahead on mean (94.5 vs.
93.3). That closeness is itself informative: both are mature, actively
maintained projects with real engineering discipline, and the scorer
reflects that they're much more alike than a hypothesis of "polished
framework vs. scrappy community tool" would have predicted going in. The
value of the fix wasn't to force a particular winner — it was to remove a
systematic distortion (test-function penalties) that would otherwise have
made the comparison unreliable in either direction.

The test-chunk ratio itself turned out to be an interesting secondary
finding: httpie is 51% test code by chunk count against Werkzeug's 33% — a
meaningfully different testing culture between the two projects, surfaced
automatically as a side effect of the exclusion logic rather than something
we set out to measure directly.

### What the lowest-scoring production code actually looks like

With both biases removed, the remaining low scorers in both repos are
believable candidates for "code a human reviewer would also flag as dense" —
which is the signal a quality scorer should actually produce.

In Werkzeug: `MultipartEncoder.send_event`, `DebugTraceback.render_traceback_html`,
`Rule._parse_rule` (routing-rule parsing — inherently branchy), and
`GuardedIterator.close`.

In httpie: `raw_main` and `program` (the CLI's top-level entry points, which
naturally accumulate branching as they dispatch to different execution
paths), `interpret` (nested-JSON argument parsing), and `collect_messages`
(HTTP request/response streaming). These are exactly the kind of
orchestration-heavy functions that legitimately sit at the complex end of a
CLI tool — a good sign the scorer is finding real structural complexity
rather than penalizing arbitrary code.

## Limitations

- **Two signals only.** Complexity and lint violations are cheap, fast
  proxies for quality — they don't capture design quality, naming, test
  coverage, or whether the code is actually correct. An LLM-judge signal
  (sampling chunks and rating them against a rubric) is planned to calibrate
  and validate these cheaper heuristics against something closer to human
  judgment.
- **`EnvironBuilder.__init__` still scores low**, and this one is arguably
  correct to flag even though the code itself is legitimate — it's a good
  example of where "high complexity" and "bad code" genuinely diverge (a
  WSGI environment builder needs many parameters by the nature of the
  problem). This is a reminder that complexity scoring should be read as
  "worth a closer look," not "definitely bad."
- **Python-only, for now.** The scoring pipeline is architected to be
  language-agnostic, but the current parser (`ast`) and scorers (`radon`,
  `ruff`) are Python-specific. See the README roadmap for the planned
  `tree-sitter`-based path to JS/TS, Go, Java, and C support.

## Why this matters

Two scoring bugs — one from stripped-context lint analysis, one from
conflating test-code style with poor design — were each significant enough
to distort how two well-known repositories compared by score, before they
were caught and fixed. Neither bug was found by inspecting the code in the
abstract; both were found by running the tool against real repositories and
noticing that the "worst" code it flagged didn't actually look bad. That's
the core argument for treating code-quality filtering as something worth
validating against real data rather than trusting a naive static-analysis
score at face value: a filter with hidden biases doesn't just produce noisy
training data, it can produce training data curated *backwards*.
