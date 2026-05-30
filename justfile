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
    #!/usr/bin/env bash
    set -euo pipefail
    file="pyproject.toml"
    current=$(grep '^version = ' "$file" | head -1 | sed 's/version = "\(.*\)"/\1/')
    IFS='.' read -r major minor patch <<< "$current"
    case "{{ level }}" in
        major) major=$((major+1)); minor=0; patch=0 ;;
        minor) minor=$((minor+1)); patch=0 ;;
        patch) patch=$((patch+1)) ;;
        *) echo "error: level must be patch, minor, or major" >&2; exit 1 ;;
    esac
    next="${major}.${minor}.${patch}"
    sed -i "s/^version = \"${current}\"/version = \"${next}\"/" "$file"
    echo "bump: ${current} → ${next}"

# Verify + bump + jj commit + push to all remotes
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
    [ "$SKIP_VERIFY" = 1 ] || just verify
    just bump patch
    jj describe -m "$MESSAGE"
    BOOKMARK=$(jj log -r '@ | @-' --no-graph -T 'bookmarks ++ "\n"' 2>/dev/null \
        | tr ' ' '\n' | grep -v '@' | grep -v '^$' | sed 's/[*?]\+$//' | head -1)
    if [ -z "$BOOKMARK" ]; then
        for n in trunk main master; do
            if jj bookmark list "$n" 2>/dev/null | grep -q "^$n:"; then
                BOOKMARK="$n"; break
            fi
        done
    fi
    [ -n "$BOOKMARK" ] || { echo "error: no main/trunk/master bookmark found" >&2; exit 1; }
    jj bookmark set "$BOOKMARK" -r @
    REMOTES=$(jj git remote list | awk '{print $1}')
    [ -n "$REMOTES" ] || { echo "warn: no remotes configured, skipping push" >&2; exit 0; }
    for remote in $REMOTES; do
        echo "» push → $remote"
        jj git push --remote "$remote" --bookmark "$BOOKMARK" --allow-new \
            || echo "warn: push to $remote failed"
    done
    jj new
