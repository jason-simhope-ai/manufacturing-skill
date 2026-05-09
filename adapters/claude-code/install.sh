#!/usr/bin/env bash
# manufacturing-skill — Claude Code installer
#
# Usage:
#   bash adapters/claude-code/install.sh                       # interactive picker
#   bash adapters/claude-code/install.sh <profile>             # single profile
#   bash adapters/claude-code/install.sh <p1>,<p2>[,...]       # multi-profile (v0.1.5+)
#   bash adapters/claude-code/install.sh --list                # list available profiles
#   bash adapters/claude-code/install.sh --core-only           # core only, no profile
#   bash adapters/claude-code/install.sh --resolve <p>/<k>/<f> # preview merged extends
#   bash adapters/claude-code/install.sh --list-conflicts [<p1>,<p2>,...]
#                                                              # dry-run conflict scan
#                                                              # (no args → all profile pairs)
#
# Examples:
#   bash adapters/claude-code/install.sh cnc-machining
#   bash adapters/claude-code/install.sh cnc-machining,injection-molding
#   bash adapters/claude-code/install.sh --core-only
#   bash adapters/claude-code/install.sh --resolve cnc-machining/agents/quote-specialist
#   bash adapters/claude-code/install.sh --list-conflicts cnc-machining,injection-molding

set -euo pipefail

PLUGIN_NAME="manufacturing-skill"
DEFAULT_PROFILE="cnc-machining"

# Detect plugin source dir (this script's parent's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ─── Helpers ─────────────────────────────────────────────

# Detect a working Python 3 interpreter. We invoke `--version` as a
# sanity check because Windows ships a fake `python3` shim that
# routes to the Microsoft Store and returns exit 49 on actual use.
detect_python() {
  local cand
  for cand in "${PYTHON3:-}" python3 python py; do
    [[ -z "${cand}" ]] && continue
    if command -v "${cand}" >/dev/null 2>&1; then
      if "${cand}" --version >/dev/null 2>&1; then
        echo "${cand}"
        return 0
      fi
    fi
  done
  return 1
}

# Cache the Python binary lookup. Sets PYTHON_BIN globally.
require_python() {
  if [[ -z "${PYTHON_BIN:-}" ]]; then
    PYTHON_BIN="$(detect_python || true)"
  fi
  if [[ -z "${PYTHON_BIN}" ]]; then
    echo "❌ Python 3 not found. Required for the requested operation." >&2
    echo "   Install python3 (and run \`pip install pyyaml\` if you use \`extends:\`)." >&2
    exit 1
  fi
}

# Return 0 if file has an `extends:` field in its YAML frontmatter
has_extends() {
  awk '/^---$/{c++; if (c==2) exit; next} c==1' "$1" \
    | grep -qE '^extends:[[:space:]]'
}

# Resolve a profile file via the Python resolver, write to target.
# Args: <profile-source> <target-output>
resolve_extends_file() {
  local src="$1"
  local dst="$2"
  require_python
  if ! "${PYTHON_BIN}" -c 'import yaml' 2>/dev/null; then
    echo "❌ PyYAML not installed. Run: ${PYTHON_BIN} -m pip install pyyaml" >&2
    exit 1
  fi
  "${PYTHON_BIN}" "${PLUGIN_ROOT}/adapters/claude-code/_resolve_extends.py" \
    --repo-root "${PLUGIN_ROOT}" \
    resolve "${src}" --out "${dst}"
}

# Parse a comma-separated profile list into the ACTIVE_PROFILES array.
# Whitespace around commas tolerated. Empty entries skipped. Duplicates
# warned and dropped (M2 in spec §4.1).
parse_profile_list() {
  local raw="$1"
  ACTIVE_PROFILES=()
  local IFS=','
  local entry
  # shellcheck disable=SC2206
  local parts=( ${raw} )
  unset IFS
  local seen=" "
  for entry in "${parts[@]}"; do
    # strip leading/trailing whitespace
    entry="$(printf '%s' "${entry}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [[ -z "${entry}" ]] && continue
    if [[ "${seen}" == *" ${entry} "* ]]; then
      echo "WARN: duplicate profile '${entry}' in argument list, ignoring" >&2
      continue
    fi
    seen="${seen}${entry} "
    ACTIVE_PROFILES+=("${entry}")
  done
}

# ─── Argument parsing ────────────────────────────────────
ARG="${1:-}"
CORE_ONLY=false
ACTIVE_PROFILES=()  # bash-3.2 compatible indexed array

case "${ARG}" in
  --resolve)
    REL="${2:-}"
    if [[ -z "${REL}" ]]; then
      echo "Usage: install.sh --resolve <profile>/<kind>/<file>" >&2
      echo "Example: install.sh --resolve cnc-machining/agents/quote-specialist" >&2
      exit 1
    fi
    SRC="${PLUGIN_ROOT}/profiles/${REL}.md"
    if [[ ! -f "${SRC}" ]]; then
      echo "❌ profile file not found: ${SRC}" >&2
      exit 1
    fi
    require_python
    "${PYTHON_BIN}" "${PLUGIN_ROOT}/adapters/claude-code/_resolve_extends.py" \
      --repo-root "${PLUGIN_ROOT}" resolve "${SRC}"
    exit $?
    ;;
  --list-conflicts)
    require_python
    REL="${2:-}"
    if [[ -z "${REL}" ]]; then
      # No-args form: scan every pair from plugin.json's available list
      "${PYTHON_BIN}" "${PLUGIN_ROOT}/adapters/claude-code/_multiprofile.py" \
        --repo-root "${PLUGIN_ROOT}" scan-all
      exit $?
    fi
    parse_profile_list "${REL}"
    if [[ ${#ACTIVE_PROFILES[@]} -lt 2 ]]; then
      echo "Need at least 2 profiles for conflict scan." >&2
      echo "Run with no args to scan all profile pairs." >&2
      exit 1
    fi
    "${PYTHON_BIN}" "${PLUGIN_ROOT}/adapters/claude-code/_multiprofile.py" \
      --repo-root "${PLUGIN_ROOT}" scan "${ACTIVE_PROFILES[@]}"
    exit $?
    ;;
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
    ;;
  -h|--help)
    sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  "")
    # No arg → interactive if TTY, otherwise default
    if [[ -t 0 ]] && [[ -t 1 ]]; then
      echo "════════════════════════════════════════════════"
      echo " manufacturing-skill installer · choose profile(s)"
      echo "════════════════════════════════════════════════"
      echo ""
      i=1
      declare -a PICKER_PROFILES
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
          PICKER_PROFILES[i]="${name}"
          ((i++))
        fi
      done
      printf "  %s) %s %-22s %s\n" "0" "🧪" "(core-only, no profile)" "— try the framework first"
      echo ""
      echo "  Default: ${DEFAULT_PROFILE}  (press Enter to accept)"
      echo "  Tip: enter \`1,2\` for multi-profile (v0.1.5+)"
      echo ""
      read -r -p "Select [0-$((i-1)), comma-separated for multi]: " choice
      choice="${choice:-}"
      if [[ -z "${choice}" ]]; then
        ACTIVE_PROFILES=("${DEFAULT_PROFILE}")
      elif [[ "${choice}" == "0" ]]; then
        CORE_ONLY=true
      else
        # Parse comma-separated picker selections
        local_ifs="${IFS}"
        IFS=','
        # shellcheck disable=SC2206
        choice_parts=( ${choice} )
        IFS="${local_ifs}"
        for c in "${choice_parts[@]}"; do
          c="$(printf '%s' "${c}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
          [[ -z "${c}" ]] && continue
          if [[ "${c}" =~ ^[0-9]+$ ]] && [[ -n "${PICKER_PROFILES[c]:-}" ]]; then
            ACTIVE_PROFILES+=("${PICKER_PROFILES[c]}")
          else
            echo "❌ Invalid selection: ${c}"
            exit 1
          fi
        done
      fi
    else
      # Non-interactive (CI etc.) — use default
      ACTIVE_PROFILES=("${DEFAULT_PROFILE}")
    fi
    ;;
  *)
    parse_profile_list "${ARG}"
    if [[ ${#ACTIVE_PROFILES[@]} -eq 0 ]]; then
      echo "❌ No valid profiles in argument: ${ARG}" >&2
      exit 1
    fi
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
  echo "Profile(s)    : ${ACTIVE_PROFILES[*]}"
fi
echo ""

# ─── Validation + conflict scan (BEFORE backup, per spec M5) ───
# A bad profile list must not destroy a working install.

if [[ "${CORE_ONLY}" == "false" ]]; then
  # Validate every profile exists
  for prof in "${ACTIVE_PROFILES[@]}"; do
    if [[ ! -d "${PLUGIN_ROOT}/profiles/${prof}" ]]; then
      echo "❌ Profile not found: ${prof}"
      echo "   Run with --list to see available profiles."
      exit 1
    fi
  done

  # Conflict scan when more than one profile
  if [[ ${#ACTIVE_PROFILES[@]} -gt 1 ]]; then
    require_python
    echo "→ Scanning for file conflicts across ${#ACTIVE_PROFILES[@]} profiles..."
    if ! "${PYTHON_BIN}" "${PLUGIN_ROOT}/adapters/claude-code/_multiprofile.py" \
         --repo-root "${PLUGIN_ROOT}" scan "${ACTIVE_PROFILES[@]}"; then
      echo ""
      echo "❌ Cannot install — conflicting files in active profiles." >&2
      echo "   Resolve by either:" >&2
      echo "     (a) Pick only one of the conflicting profiles" >&2
      echo "     (b) Create a merged profile that combines both" >&2
      echo "   See docs/profile-development.md#多-profile-同時-active" >&2
      exit 1
    fi
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

# ─── Backup existing install (after validation passes) ───
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

# Stage 2: overlay each active profile in order. The conflict scan
# above guarantees no file collisions between profiles, so order
# within Stage 2 doesn't affect the final state.
# Files with `extends:` frontmatter are merged via _resolve_extends.py;
# files without are copied as-is (v0.1.x whole-file override).
if [[ "${CORE_ONLY}" == "false" ]]; then
  for prof in "${ACTIVE_PROFILES[@]}"; do
    echo "→ Overlaying profile: ${prof}..."
    PROF_DIR="${PLUGIN_ROOT}/profiles/${prof}"
    for sub in agents skills know-how hooks; do
      if [[ ! -d "${PROF_DIR}/${sub}" ]]; then continue; fi
      for f in "${PROF_DIR}/${sub}/"*.md; do
        [[ -f "${f}" ]] || continue
        base="$(basename "${f}")"
        # Skip _templates/ stubs
        case "${base}" in _*) continue;; esac
        target="${TARGET_DIR}/${sub}/${base}"
        if has_extends "${f}"; then
          echo "  ↳ resolving extends: ${sub}/${base}"
          resolve_extends_file "${f}" "${target}"
        else
          cp "${f}" "${target}"
        fi
      done
    done
  done
else
  echo "→ Skipping profile overlay (core-only mode)"
fi

# Stage 3: copy plugin manifest + profile manifest(s).
# Singular `active-profile.json` retained indefinitely as a copy of the
# first profile's manifest for backwards compatibility (spec §6.2 / M4).
# Plural `active-profiles.json` is generated by the aggregator when
# more than one profile is active (or for symmetry / forward-compat
# even with one).
cp "${PLUGIN_ROOT}/plugin.json" "${TARGET_DIR}/plugin.json"
if [[ "${CORE_ONLY}" == "false" ]]; then
  cp "${PLUGIN_ROOT}/profiles/${ACTIVE_PROFILES[0]}/profile.json" \
     "${TARGET_DIR}/active-profile.json"
  if [[ ${#ACTIVE_PROFILES[@]} -gt 0 ]]; then
    require_python
    "${PYTHON_BIN}" "${PLUGIN_ROOT}/adapters/claude-code/_multiprofile.py" \
      --repo-root "${PLUGIN_ROOT}" \
      aggregate "${ACTIVE_PROFILES[@]}" \
      --out "${TARGET_DIR}/active-profiles.json"
  fi
fi

# Stage 4: write install marker (.installed).
# Both singular `activeProfile` (for v0.1.x readers) and plural
# `activeProfiles` (canonical from v0.1.5) are written.
if [[ "${CORE_ONLY}" == "true" ]]; then
  ACTIVE_PROFILE_FIRST="(core-only)"
  ACTIVE_PROFILES_JSON="[]"
else
  ACTIVE_PROFILE_FIRST="${ACTIVE_PROFILES[0]}"
  # Build JSON array literal: ["a","b","c"]
  ACTIVE_PROFILES_JSON=$(printf '"%s",' "${ACTIVE_PROFILES[@]}" | sed 's/,$//')
  ACTIVE_PROFILES_JSON="[${ACTIVE_PROFILES_JSON}]"
fi
PLUGIN_VERSION=$(grep -oE '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "${PLUGIN_ROOT}/plugin.json" \
  | head -1 \
  | sed -E 's/.*"([^"]*)"$/\1/')
cat > "${TARGET_DIR}/.installed" <<EOF
{
  "installedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "pluginVersion": "${PLUGIN_VERSION}",
  "activeProfile": "${ACTIVE_PROFILE_FIRST}",
  "activeProfiles": ${ACTIVE_PROFILES_JSON},
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
elif [[ ${#ACTIVE_PROFILES[@]} -gt 1 ]]; then
  echo "   /quote @examples/sample-drawing/bracket.md"
  echo "   /install-profile <list>     # change active profiles (replaces)"
  echo "   /add-profile <name>         # add another profile to the active set"
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
