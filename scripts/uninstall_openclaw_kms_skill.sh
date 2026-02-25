#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-${HOME}/.openclaw/openclaw.json}"
WORKSPACE_DIR="${OPENCLAW_WORKSPACE_DIR:-}"
if [[ -z "${WORKSPACE_DIR}" && -f "${CONFIG_PATH}" ]]; then
  WORKSPACE_DIR="$(node -e 'const fs=require("fs"); try { const c=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); process.stdout.write((c && c.agents && c.agents.defaults && c.agents.defaults.workspace) || ""); } catch (_) {}' "${CONFIG_PATH}")"
fi
if [[ -z "${WORKSPACE_DIR}" ]]; then
  WORKSPACE_DIR="${HOME}/.openclaw/workspace"
fi

TARGET_DIR="${WORKSPACE_DIR}/skills/kms"

if [[ -d "${TARGET_DIR}" ]]; then
  rm -rf "${TARGET_DIR}"
  echo "Removed: ${TARGET_DIR}"
else
  echo "No installed kms skill found at: ${TARGET_DIR}"
fi

if [[ -d "${HOME}/.openclaw/skills" ]]; then
  find "${HOME}/.openclaw/skills" -maxdepth 1 -type d -name "kms.backup.*" -prune -exec rm -rf {} +
fi

INFO_JSON="$(openclaw skills info kms --json)"
if echo "${INFO_JSON}" | rg -q '"error"\s*:\s*"not found"'; then
  echo "Verification: kms skill is no longer discoverable."
else
  echo "WARNING: kms skill is still discoverable (possibly from another skill directory)."
fi

echo "Done."
