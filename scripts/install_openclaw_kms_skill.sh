#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${REPO_ROOT}/openclaw-skill/kms"
CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-${HOME}/.openclaw/openclaw.json}"
WORKSPACE_DIR="${OPENCLAW_WORKSPACE_DIR:-}"
if [[ -z "${WORKSPACE_DIR}" && -f "${CONFIG_PATH}" ]]; then
  WORKSPACE_DIR="$(node -e 'const fs=require("fs"); try { const c=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); process.stdout.write((c && c.agents && c.agents.defaults && c.agents.defaults.workspace) || ""); } catch (_) {}' "${CONFIG_PATH}")"
fi
if [[ -z "${WORKSPACE_DIR}" ]]; then
  WORKSPACE_DIR="${HOME}/.openclaw/workspace"
fi
TARGET_ROOT="${WORKSPACE_DIR}/skills"
TARGET_DIR="${TARGET_ROOT}/kms"
BACKUP_ROOT="${HOME}/.openclaw/skill-backups/$(basename "${WORKSPACE_DIR}")"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "ERROR: source skill directory not found: ${SOURCE_DIR}" >&2
  exit 1
fi

mkdir -p "${TARGET_ROOT}"

if [[ -d "${TARGET_DIR}" ]]; then
  mkdir -p "${BACKUP_ROOT}"
  BACKUP_DIR="${BACKUP_ROOT}/kms.${TIMESTAMP}"
  mv "${TARGET_DIR}" "${BACKUP_DIR}"
  echo "Backed up existing kms skill to: ${BACKUP_DIR}"
fi

cp -R "${SOURCE_DIR}" "${TARGET_DIR}"
echo "OpenClaw workspace: ${WORKSPACE_DIR}"
echo "Installed kms skill to: ${TARGET_DIR}"

INFO_JSON="$(openclaw skills info kms --json)"
if echo "${INFO_JSON}" | rg -q '"error"\s*:\s*"not found"'; then
  echo "ERROR: kms skill not discoverable after install." >&2
  exit 1
fi

if echo "${INFO_JSON}" | rg -q '"eligible"\s*:\s*true'; then
  echo "Verification: kms skill is discoverable and eligible."
else
  echo "Verification: kms skill is discoverable but not eligible yet."
  echo "Check required env: KMS_BASE_URL, KMS_API_KEY."
fi

echo "Done."
