#!/bin/bash
# Usage: ./onboard.sh <client-name> [knowledge-base-file]
# Example: ./onboard.sh techcorp ./docs/techcorp_products.pdf

set -e

CLIENT=$1
KB_FILE=$2

if [ -z "$CLIENT" ]; then
  echo "Usage: ./onboard.sh <client-name> [knowledge-base-file]"
  exit 1
fi

VALUES_FILE="helm/clients/values-${CLIENT}.yaml"

if [ ! -f "$VALUES_FILE" ]; then
  echo "ERROR: $VALUES_FILE not found."
  echo "Copy helm/clients/values-template.yaml → $VALUES_FILE and fill it in."
  exit 1
fi

echo "── Deploying RECEP for client: $CLIENT ──"
helm upgrade --install recep-${CLIENT} ./helm/recep \
  -f "$VALUES_FILE" \
  --wait

echo "── Waiting for API to be ready ──"
kubectl rollout status deployment/recep-api -n recep-${CLIENT}

# Upload knowledge base if provided
if [ -n "$KB_FILE" ]; then
  echo "── Uploading knowledge base: $KB_FILE ──"
  # Get the ingress domain from values file
  DOMAIN=$(grep 'domain:' "$VALUES_FILE" | head -1 | awk '{print $2}')
  curl -f -X POST "https://${CLIENT}.${DOMAIN}/api/knowledge-base/upload" \
    -F "file=@${KB_FILE}"
  echo "Knowledge base uploaded."
fi

echo ""
echo "✓ Client $CLIENT is live."
echo "  Dashboard: https://${CLIENT}.$(grep 'domain:' $VALUES_FILE | head -1 | awk '{print $2}')"
echo ""
echo "Next: make a test call to verify."
