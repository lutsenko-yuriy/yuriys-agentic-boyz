#!/usr/bin/env bash
# setup.sh — substitute {{PLACEHOLDERS}} with your project's values.
# Run once after cloning / using this template:  ./setup.sh

set -euo pipefail

# ── helpers ──────────────────────────────────────────────────────────────────

ask() {
  local prompt="$1" default="${2:-}"
  if [[ -n "$default" ]]; then
    read -r -p "$prompt [$default]: " value
    echo "${value:-$default}"
  else
    read -r -p "$prompt: " value
    while [[ -z "$value" ]]; do
      echo "  (required)" >&2
      read -r -p "$prompt: " value
    done
    echo "$value"
  fi
}

replace() {
  # replace all occurrences of $1 with $2 in all tracked text files
  local placeholder="$1" value="$2"
  # escape for sed
  local escaped_value
  escaped_value=$(printf '%s\n' "$value" | sed 's/[[\.*^$()+?{|]/\\&/g; s/]/\\]/g')
  grep -rl --include="*.md" --include="*.json" --include="*.sh" --include="*.yaml" --include="*.yml" \
    "$placeholder" . 2>/dev/null \
    | xargs sed -i "" "s|${placeholder}|${escaped_value}|g"
}

# ── collect values ────────────────────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Claude multi-agent project setup           ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

PROJECT_NAME=$(ask "Project name (e.g. My App)")
PROJECT_DESCRIPTION=$(ask "One-line project description")
STACK=$(ask "Tech stack (e.g. Flutter/Dart, Node/TypeScript, Rails/Ruby)" "")
ARCHITECTURE_SUMMARY=$(ask "One-line architecture summary (e.g. Vertical-slice with Riverpod + sqflite)")
CODE_STYLE=$(ask "Code style reference (e.g. 'Flutter style guide' or 'Airbnb JS')" "Project conventions")

echo ""
echo "── Linear ───────────────────────────────────────"
echo "Find these in your Linear workspace settings and project URL."
echo ""
LINEAR_WORKSPACE_NAME=$(ask "Linear workspace name")
LINEAR_TEAM_ID=$(ask "Linear team ID (UUID)")
LINEAR_PROJECT_ID=$(ask "Linear project ID (UUID)")
LINEAR_ISSUE_PREFIX=$(ask "Linear issue prefix (e.g. HAB, APP, PROJ)")
LINEAR_PROJECT_URL=$(ask "Linear project URL (https://linear.app/...)" "https://linear.app")

# ── substitute ───────────────────────────────────────────────────────────────

echo ""
echo "Substituting placeholders..."

replace "{{PROJECT_NAME}}"          "$PROJECT_NAME"
replace "{{PROJECT_DESCRIPTION}}"   "$PROJECT_DESCRIPTION"
replace "{{STACK}}"                 "$STACK"
replace "{{ARCHITECTURE_SUMMARY}}"  "$ARCHITECTURE_SUMMARY"
replace "{{CODE_STYLE}}"            "$CODE_STYLE"
replace "{{LINEAR_WORKSPACE_NAME}}" "$LINEAR_WORKSPACE_NAME"
replace "{{LINEAR_TEAM_ID}}"        "$LINEAR_TEAM_ID"
replace "{{LINEAR_PROJECT_ID}}"     "$LINEAR_PROJECT_ID"
replace "{{LINEAR_ISSUE_PREFIX}}"   "$LINEAR_ISSUE_PREFIX"
replace "{{LINEAR_PROJECT_URL}}"    "$LINEAR_PROJECT_URL"

# ── done ─────────────────────────────────────────────────────────────────────

echo ""
echo "✅ Done! Next steps:"
echo ""
echo "  1. Review CLAUDE.md and fill in the 'Common Commands' section for your stack."
echo "  2. Fill in docs/PRODUCT_SPEC.md with your feature requirements."
echo "  3. Fill in docs/ARCHITECTURE.md with your directory structure and layer rules."
echo "  4. Add your local binary paths to CLAUDE.local.md (not committed)."
echo "  5. Open Claude Code and start your first session — the Product Owner agent"
echo "     will present an empty backlog and ask what goes into the first release."
echo ""
echo "  Linear MCP auth: run \`/mcp\` in Claude Code the first time to authenticate."
echo ""
