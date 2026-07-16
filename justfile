# justfile — tmux-nerd-icons
# Universal recipe API per rain/just-spec

default:
    @just --list --unsorted

# Lint: ruff check + format check + mypy
lint:
    uv run ruff check scripts/nerd_icons
    uv run ruff format --check scripts/nerd_icons
    uv run mypy scripts/nerd_icons

# Test: conformance suite (skips gracefully when test vectors are absent)
test:
    bash tests/test_conformance.sh

# No buildable artifact for this tmux plugin
build:
    @echo "build: no artifact to build for a tmux plugin"

# Pre-push gate: lint + test + build
verify: lint test build

# Bump version in pyproject.toml
bump level="patch":
    uv version --bump {{level}}

# Bump + verify + jj commit + push to owned remotes (JUST_PUSH_REMOTES overrides).
# Failed verify aborts after the bump — retry bumps again; version gaps accepted.
commit +message:
    #!/usr/bin/env bash
    set -euo pipefail
    MESSAGE={{ quote(message) }}
    SKIP_VERIFY=0
    case " $MESSAGE " in
        *" --no-verify "*)
            SKIP_VERIFY=1
            MESSAGE="${MESSAGE/ --no-verify/}"
            MESSAGE="${MESSAGE/--no-verify /}"
            MESSAGE="${MESSAGE/--no-verify/}"
            ;;
    esac
    [ -n "$MESSAGE" ] || { echo "error: commit message required" >&2; exit 1; }
    just bump patch
    [ "$SKIP_VERIFY" = 1 ] || just verify
    jj describe -m "$MESSAGE"
    BOOKMARK=$(jj log -r '@ | @-' --no-graph \
        -T 'local_bookmarks.map(|b| b.name() ++ "\n").join("")' | head -1)
    if [ -z "$BOOKMARK" ]; then
        for n in trunk main master; do
            if jj bookmark list "$n" 2>/dev/null | grep "^$n:" >/dev/null; then
                BOOKMARK="$n"; break
            fi
        done
    fi
    [ -n "$BOOKMARK" ] || { echo "error: no main/trunk/master bookmark found" >&2; exit 1; }
    jj bookmark set "$BOOKMARK" -r @
    REMOTES=$(jj git remote list | awk '{print $1}')
    [ -n "$REMOTES" ] || { echo "warn: no remotes configured, skipping push" >&2; exit 0; }
    # Push ONLY to remotes we own. A fork's `upstream` (and any other
    # third-party remote) is FETCH-ONLY: pushing our main there is an
    # incursion into someone else's repo. Overridable per-repo with
    # JUST_PUSH_REMOTES="a b".
    #
    # Skips are announced, never silent — a remote that quietly stops being
    # pushed is the same class of bug this recipe exists to prevent (a push
    # that looks successful while not going where you think). If you own a
    # remote under a different name, name it here or set JUST_PUSH_REMOTES.
    PUSH_TARGETS="${JUST_PUSH_REMOTES:-}"
    if [ -z "$PUSH_TARGETS" ]; then
        for remote in $REMOTES; do
            case "$remote" in
                origin|forgejo|github) PUSH_TARGETS="$PUSH_TARGETS $remote" ;;
                *) echo "» skip → $remote (fetch-only; not a push target)" >&2 ;;
            esac
        done
    fi
    [ -n "$PUSH_TARGETS" ] || { echo "error: no push targets among remotes: $REMOTES" >&2; exit 1; }
    PUSH_FAILED=0
    for remote in $PUSH_TARGETS; do
        echo "» push → $remote"
        jj git push --remote "$remote" --bookmark "$BOOKMARK" --allow-new \
            || { echo "error: push to $remote failed" >&2; PUSH_FAILED=1; }
    done
    # A successful push makes @ immutable, and jj then auto-creates a
    # fresh empty child; an unconditional `jj new` would stack a second
    # empty on top, stranding an undescribed commit that blocks the next
    # push. Only start a new change when @ is still the described commit.
    WC_STATE=$(jj log -r @ --no-graph \
        -T 'if(empty, "empty", "dirty") ++ "-" ++ if(description, "desc", "nodesc")')
    [ "$WC_STATE" = "empty-nodesc" ] || jj new
    exit $PUSH_FAILED
