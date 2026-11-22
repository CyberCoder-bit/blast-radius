# AGENTS.md: RWX Blast Radius

These are the instructions for any coding agent in this repo. `CLAUDE.md` imports this file. Where things disagree, `SCORING.md` wins on scoring and `docs/CHALLENGE.md` wins on rules.

## The task

The image gets patches at `/data/commits/<id>.patch`. Each is a unified diff against sqlglot at `eb11aec4be8cb2122afe713a4816662c3f0fb2fa`, and each stands alone. For every patch, print one stdout line, `{"commit":"<id>","workers":[[12,845],[3]]}`, naming which tests from `/data/tests.json` to run, split over at most 8 workers. `"workers":[]` runs nothing. A lower total wins. Only the **final** counts: unseen commits, about 1.5× the practice count, including **kinds of change not seen in practice**.

**Cutoff: Sun 11:00 AM EST.** Submissions are limited to about one per hour, so never submit a build that hasn't passed `make sample`.

## Scoring economics

- Each commit costs `max worker load + 2 s × workers`, and `[]` costs 0. A test's load is `round(seconds*1000)` ms.
- Leaving out any failing test adds **300 s**. The commit's own cost still counts.
- The **CPU seconds** of every process in the container, user plus system, are added to the total.
- The board takes the median of 3 runs. CPU time is the only part that varies between runs.

What follows from that:

- One miss (300 s) costs about 3× running the whole suite serially (about 103 s), or about 7× the 3-worker baseline (about 40 s a commit). Never trade a plausible miss for a few seconds.
- Every non-empty answer pays at least 2 s. Add workers only while `max load + 2k` keeps falling: try k = 1..8 with longest-first packing and keep the best k.
- A few tests dominate: `test_parser.py::test_max_nodes` (28.8 s, #1490), `test_executor.py::test_execute_tpcds` (21.5 s, #1106), `test_generator.py::test_generator_memory` (6.7 s, #1224), then tpch/optimized_tpch (about 3.5–3.9 s). Most tests take under 0.05 s, so once a worker exists they are almost free to add. The expensive ones need real evidence.
- Include a test when `P(it fails and nothing else selected catches the miss) × 300 s` is more than its marginal cost. The penalty counts per commit, not per test, so one missed failing test costs as much as missing ten.
- An empty answer is correct and free when nothing breaks. That was 11 of the 30 sample commits.
- CPU is charged. Python startup plus our code runs once per batch. Keep the selector stdlib-only with lazy, small imports. Running sqlglot tests at run time is allowed, but every CPU second they take is charged.

## Hard rules

Breaking a rule gets the run rejected or the team disqualified.

1. **No answer lookup tables.** Nothing maps a patch, a patch hash, or a kind of edit to the tests it breaks. `sample/answers.json` is only for local scoring: the selector and the map builders must never read it, and no heuristic may be keyed to specific sample commits. Maps must come from the **pinned sqlglot commit**, through coverage, imports, fixture reads, or the AST. Top entries' code gets read, so every rule needs a defensible general reason.
2. **stdout carries only answer lines.** One line per commit, no repeated commit, no repeated test within a line, only numbers from tests.json, at most 8 non-empty workers, and at most 2 MB in total. Logs go to **stderr**. A crash or a stray print rejects the whole run, so a per-commit failure must fall back to a conservative answer, never to an exception.
3. **Build.** The `Dockerfile` stays at the repo root. Keep the pinned `FROM python:3.13-slim@sha256:e48f…` digest: it is the labeling image, and its Python and SQLite decide test behaviour. Downloads may come only from PyPI, npm, Docker Hub, GitHub releases at a fixed tag, or sqlglot at the pinned commit. Nothing may come from an address we control. The build gets 4 cores, 8 GB, 10 min, and network.
4. **Repo size is at most 20 MB.** No submodules and no LFS. Commit generated maps as plain files and aim for under 10 MB.
5. **The run has** no network, 2 cores, 4 GB, and **3 min for the whole batch** (4.5 min in the final), as user `nobody` with `HOME=/tmp`, a read-only disk, an empty **64 MB `/tmp`**, and at most 256 processes. Every file in the image must be readable by `nobody`.
6. Work only in our own repo, with no code from other teams.
7. **Never edit the kit files:** `score.py`, `SCORING.md`, `sample/`, `requirements.lock`, `docs/KIT_README.md`.

## What "fails" means

A test fails when pytest reports a failure, an error, or a timeout, or when its file can't be imported. When any subtest fails, the whole test fails. pytest 9 can print `PASSED` next to `SUBFAILED` lines, and that test failed. The labels were made with `SKIP_INTEGRATION=0`, so the executor tests run. One test is skipped in their environment: `tests.json["skipped"]` lists it, and it has no number.

**Comment-only changes are not promised to be harmless.** A `#` can land inside a string literal, inside SQL in a fixture (`tests/fixtures/**/*.sql` use `#` and `--` meaningfully, for example `# title:` and `# execute: true` directives), in a docstring, or on a line that tests check by source or line number. Classify comments by tokenizing the file, never with a regex on the diff line.

## Data facts from the sample kit

- `tests.json` has 1620 numbered tests in 58 files, about 103 s serial. Per-file seconds: test_executor 31.6, test_parser 29.1, test_optimizer 19.8, test_generator 6.8, and everything else under 2.
- The 30 sample commits break down into code 16, fixture 8, comment 3, and multi 3. The patches are tiny single-hunk mutations: operator flips (`and`→`or`, `is`→`==`), injected tokens, inserted comments, and edited fixture lines.
- The failure sets range from empty to about 40 tests across many files. For example, one `sqlglot/serde.py` mutation broke the executor and optimizer suites.
- Many optimizer tests each read one fixture file under `tests/fixtures/` through `tests/helpers.py` (`load_sql_fixtures`, `load_sql_fixture_pairs`). Derive which tests open which fixture by tracing file reads at the pinned commit, not from the answers.
- The pinned checkout takes about 15 MB (`sqlglot/` 3.5 MB, `tests/` 8.8 MB), so a patched copy fits in the 64 MB `/tmp` if needed.
- The run-everything baseline scores 1210.5 s simulated on the sample with 0 misses. The board baseline is 1614.1 s, which suggests the practice set has about 40 commits.

## Repo layout

```
Dockerfile            submission image (root, required); CMD python -m selector
.dockerignore         ALLOWLIST: only selector/ and maps/ enter the image
Makefile              kit targets + ours (see Commands)
AGENTS.md CLAUDE.md   agent instructions (this file is canonical)
README.md             public overview of the approach
SCORING.md score.py requirements.lock sample/    starter kit, do not edit
selector/             runtime code: stdlib only, runs in the image
  __main__.py         entry point; reads $BLAST_DATA (default /data)
maps/                 committed generated maps (plain files) the selector loads
tools/                offline/dev scripts (not in the image)
  lab.Dockerfile      labeling env: pinned base + requirements.lock
  cputime.py          CPU meter used by make sample-cpu
docs/
  CHALLENGE.md        full challenge statement and rules
  KIT_README.md       starter-kit README, verbatim
  LOG.md              experiment and submission log, append-only
vendor/sqlglot/       pinned sqlglot checkout (gitignored; make sqlglot)
```

`vendor/sqlglot/` has its own `AGENTS.md` and `CLAUDE.md`. Those are sqlglot's contributor instructions and **do not apply here**. Treat that directory as read-only reference data.

As the selector grows, split `selector/` into modules: `patch.py` (diff parsing into old-side line ranges), `maps.py` (loading), `classify.py` (comment, docstring, code, and fixture edits), `select.py` (risk to a test set), and `schedule.py` (best-k packing).

## Commands

| Command | What it does |
| --- | --- |
| `make local` | Runs the selector on the host against `sample/` and scores it. A seconds-fast loop with no Docker and no CPU measurement. |
| `make sample` | The official check: builds the image, runs it under the scorer's limits, and scores it. **Run it before every submission.** |
| `make sample-cpu` | Same as `make sample`, but also measures the selector's CPU inside the container and prints a board-like `Total`. |
| `make check` | Checks the output format only. |
| `make sqlglot` | Shallow-clones sqlglot at the pinned commit into `vendor/sqlglot`. |
| `make lab` | Builds the lab image: the labeling environment, with the pinned base plus `requirements.lock`, `SKIP_INTEGRATION=0`, and `PYTHONPATH=/work/vendor/sqlglot`. |
| `make lab-run CMD="…"` | Runs a command in the lab, with the working directory at `vendor/sqlglot` and the repo mounted at `/work`. Example: `make lab-run CMD="python -m pytest -q -p no:cacheprovider tests/test_serde.py"`. |
| `make lab-shell` | Opens an interactive shell in the lab. |

Run sqlglot's tests and build maps **in the lab, not on the host**. Host Python is 3.14, but the labels came from 3.13 with the pinned SQLite and packages. Coverage line attribution and skip behaviour can differ.

## Working conventions

- **Evidence over intuition.** Every selector change gets `make sample`, and the result (simulated seconds, misses, CPU) goes into `docs/LOG.md`, along with board results after each submission.
- **Don't overfit the sample.** Thirty commits is a tiny set, and the final adds new kinds of change. Prefer principled signals (coverage, imports, fixture reads, how far the AST changed), with conservative fallbacks for anything unrecognised: a non-`.py` file, a new file, a deleted file, `__init__.py`, a module-level or class-body edit, a decorator, the tokenizer or core expression classes. When in doubt, include the test.
- **Map builders are reproducible.** Every file in `maps/` is produced by a script in `tools/` from the pinned commit, with the exact command in its docstring. Maps are compact: deduplicate test sets, intern them, and gzip if large.
- **Prefer committed maps to build-time work.** A Docker build that runs the test suite costs minutes on every submission and risks the 10-minute cap.
- **Be deterministic.** The same input gives the same output: no randomness, no wall-clock heuristics.
- **Stay inside the budget.** The final has about 60 commits in 4.5 min on 2 cores. Anything that runs tests at run time needs a hard global time budget, with a fallback to the static selection.
- **Keep the image lean.** Only `selector/` and `maps/` go in. Precompile `.pyc` at build time, because the disk is read-only at run time.

## Approach

This is the current plan. Update it as decisions land.

1. **Coverage map.** In the lab, run each test with per-test line coverage at the pinned commit (`sys.monitoring` on 3.13 is fast, or coverage.py dynamic contexts). Record `(file, line) → test set`. Keep **import-time** lines (module and class bodies, decorators, defaults) separately: everything that imports the module executes them.
2. **Fixture and data-read map.** Record which non-`.py` files each test opens. For line-addressed fixtures such as the optimizer `.sql` files, record which test consumes which statement.
3. **Patch analysis.** Parse the diff into files and old-side line ranges, then classify each hunk: whitespace, true comment (by tokenizer), docstring, code, fixture, test file, or new or deleted file.
4. **Selection.** Union the covering tests, widen for risky edit sites (import-time code, shared helpers, the tokenizer, parser or generator core), and drop what can't fail.
5. **Scheduling.** Pack longest-first for each k from 1 to 8 and pick the k that minimises `max load + 2k`.
6. **Optional runtime verification.** Copy the sources to `/tmp`, apply the patch, and run the candidate tests to prune them or prove `[]`. This only pays when the CPU spent is less than the seconds saved, for example to avoid #1490 or #1106 or to confirm a change breaks nothing. It needs sqlglot and the test dependencies in the image.
