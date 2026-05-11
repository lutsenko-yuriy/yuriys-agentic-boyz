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
echo "── Git host ─────────────────────────────────────"
echo "Where pull requests / merge requests live."
echo "Examples: GitHub, GitLab, Bitbucket"
echo ""
GIT_HOST=$(ask "Git host (e.g. GitHub)")

echo ""
echo "── Project management tool ──────────────────────"
echo "This is the tool where issues, milestones, and the backlog live."
echo "Examples: Linear, Jira, Shortcut"
echo "Leave blank to use the built-in issue tracker of your Git host"
echo "(${GIT_HOST} Issues) — zero config required."
echo ""
PM_TOOL=$(ask "PM tool name (leave blank to use ${GIT_HOST} Issues)" "")
if [[ -z "$PM_TOOL" ]]; then
  PM_TOOL="${GIT_HOST} Issues"
  echo "  → Using ${PM_TOOL} (built-in repo issue tracker)"
fi
ISSUE_PREFIX=$(ask "Issue identifier prefix (e.g. HAB, APP, PROJ — leave blank for tools like GitHub Issues that use numbers)" "")
PM_PROJECT_URL=$(ask "PM project URL (link to the board / backlog — leave blank if using repo issues)" "")

echo ""
echo "── Experiment tracking ──────────────────────────"
echo "Tool used to run A/B tests or feature flags."
echo "Examples: Firebase A/B Testing, Statsig, LaunchDarkly, PostHog"
echo ""
EXPERIMENT_TOOL=$(ask "Experiment tool name" "Firebase A/B Testing")

echo ""
echo "── AI models ────────────────────────────────────"
echo "Surveying available models on this machine..."
echo ""

# ── auto-detect models ────────────────────────────────────────────────────────

_detected_models=()

# Ollama — list pulled models (name:tag, strip :latest suffix for brevity)
if command -v ollama &>/dev/null && ollama list &>/dev/null 2>&1; then
  while IFS= read -r line; do
    model=$(echo "$line" | awk '{print $1}')
    # strip :latest tag
    model="${model%:latest}"
    [[ -n "$model" ]] && _detected_models+=("$model")
  done < <(ollama list 2>/dev/null | tail -n +2)
  if [[ ${#_detected_models[@]} -gt 0 ]]; then
    echo "  Ollama models found: ${_detected_models[*]}"
  else
    echo "  Ollama is installed but no models are pulled yet."
  fi
fi

# Cloud API keys — report which providers are reachable
if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "  ANTHROPIC_API_KEY detected — Anthropic models available"
  _detected_models+=("claude-opus-4-7" "claude-sonnet-4-6" "claude-haiku-4-5")
fi
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  echo "  OPENAI_API_KEY detected — OpenAI models available"
  _detected_models+=("gpt-4o" "gpt-4o-mini")
fi
if [[ -n "${GEMINI_API_KEY:-}" || -n "${GOOGLE_API_KEY:-}" ]]; then
  echo "  Google API key detected — Gemini models available"
  _detected_models+=("gemini-1.5-pro" "gemini-1.5-flash")
fi
if [[ -n "${GROQ_API_KEY:-}" ]]; then
  echo "  GROQ_API_KEY detected — Groq models available"
  _detected_models+=("llama-3.3-70b-versatile" "llama-3.1-8b-instant")
fi
if [[ -n "${MISTRAL_API_KEY:-}" ]]; then
  echo "  MISTRAL_API_KEY detected — Mistral models available"
  _detected_models+=("mistral-large-latest" "mistral-small-latest")
fi

# Build comma-separated suggestion from detected list (deduplicated)
_suggestion=""
if [[ ${#_detected_models[@]} -gt 0 ]]; then
  _suggestion=$(printf '%s\n' "${_detected_models[@]}" | awk '!seen[$0]++' | paste -sd ',' -)
  echo ""
  echo "  Suggested: ${_suggestion}"
fi

echo ""
echo "Edit the list — add, remove, or rename models as needed."
echo "The calibrate skill will map them to effort/reasoning tiers."
echo ""
AVAILABLE_MODELS=$(ask "Available models (comma-separated)" "${_suggestion}")

echo ""
echo "── AI attribution ───────────────────────────────"
echo "These appear in commit messages and PR/MR bodies."
echo ""
AI_COMMIT_TRAILER=$(ask "Commit co-author line (e.g. Co-Authored-By: AI Assistant <ai@example.com>)" "")
AI_TOOL_CREDIT=$(ask "PR/MR body AI credit line (e.g. 🤖 Generated with Claude Code)" "")

# ── substitute ───────────────────────────────────────────────────────────────

echo ""
echo "Substituting placeholders..."

replace "{{PROJECT_NAME}}"        "$PROJECT_NAME"
replace "{{PROJECT_DESCRIPTION}}" "$PROJECT_DESCRIPTION"
replace "{{STACK}}"               "$STACK"
replace "{{ARCHITECTURE_SUMMARY}}" "$ARCHITECTURE_SUMMARY"
replace "{{CODE_STYLE}}"          "$CODE_STYLE"
replace "{{PM_TOOL}}"             "$PM_TOOL"
replace "{{ISSUE_PREFIX}}"        "$ISSUE_PREFIX"
replace "{{PM_PROJECT_URL}}"      "$PM_PROJECT_URL"
replace "{{EXPERIMENT_TOOL}}"     "$EXPERIMENT_TOOL"
replace "{{GIT_HOST}}"            "$GIT_HOST"
replace "{{AVAILABLE_MODELS}}"   "$AVAILABLE_MODELS"
replace "{{AI_COMMIT_TRAILER}}"  "$AI_COMMIT_TRAILER"
replace "{{AI_TOOL_CREDIT}}"     "$AI_TOOL_CREDIT"

# ── done ─────────────────────────────────────────────────────────────────────

echo ""
echo "✅ Done! Next steps:"
echo ""
echo "  1. Review CLAUDE.md and fill in the 'Common Commands' section for your stack."
echo "  2. Fill in docs/PRODUCT_SPEC.md with your feature requirements."
echo "  3. Fill in docs/ARCHITECTURE.md with your directory structure and layer rules."
echo "  4. Add your local binary paths and PM/Git tool auth notes to CLAUDE.local.md (not committed)."
echo "  5. Open Claude Code and start your first session — the product-owner-backlog skill"
echo "     will present an empty backlog and ask what goes into the first release."
echo ""
echo "  PM tool MCP (if applicable): run \`/mcp\` in Claude Code the first time to authenticate."
echo ""
