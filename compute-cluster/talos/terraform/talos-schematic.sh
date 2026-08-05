#!/usr/bin/env bash
set -euo pipefail

TF_FILE="variables.tf"
ADD_TO_TF=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --add)
      ADD_TO_TF=true
      if [[ -n "${2:-}" && ! "$2" =~ ^-- ]]; then
        TF_FILE="$2"
        shift
      fi
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [--add [path/to/variables.tf]]"
      exit 1
      ;;
  esac
done

# 1. Fetch the latest stable Talos version tag from GitHub API
LATEST_VERSION=$(curl -s https://api.github.com/repos/siderolabs/talos/releases/latest | jq -r '.tag_name')

echo "--> Latest Talos Version: ${LATEST_VERSION}"

# 2. Define the JSON payload matching the Talos Factory API
SCHEMATIC_PAYLOAD=$(cat <<EOF
{
  "customization": {
    "systemExtensions": {
      "officialExtensions": [
        # "siderolabs/iscsi-tools",  # Only needed for longhorn
        # "siderolabs/util-linux-tools",  # Only needed for longhorn
        "siderolabs/qemu-guest-agent"
      ]
    }
  }
}
EOF
)

# 3. Post the schematic to Talos Image Factory
echo "--> Requesting Schematic ID from Talos Factory..."
RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "${SCHEMATIC_PAYLOAD}" \
  https://factory.talos.dev/schematics)

# Validate JSON response
if ! echo "${RESPONSE}" | jq . >/dev/null 2>&1; then
  echo "Error: Received non-JSON response from Talos Factory:"
  echo "${RESPONSE}"
  exit 1
fi

# 4. Extract the Schematic ID
SCHEMATIC_ID=$(echo "${RESPONSE}" | jq -r '.id')
FULL_ISO_URL="https://factory.talos.dev/image/${SCHEMATIC_ID}/${LATEST_VERSION}/nocloud-amd64.iso"

echo "-----------------------------------------------------------------"
echo "Schematic ID  : ${SCHEMATIC_ID}"
echo "Talos Version : ${LATEST_VERSION}"
echo "ISO URL       : ${FULL_ISO_URL}"
echo ""
echo "Use --add /path/to/variables.tf to automatically update the terraform variables"
echo "-----------------------------------------------------------------"

# 5. If --add was specified, update iso_url in variables.tf
if [[ "${ADD_TO_TF}" == true ]]; then
  if [[ ! -f "${TF_FILE}" ]]; then
    echo "Error: ${TF_FILE} not found!"
    exit 1
  fi

  echo "--> Updating 'iso_url' default in ${TF_FILE}..."

  # Update iso_url default in variables.tf
  sed -i -E "/variable \"iso_url\"/,/}/s|(default\s*= \").*(\")|\1${FULL_ISO_URL}\2|" "${TF_FILE}"

  echo "--> Successfully updated ${TF_FILE}!"
fi