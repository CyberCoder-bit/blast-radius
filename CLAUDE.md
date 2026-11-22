@AGENTS.md

## Claude Code specifics

- `AGENTS.md`, imported above, is canonical. Put shared guidance there, and keep this file for Claude Code-only notes.
- Run long jobs in the background: Docker builds, `make sample`, lab test runs, and map builds. A full sqlglot test run with coverage takes minutes.
- Scratch files and throwaway analysis go in the session scratchpad, not the repo. Results worth keeping go in `docs/LOG.md`, and generated artifacts go in `maps/` through a script in `tools/`.
- Quote the actual `make sample` or `make sample-cpu` output before claiming a score changed.
- Don't commit, push, or create the GitHub repo unless asked. The user picks which commit gets submitted.
- When the working directory is inside `vendor/sqlglot`, its own `CLAUDE.md` loads. Ignore it, because it is sqlglot's contributor guide, not ours.
- To check a hypothesis about why a test fails, apply the patch to a scratch copy of `vendor/sqlglot` in the lab and run only that test. Never edit `vendor/sqlglot` itself.
