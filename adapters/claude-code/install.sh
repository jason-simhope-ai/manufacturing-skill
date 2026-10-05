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
#
# Safety:
#   - Every check (profile names, profile dirs, python3 / PyYAML when needed,
#     conflict scan) runs BEFORE anything under ~/.claude is touched.
#   - The new tree is built next to the target and swapped in with `mv`; the
#     old install is moved to <target>.bak.<timestamp>.<pid> and restored
#     automatically if the swap fails. Only the newest 3 backups are kept.
#   - python3 is needed only for multi-profile installs and `extends:` files
#     (those also need PyYAML). A single plain profile installs without it.
#   - If ~/.claude is missing and stdin is not a terminal, the installer
#     cannot ask; it exits 2 without changing anything. Create the dir first.
# Exit codes: 0 ok · 1 error (existing install untouched) · 2 ~/.claude missing
#   (non-interactive)

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
    echo "   Install python3 (plus \`pip install pyyaml\` for profiles that use \`extends:\`)." >&2
    exit 1
  fi
}

# Return 0 if file has an `extends:` field in its YAML frontmatter.
# CRLF-tolerant: a trailing \r is stripped from every line first (a Windows
# checkout with autocrlf turns "---" into "---\r"). Single awk, no pipe, so
# pipefail cannot misreport an early exit.
has_extends() {
  awk '
    { sub(/\r$/, "") }
    /^---$/ { c++; if (c == 2) exit; next }
    c == 1 && /^extends:[[:space:]]/ { found = 1; exit }
    END { exit !found }
  ' "$1"
}

# JSON-escape a string for use between double quotes (pure sed fallback:
# backslash and double quote; used only when python3 is unavailable).
json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
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

# Read a profile.json "status" field; a missing status means "complete".
profile_status() {
  local s
  s="$({ grep -oE '"status"[[:space:]]*:[[:space:]]*"[^"]*"' "$1" || true; } | head -1 | sed 's/.*"\([^"]*\)"$/\1/')"
  printf '%s\n' "${s:-complete}"
}

# Read a profile.json "version" field (empty if absent).
profile_version() {
  { grep -oE '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$1" || true; } | head -1 | sed 's/.*"\([^"]*\)"$/\1/'
}

# Print the strings of a profile.json "warnings" array, one per line.
# Pure awk so it works without python3 (single-profile installs).
profile_warnings() {
  awk '
    !inw {
      if (match($0, /"warnings"[[:space:]]*:[[:space:]]*\[/)) {
        inw = 1; $0 = substr($0, RSTART + RLENGTH)
      } else next
    }
    {
      s = $0
      while (length(s) > 0) {
        c = substr(s, 1, 1)
        if (c == "]") exit
        if (c == "\"" && match(s, /^"([^"\\]|\\.)*"/)) {
          print substr(s, 2, RLENGTH - 2); s = substr(s, RLENGTH + 1); continue
        }
        s = substr(s, 2)
      }
    }' "$1"
}

# Profile names: letters, digits, "-" and "_" only, not starting with "-".
# Rejects "..", "/", spaces and glob characters before any path is built.
valid_profile_name() {
  local re='^[A-Za-z0-9_][A-Za-z0-9_-]*$'
  [[ "$1" =~ $re ]]
}

# Parse a comma-separated profile list into the ACTIVE_PROFILES array.
# Whitespace around commas tolerated. Empty entries skipped. Duplicates
# warned and dropped (M2 in spec §4.1). `read -a` splits without glob
# expansion, so `*` stays literal and is rejected by valid_profile_name.
parse_profile_list() {
  local raw="$1"
  ACTIVE_PROFILES=()
  local entry
  local parts=()
  IFS=',' read -r -a parts <<< "${raw}" || true
  local seen=" "
  for entry in ${parts[@]+"${parts[@]}"}; do
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
    for prof in ${ACTIVE_PROFILES[@]+"${ACTIVE_PROFILES[@]}"}; do
      if ! valid_profile_name "${prof}"; then
        echo "❌ Invalid profile name: '${prof}' (allowed: letters, digits, '-' and '_')" >&2
        exit 1
      fi
    done
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
        status="$(profile_status "${p}/profile.json")"
        case "${status}" in
          complete) icon="✅";;
          alpha)    icon="🧪";;
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
    awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"
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
          status="$(profile_status "${p}/profile.json")"
          case "${status}" in
            complete) icon="✅";;
            alpha)    icon="🧪 alpha";;
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
        choice_parts=()
        IFS=',' read -r -a choice_parts <<< "${choice}" || true
        for c in ${choice_parts[@]+"${choice_parts[@]}"}; do
          c="$(printf '%s' "${c}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
          [[ -z "${c}" ]] && continue
          # 10# so "08" / "09" are decimal, not an invalid octal subscript
          if [[ "${c}" =~ ^[0-9]+$ ]] && [[ -n "${PICKER_PROFILES[$((10#${c}))]:-}" ]]; then
            ACTIVE_PROFILES+=("${PICKER_PROFILES[$((10#${c}))]}")
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

# ─── Preflight (BEFORE anything is touched, per spec M5) ──────────
# Every check that can fail runs here. A bad argument, a missing tool or
# a conflicting profile list must leave a working install exactly as it is.

# Usage: preflight_fail <error> [hint lines...]
preflight_fail() {
  echo "❌ $1" >&2
  shift
  local line
  for line in "$@"; do echo "   ${line}" >&2; done
  echo "   Nothing was changed; any existing install is untouched." >&2
  exit 1
}

NEED_PYTHON_FOR=""   # human-readable reasons; empty = python optional
NEED_YAML=false

if [[ "${CORE_ONLY}" == "false" ]]; then
  # 1. Names and profile dirs
  for prof in "${ACTIVE_PROFILES[@]}"; do
    if ! valid_profile_name "${prof}"; then
      preflight_fail "Invalid profile name: '${prof}' (allowed: letters, digits, '-' and '_'; no '/', '..', spaces or wildcards)."
    fi
    if [[ ! -f "${PLUGIN_ROOT}/profiles/${prof}/profile.json" ]]; then
      preflight_fail "Profile not found: ${prof}" "Run with --list to see available profiles."
    fi
  done

  # 2. Which tools does this install actually need?
  if [[ ${#ACTIVE_PROFILES[@]} -gt 1 ]]; then
    NEED_PYTHON_FOR="multi-profile conflict scan + active-profiles.json"
  fi
  for prof in "${ACTIVE_PROFILES[@]}"; do
    for sub in agents skills know-how hooks; do
      for f in "${PLUGIN_ROOT}/profiles/${prof}/${sub}/"*.md; do
        [[ -f "${f}" ]] || continue
        case "$(basename "${f}")" in _*) continue;; esac
        if has_extends "${f}"; then
          NEED_YAML=true
          NEED_PYTHON_FOR="${NEED_PYTHON_FOR:+${NEED_PYTHON_FOR}; }extends: in profiles/${prof}/${sub}/$(basename "${f}")"
          break 2
        fi
      done
    done
  done

  PYTHON_BIN="$(detect_python || true)"
  if [[ -n "${NEED_PYTHON_FOR}" && -z "${PYTHON_BIN}" ]]; then
    preflight_fail "Python 3 not found. Needed for: ${NEED_PYTHON_FOR}." "Install python3 and re-run."
  fi
  if [[ "${NEED_YAML}" == "true" ]] && ! "${PYTHON_BIN}" -c 'import yaml' 2>/dev/null; then
    preflight_fail "PyYAML not installed. Needed to resolve \`extends:\` profile files." \
      "Run: ${PYTHON_BIN} -m pip install pyyaml"
  fi

  # 3. Conflict scan when more than one profile
  if [[ ${#ACTIVE_PROFILES[@]} -gt 1 ]]; then
    echo "→ Scanning for file conflicts across ${#ACTIVE_PROFILES[@]} profiles..."
    if ! "${PYTHON_BIN}" "${PLUGIN_ROOT}/adapters/claude-code/_multiprofile.py" \
         --repo-root "${PLUGIN_ROOT}" scan "${ACTIVE_PROFILES[@]}"; then
      echo ""
      preflight_fail "Cannot install — conflicting files in active profiles." \
        "Resolve by either:" \
        "  (a) Pick only one of the conflicting profiles" \
        "  (b) Create a merged profile that combines both" \
        "See docs/profile-development.md#多-profile-同時-active"
    fi
  fi
fi

# 4. Claude Code config dir
if [[ ! -d "${CLAUDE_DIR}" ]]; then
  echo "⚠️ Claude Code config dir not found at ${CLAUDE_DIR}"
  if [[ ! -t 0 ]]; then
    echo "❌ stdin is not a terminal, so the installer cannot ask whether to create it." >&2
    echo "   Create it first (mkdir -p \"${CLAUDE_DIR}\") or start Claude Code once, then re-run." >&2
    echo "   Nothing was changed." >&2
    exit 2
  fi
  echo "   Create it? [y/N]"
  answer=""
  read -r answer || answer=""
  # Lowercase in a bash-3.2-compatible way (macOS default bash is still 3.2)
  answer_lower="$(printf '%s' "${answer}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${answer_lower}" != "y" ]]; then
    echo "Aborted."
    exit 1
  fi
  mkdir -p "${CLAUDE_DIR}"
fi

# ─── Build the new tree next to the target, then swap ──────────────
# STAGE_DIR lives in the same plugins/ dir as TARGET_DIR, so both `mv`s
# below are same-filesystem renames. The old install is only moved after
# the new tree is complete; if anything fails after that, the EXIT trap
# moves it back.

PLUGINS_DIR="$(dirname "${TARGET_DIR}")"
STAGE_DIR=""
BACKUP=""
SWAP_STATE="none"   # none → building → old-moved → done
KEEP_BACKUPS=3

on_exit() {
  local rc=$?
  if [[ "${SWAP_STATE}" == "old-moved" ]]; then
    [[ ${rc} -eq 0 ]] && rc=1
    if [[ ! -e "${TARGET_DIR}" && ! -L "${TARGET_DIR}" ]] && mv "${BACKUP}" "${TARGET_DIR}"; then
      echo "❌ Install failed during the swap; previous install restored at ${TARGET_DIR}" >&2
    else
      echo "❌ Install failed during the swap and the previous install could not be restored automatically." >&2
      echo "   It is intact at: ${BACKUP}" >&2
      echo "   Restore with:   rm -rf '${TARGET_DIR}' && mv '${BACKUP}' '${TARGET_DIR}'" >&2
    fi
  elif [[ "${SWAP_STATE}" == "building" && ${rc} -ne 0 ]]; then
    echo "❌ Install failed while building the new tree; existing install untouched." >&2
  fi
  if [[ -n "${STAGE_DIR}" && -d "${STAGE_DIR}" ]]; then
    rm -rf "${STAGE_DIR}"
  fi
  exit "${rc}"
}
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

mkdir -p "${PLUGINS_DIR}"
stage_try="${PLUGINS_DIR}/.${PLUGIN_NAME}.new.$$.${RANDOM}"
mkdir "${stage_try}"   # no -p: fails rather than reuse an existing dir
STAGE_DIR="${stage_try}"
SWAP_STATE="building"

# Stage 1: copy core
echo "→ Installing core layer..."
cp -r "${PLUGIN_ROOT}/core/commands" "${STAGE_DIR}/commands"
cp -r "${PLUGIN_ROOT}/core/agents"   "${STAGE_DIR}/agents"
cp -r "${PLUGIN_ROOT}/core/skills"   "${STAGE_DIR}/skills"
cp -r "${PLUGIN_ROOT}/core/hooks"    "${STAGE_DIR}/hooks"
cp -r "${PLUGIN_ROOT}/core/know-how" "${STAGE_DIR}/know-how"

# Stage 2: overlay each active profile in order. The conflict scan
# above guarantees no file collisions between profiles, so order
# within Stage 2 doesn't affect the final state.
# Files with `extends:` frontmatter are merged via _resolve_extends.py;
# files without are copied as-is (v0.1.x whole-file override).
OVERLAY_COUNTS=()   # parallel to ACTIVE_PROFILES
if [[ "${CORE_ONLY}" == "false" ]]; then
  for prof in "${ACTIVE_PROFILES[@]}"; do
    echo "→ Overlaying profile: ${prof}..."
    PROF_DIR="${PLUGIN_ROOT}/profiles/${prof}"
    n_files=0
    for sub in agents skills know-how hooks; do
      if [[ ! -d "${PROF_DIR}/${sub}" ]]; then continue; fi
      for f in "${PROF_DIR}/${sub}/"*.md; do
        [[ -f "${f}" ]] || continue
        base="$(basename "${f}")"
        # Skip _templates/ stubs
        case "${base}" in _*) continue;; esac
        target="${STAGE_DIR}/${sub}/${base}"
        if has_extends "${f}"; then
          echo "  ↳ resolving extends: ${sub}/${base}"
          resolve_extends_file "${f}" "${target}"
        else
          cp "${f}" "${target}"
        fi
        n_files=$((n_files + 1))
      done
    done
    OVERLAY_COUNTS+=("${n_files}")
  done
else
  echo "→ Skipping profile overlay (core-only mode)"
fi

# Stage 3: copy plugin manifest + profile manifest(s).
# Singular `active-profile.json` retained indefinitely as a copy of the
# first profile's manifest for backwards compatibility (spec §6.2 / M4).
# Plural `active-profiles.json` is generated by the aggregator. It needs
# python3: always present for multi-profile (checked in preflight); for a
# single profile without python3 it is skipped and readers fall back to
# the singular file.
cp "${PLUGIN_ROOT}/plugin.json" "${STAGE_DIR}/plugin.json"
if [[ "${CORE_ONLY}" == "false" ]]; then
  cp "${PLUGIN_ROOT}/profiles/${ACTIVE_PROFILES[0]}/profile.json" \
     "${STAGE_DIR}/active-profile.json"
  if [[ -n "${PYTHON_BIN}" ]]; then
    "${PYTHON_BIN}" "${PLUGIN_ROOT}/adapters/claude-code/_multiprofile.py" \
      --repo-root "${PLUGIN_ROOT}" \
      aggregate "${ACTIVE_PROFILES[@]}" \
      --out "${STAGE_DIR}/active-profiles.json"
  else
    echo "ℹ️ python3 not found — skipping active-profiles.json (single profile; readers use active-profile.json)"
  fi
fi

# Stage 4: write install marker (.installed).
# Both singular `activeProfile` (for v0.1.x readers) and plural
# `activeProfiles` (canonical from v0.1.5) are written.
if [[ "${CORE_ONLY}" == "true" ]]; then
  ACTIVE_PROFILE_FIRST="(core-only)"
  ACTIVE_PROFILES_LIST=()
else
  ACTIVE_PROFILE_FIRST="${ACTIVE_PROFILES[0]}"
  ACTIVE_PROFILES_LIST=("${ACTIVE_PROFILES[@]}")
fi
PLUGIN_VERSION=$(grep -oE '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "${PLUGIN_ROOT}/plugin.json" \
  | head -1 \
  | sed -E 's/.*"([^"]*)"$/\1/')
INSTALLED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [[ -z "${PYTHON_BIN:-}" ]]; then   # --core-only skips the preflight lookup
  PYTHON_BIN="$(detect_python || true)"
fi
if [[ -n "${PYTHON_BIN}" ]]; then
  # Proper JSON via python (handles every special character in the path).
  # ${arr[@]+...} keeps an empty array safe under `set -u` on bash 3.2.
  "${PYTHON_BIN}" -c '
import json, sys
at, ver, first, src = sys.argv[1:5]
doc = {"installedAt": at, "pluginVersion": ver, "activeProfile": first,
       "activeProfiles": sys.argv[5:], "source": src}
sys.stdout.write(json.dumps(doc, indent=2) + "\n")
' "${INSTALLED_AT}" "${PLUGIN_VERSION}" "${ACTIVE_PROFILE_FIRST}" "${PLUGIN_ROOT}" \
    ${ACTIVE_PROFILES_LIST[@]+"${ACTIVE_PROFILES_LIST[@]}"} > "${STAGE_DIR}/.installed"
else
  # Pure-bash fallback: escapes `\` and `"` (profile names are validated;
  # the repo path is the only free-form value).
  ACTIVE_PROFILES_JSON=""
  if [[ ${#ACTIVE_PROFILES_LIST[@]} -gt 0 ]]; then
    for _p in "${ACTIVE_PROFILES_LIST[@]}"; do
      ACTIVE_PROFILES_JSON="${ACTIVE_PROFILES_JSON:+${ACTIVE_PROFILES_JSON},}\"$(json_escape "${_p}")\""
    done
  fi
  cat > "${STAGE_DIR}/.installed" <<JSON
{
  "installedAt": "${INSTALLED_AT}",
  "pluginVersion": "$(json_escape "${PLUGIN_VERSION}")",
  "activeProfile": "$(json_escape "${ACTIVE_PROFILE_FIRST}")",
  "activeProfiles": [${ACTIVE_PROFILES_JSON}],
  "source": "$(json_escape "${PLUGIN_ROOT}")"
}
JSON
fi

# Swap: old → unique backup path, new → target.
if [[ -e "${TARGET_DIR}" || -L "${TARGET_DIR}" ]]; then
  BACKUP="${TARGET_DIR}.bak.$(date +%Y%m%d-%H%M%S).$$"
  n=1
  while [[ -e "${BACKUP}" || -L "${BACKUP}" ]]; do
    BACKUP="${TARGET_DIR}.bak.$(date +%Y%m%d-%H%M%S).$$.${n}"
    n=$((n + 1))
  done
  mv "${TARGET_DIR}" "${BACKUP}"
  SWAP_STATE="old-moved"
  echo "ℹ️ Existing install moved to ${BACKUP}"
  # Test hook (CI): simulate a failure between the two renames.
  if [[ -n "${MFG_INSTALL_TEST_FAIL_SWAP:-}" ]]; then
    echo "   (MFG_INSTALL_TEST_FAIL_SWAP set — simulating swap failure)" >&2
    exit 1
  fi
fi
mv "${STAGE_DIR}" "${TARGET_DIR}"
STAGE_DIR=""
SWAP_STATE="done"

# Cap retained backups: keep the newest KEEP_BACKUPS, delete older ones.
# Names sort chronologically (YYYYmmdd-HHMMSS prefix).
ALL_BACKUPS=()
for b in "${TARGET_DIR}".bak.*; do
  if [[ -d "${b}" && ! -L "${b}" ]]; then ALL_BACKUPS+=("${b}"); fi
done
n_backups=${#ALL_BACKUPS[@]}
if [[ ${n_backups} -gt ${KEEP_BACKUPS} ]]; then
  n_drop=$((n_backups - KEEP_BACKUPS))
  i=0
  while [[ ${i} -lt ${n_drop} ]]; do
    rm -rf "${ALL_BACKUPS[i]}"
    i=$((i + 1))
  done
  echo "ℹ️ Removed ${n_drop} older backup(s); keeping the newest ${KEEP_BACKUPS} (${TARGET_DIR}.bak.*)."
elif [[ ${n_backups} -gt 0 ]]; then
  echo "ℹ️ ${n_backups} backup(s) kept; only the newest ${KEEP_BACKUPS} are retained (${TARGET_DIR}.bak.*)."
fi
if [[ -n "${BACKUP}" ]]; then
  echo "   Undo this install: rm -rf '${TARGET_DIR}' && mv '${BACKUP}' '${TARGET_DIR}'"
fi

echo ""
echo "✅ Installation complete."

# ─── Profile maturity warnings (stub / alpha) ──────────────────────
ALL_STUB=false
if [[ "${CORE_ONLY}" == "false" ]]; then
  ALL_STUB=true
  idx=0
  for prof in "${ACTIVE_PROFILES[@]}"; do
    pj="${PLUGIN_ROOT}/profiles/${prof}/profile.json"
    status="$(profile_status "${pj}")"
    [[ "${status}" == "stub" ]] || ALL_STUB=false
    warnings="$(profile_warnings "${pj}")"
    if [[ "${status}" == "stub" ]]; then
      echo ""
      echo "⚠️ ════════════════════════════════════════════════"
      echo "⚠️  STUB PROFILE: ${prof} ($(profile_version "${pj}"))"
      echo "⚠️ ════════════════════════════════════════════════"
      echo "   Profile files installed: ${OVERLAY_COUNTS[idx]} — you have the generic core layer only."
      echo "   No ${prof} vertical know-how, agents or skills are included yet."
      case "${prof}" in
        food-processing)
          echo "   HACCP / food-safety content is NOT included — do not use output for CCP, allergen or recall decisions.";;
        pharma)
          echo "   GxP content is NOT included — do not use output for GMP, batch-record or validation decisions.";;
      esac
      echo "   Contributions wanted: profiles/${prof}/README.md"
      if [[ -n "${warnings}" ]]; then echo "   Profile warnings:"; fi
    elif [[ -n "${warnings}" ]]; then
      echo ""
      echo "⚠️ ${prof} (${status}) — read before use:"
    fi
    if [[ -n "${warnings}" ]]; then
      printf '%s\n' "${warnings}" | sed 's/^/     • /'
    fi
    idx=$((idx + 1))
  done
fi

echo ""
echo "Try in Claude Code:"
echo "   /manufacturing                # see plugin status"
echo "   /manufacturing init           # interactive setup wizard"
if [[ "${CORE_ONLY}" == "true" || "${ALL_STUB}" == "true" ]]; then
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
