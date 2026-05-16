#!/usr/bin/env bash
# Symlink the telegram-deployer skill into ~/.claude/skills/ for local development.
# After running this, the skill is invokable in your Claude Code as "telegram-deployer".

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_SRC="$REPO_ROOT/skills/telegram-deployer"
SKILL_DST="$HOME/.claude/skills/telegram-deployer"

if [[ ! -d "$SKILL_SRC" ]]; then
    echo "❌ Source skill not found: $SKILL_SRC" >&2
    exit 1
fi

mkdir -p "$HOME/.claude/skills"

if [[ -e "$SKILL_DST" || -L "$SKILL_DST" ]]; then
    echo "⚠️  $SKILL_DST already exists — removing"
    rm -rf "$SKILL_DST"
fi

# On Windows Git Bash, ln -s creates a junction by default; both work for Claude Code
ln -s "$SKILL_SRC" "$SKILL_DST"
echo "✅ Linked $SKILL_DST → $SKILL_SRC"
echo "Restart Claude Code (or start a new session) and the 'telegram-deployer' skill will be available."
