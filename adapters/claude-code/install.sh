#!/usr/bin/env bash
# manufacturing-skill — Claude Code installer
#
# Usage:
#   bash adapters/claude-code/install.sh                  # interactive picker
#   bash adapters/claude-code/install.sh <profile_name>   # explicit
#   bash adapters/claude-code/install.sh --list           # list available
#   bash adapters/claude-code/install.sh --core-only      # no profile, core only
#
# Examples:
#   bash adapters/claude-code/install.sh cnc-machining
#   bash adapters/claude-code/install.sh injection-molding
#   bash adapters/claude-code/install.sh --core-only       # try without commitment

set -euo pipefail

PLUGIN_NAME="manufacturing-skill"
DEFAULT_PROFILE="cnc-machining"

# Detect plugin source dir (this script's parent's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ─── Argument parsing ────────────────────────────────────
ARG="${1:-}"
CORE_ONLY=false
PROFILE=""

case "${ARG}" in
  --list)
    echo "Available profiles:"
    for p in "${PLUGIN_ROOT}/profiles/"*/; do
      name="$(basename "${p}")"
      if [[ -f "${p}/profile.json" ]]; then
        status="$(grep -oE '"status"[[:space:]]*:[[:space:]]*"[^"]*"' "${p}/profile.json" | head -1 | sed 's/.*"\([^"]*\)"$/\1/')"
        if [[ -z "${status}" ]]; then status="complete"; fi
        case "${status}" in
          complete) icon="✅";;
          stub)     icon="🚧";;
          *)        icon="❓";;
        esac
        echo "  ${icon} ${name} (${status})"
      fi
    done
    exit 0
    ;;
  --core-only)
    CORE_ONLY=true
    PROFILE=""
    ;;
  -h|--help)
    sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  "")
    # No arg → interactive if TTY, otherwise default
    if [[ -t 0 ]] && [[ -t 1 ]]; then
      echo "════════════════════════════════════════════════"
      echo " manufacturing-skill installer · choose a profile"
      echo "════════════════════════════════════════════════"
      echo ""
      i=1
      declare -a PROFILE_LIST
      for p in "${PLUGIN_ROOT}/profiles/"*/; do
        name="$(basename "${p}")"
        if [[ -f "${p}/profile.json" ]]; then
          status="$(grep -oE '"status"[[:space:]]*:[[:space:]]*"[^"]*"' "${p}/profile.json" | head -1 | sed 's/.*"\([^"]*\)"$/\1/')"
          if [[ -z "${status}" ]]; then status="complete"; fi
          case "${status}" in
            complete) icon="✅";;
            stub)     icon="🚧 stub";;
            *)        icon="❓";;
          esac
          printf "  %s) %s %-22s %s\n" "${i}" "${icon}" "${name}" ""
          PROFILE_LIST[i]="${name}"
          ((i++))
        fi
      done
      printf "  %s) %s %-22s %s\n" "0" "🧪" "(core-only, no profile)" "— try the framework first"
      echo ""
      echo "  Default: ${DEFAULT_PROFILE}  (press Enter to accept)"
      echo ""
      read -r -p "Select [0-$((i-1))]: " choice
      choice="${choice:-}"
      if [[ -z "${choice}" ]]; then
        PROFILE="${DEFAULT_PROFILE}"
      elif [[ "${choice}" == "0" ]]; then
        CORE_ONLY=true
        PROFILE=""
      elif [[ "${choice}" =~ ^[0-9]+$ ]] && [[ -n "${PROFILE_LIST[choice]:-}" ]]; then
        PROFILE="${PROFILE_LIST[choice]}"
      else
        echo "❌ Invalid selection."
        exit 1
      fi
    else
      # Non-interactive (CI etc.) — use default
      PROFILE="${DEFAULT_PROFILE}"
    fi
    ;;
  *)
    PROFILE="${ARG}"
    ;;
esac

# Detect Claude Code config dir (cross-platform)
detect_claude_dir() {
  if [[ -n "${CLAUDE_CONFIG_DIR:-}" ]]; then
    echo "${CLAUDE_CONFIG_DIR}"
  elif [[ "${OSTYPE:-}" == "msys" || "${OSTYPE:-}" == "cygwin" || -n "${WINDIR:-}" ]]; then
    echo "${HOME}/.claude"
  elif [[ "${OSTYPE:-}" == "darwin"* ]]; then
    echo "${HOME}/.claude"
  else
    echo "${HOME}/.claude"
  fi
}

CLAUDE_DIR="$(detect_claude_dir)"
TARGET_DIR="${CLAUDE_DIR}/plugins/${PLUGIN_NAME}"

echo ""
echo "════════════════════════════════════════════════"
echo " manufacturing-skill Claude Code installer"
echo "════════════════════════════════════════════════"
echo ""
echo "Plugin source : ${PLUGIN_ROOT}"
echo "Claude dir    : ${CLAUDE_DIR}"
echo "Install target: ${TARGET_DIR}"
if [[ "${CORE_ONLY}" == "true" ]]; then
  echo "Profile       : (core-only, no vertical)"
else
  echo "Profile       : ${PROFILE}"
fi
echo ""

# Validate profile exists (when not core-only)
if [[ "${CORE_ONLY}" == "false" ]]; then
  if [[ ! -d "${PLUGIN_ROOT}/profiles/${PROFILE}" ]]; then
    echo "❌ Profile not found: ${PROFILE}"
    echo "   Run with --list to see available profiles."
    exit 1
  fi
fi

# Validate Claude Code dir exists
if [[ ! -d "${CLAUDE_DIR}" ]]; then
  echo "⚠️ Claude Code config dir not found at ${CLAUDE_DIR}"
  echo "   Create it? [y/N]"
  read -r answer
  # Lowercase in a bash-3.2-compatible way (macOS default bash is still 3.2)
  answer_lower="$(printf '%s' "${answer}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${answer_lower}" != "y" ]]; then
    echo "Aborted."
    exit 1
  fi
  mkdir -p "${CLAUDE_DIR}"
fi

# Backup existing install
if [[ -d "${TARGET_DIR}" ]]; then
  BACKUP="${TARGET_DIR}.bak.$(date +%Y%m%d-%H%M%S)"
  echo "ℹ️ Existing install found, backing up to ${BACKUP}"
  mv "${TARGET_DIR}" "${BACKUP}"
fi

mkdir -p "${TARGET_DIR}"

# Stage 1: copy core
echo "→ Installing core layer..."
cp -r "${PLUGIN_ROOT}/core/commands" "${TARGET_DIR}/commands"
cp -r "${PLUGIN_ROOT}/core/agents"   "${TARGET_DIR}/agents"
cp -r "${PLUGIN_ROOT}/core/skills"   "${TARGET_DIR}/skills"
cp -r "${PLUGIN_ROOT}/core/hooks"    "${TARGET_DIR}/hooks"
cp -r "${PLUGIN_ROOT}/core/know-how" "${TARGET_DIR}/know-how"

# Stage 2: overlay profile (filename-based override) — skip if --core-only
if [[ "${CORE_ONLY}" == "false" ]]; then
  echo "→ Overlaying profile: ${PROFILE}..."
  PROF_DIR="${PLUGIN_ROOT}/profiles/${PROFILE}"
  for sub in agents skills know-how hooks; do
    if [[ -d "${PROF_DIR}/${sub}" ]]; then
      cp -r "${PROF_DIR}/${sub}/." "${TARGET_DIR}/${sub}/" 2>/dev/null || true
    fi
  done
else
  echo "→ Skipping profile overlay (core-only mode)"
fi

# Stage 3: copy plugin manifest + profile manifest
cp "${PLUGIN_ROOT}/plugin.json" "${TARGET_DIR}/plugin.json"
if [[ "${CORE_ONLY}" == "false" ]]; then
  cp "${PLUGIN_ROOT}/profiles/${PROFILE}/profile.json" "${TARGET_DIR}/active-profile.json"
fi

# Stage 4: write install marker
ACTIVE_PROFILE_VAL="${PROFILE}"
if [[ "${CORE_ONLY}" == "true" ]]; then ACTIVE_PROFILE_VAL="(core-only)"; fi
cat > "${TARGET_DIR}/.installed" <<EOF
{
  "installedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "pluginVersion": "$(grep -oE '"version"[^,]*' "${PLUGIN_ROOT}/plugin.json" | head -1)",
  "activeProfile": "${ACTIVE_PROFILE_VAL}",
  "source": "${PLUGIN_ROOT}"
}
EOF

echo ""
echo "✅ Installation complete."
echo ""
echo "Try in Claude Code:"
echo "   /manufacturing                # see plugin status"
echo "   /manufacturing init           # interactive setup wizard"
if [[ "${CORE_ONLY}" == "true" ]]; then
  echo "   /quote 「我做不鏽鋼五金件，幫我寫一份報價流程」"
  echo "   /install-profile <name>     # add a vertical profile later"
else
  echo "   /quote @examples/sample-drawing/bracket.md"
  echo "   /install-profile <other>    # switch profiles"
fi
echo ""
echo "Docs:"
echo "   - README.zh-TW.md"
echo "   - manufacturing.md (the soul doc)"
echo "   - docs/explainers/04-懶人包-5分鐘上手.html (start here ★)"
echo "   - docs/explainers/01-架構總覽.html"
