#!/usr/bin/env bash
# manufacturing-plugin — Claude Code installer
#
# Usage:
#   bash adapters/claude-code/install.sh [profile_name]
#
# Default profile: cnc-machining
# Example:
#   bash adapters/claude-code/install.sh cnc-machining
#   bash adapters/claude-code/install.sh           # uses default

set -euo pipefail

PLUGIN_NAME="manufacturing-plugin"
DEFAULT_PROFILE="cnc-machining"
PROFILE="${1:-$DEFAULT_PROFILE}"

# Detect plugin source dir (this script's parent's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

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

echo "════════════════════════════════════════════════"
echo " manufacturing-plugin Claude Code installer"
echo "════════════════════════════════════════════════"
echo ""
echo "Plugin source : ${PLUGIN_ROOT}"
echo "Claude dir    : ${CLAUDE_DIR}"
echo "Install target: ${TARGET_DIR}"
echo "Profile       : ${PROFILE}"
echo ""

# Validate profile exists
if [[ ! -d "${PLUGIN_ROOT}/profiles/${PROFILE}" ]]; then
  echo "❌ Profile not found: ${PROFILE}"
  echo "   Available:"
  ls -1 "${PLUGIN_ROOT}/profiles/" | sed 's/^/   - /'
  exit 1
fi

# Validate Claude Code dir exists
if [[ ! -d "${CLAUDE_DIR}" ]]; then
  echo "⚠️ Claude Code config dir not found at ${CLAUDE_DIR}"
  echo "   Create it? [y/N]"
  read -r answer
  if [[ "${answer,,}" != "y" ]]; then
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

# Stage 2: overlay profile (filename-based override)
echo "→ Overlaying profile: ${PROFILE}..."
PROF_DIR="${PLUGIN_ROOT}/profiles/${PROFILE}"
for sub in agents skills know-how hooks; do
  if [[ -d "${PROF_DIR}/${sub}" ]]; then
    cp -r "${PROF_DIR}/${sub}/." "${TARGET_DIR}/${sub}/" 2>/dev/null || true
  fi
done

# Stage 3: copy plugin manifest + profile manifest
cp "${PLUGIN_ROOT}/plugin.json" "${TARGET_DIR}/plugin.json"
cp "${PROF_DIR}/profile.json"   "${TARGET_DIR}/active-profile.json"

# Stage 4: write install marker
cat > "${TARGET_DIR}/.installed" <<EOF
{
  "installedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "pluginVersion": "$(grep -oE '"version"[^,]*' "${PLUGIN_ROOT}/plugin.json" | head -1)",
  "activeProfile": "${PROFILE}",
  "source": "${PLUGIN_ROOT}"
}
EOF

echo ""
echo "✅ Installation complete."
echo ""
echo "Try in Claude Code:"
echo "   /manufacturing                 # see plugin status"
echo "   /quote @examples/sample-drawing/bracket.md"
echo "   /install-profile cnc-machining # switch profiles"
echo ""
echo "Docs:"
echo "   - README.zh-TW.md"
echo "   - manufacturing.md (the soul doc)"
echo "   - docs/explainers/01-架構總覽.html (open in browser)"
