# Blast Radius

This is an entry for the RWX **Blast Radius** challenge. Given a patch to [sqlglot](https://github.com/tobymao/sqlglot) at `eb11aec`, it picks the tests that can catch the change and packs them onto at most 8 workers.

- The challenge and its rules are in [docs/CHALLENGE.md](docs/CHALLENGE.md). The exact scoring is in [SCORING.md](SCORING.md).
- The approach, the repo layout, and the working rules are in [AGENTS.md](AGENTS.md).
- The score history is in [docs/LOG.md](docs/LOG.md).

## Run it

You need Docker, make, and Python 3.9 or newer.

```sh
make local        # quick host run on the 30 sample commits
make sample       # build the image, run it under the scorer's limits, and score it
make sample-cpu   # the same, plus measured CPU seconds
make sqlglot lab  # pinned sqlglot checkout and the labeling environment, used to build maps
```

The image reads `/data/commits/*.patch` and `/data/tests.json`. It prints one JSON line per commit to stdout and sends its logs to stderr.

## How it works

It is still the starter baseline: every test on every commit, over 3 workers. The plan is to select tests from per-test coverage and fixture-read maps built from the pinned commit. See AGENTS.md § Approach.
