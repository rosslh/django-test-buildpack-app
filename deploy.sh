#!/bin/bash
# deploy.sh

TOOL_NAME="editengine"
REPO_URL="https://github.com/rosslh/django-test-buildpack-app"

echo "🚀 Deploying $TOOL_NAME..."

ssh -i ~/.ssh/Toolforge rosslh@login.toolforge.org "become editengine bash -c '
  set -euo pipefail;
  echo \"🛑 Stopping service...\";
  toolforge webservice buildservice stop --mount all || echo \"ℹ️  Service was not running\";
  echo \"🔨 Starting build...\";
  toolforge build start https://github.com/rosslh/django-test-buildpack-app || { echo \"❌ Build failed\"; exit 1; };
  echo \"▶️  Starting service...\";
  toolforge webservice buildservice start --mount all || { echo \"❌ Service start failed\"; exit 1; };
  echo \"✅ Deployment successful!\"
'"

echo "🎉 Done!"
