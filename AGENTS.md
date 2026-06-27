# Agent Instructions

## Scope

This repo is a tmux plugin that maps process names to Nerd Font icons. It has two layers:
- A Bash plugin entrypoint (`nerd-icons.tmux`, `scripts/`) that hooks into tmux
- A Python code-generation layer (`scripts/nerd_icons/`) that produces `generated-bubble-bar.conf`

Changes to the Python layer require running `just lint` (ruff + mypy). Changes to Bash scripts should be validated against `.shellcheckrc`.

## Non-goals

- Do not add Nix packaging or a flake.nix — this is intentionally a pure Bash/Python plugin.
- Do not add CI — no `.forgejo/` workflows are needed for a non-flake repo.
- Do not modify `uv.lock` manually — always use `uv` to update dependencies.

## Conventions

- Version lives in `pyproject.toml`. Use `just bump [patch|minor|major]` to increment.
- The generated config (`generated-bubble-bar.conf`) is committed — regenerate with `scripts/nerd_icons/` tooling after icon map changes.
- Lint gate: `uv run ruff check` + `uv run ruff format --check` + `uv run mypy` (all under `scripts/nerd_icons/`).
- Test gate: `bash tests/test_conformance.sh`.
- Commit gate: `just commit "msg"` — runs verify, bumps patch, then pushes.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:7510c1e2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
