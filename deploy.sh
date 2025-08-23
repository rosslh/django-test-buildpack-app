#!/bin/bash
# deploy.sh

TOOL_NAME="editengine"
REPO_URL="https://github.com/rosslh/django-test-buildpack-app"

echo "🚀 Deploying $TOOL_NAME..."

ssh -i ~/.ssh/Toolforge rosslh@login.toolforge.org "become editengine bash -c '
  set -euo pipefail;
  echo \"⚙️  Setting environment variables...\";
  toolforge envvars create DJANGO_SETTINGS_MODULE \"EditEngine.settings\";
  toolforge envvars create DJANGO_CONFIGURATION \"Production\";
  toolforge envvars create REDIS_HOST \"tools-redis\";
  toolforge envvars create REDIS_PORT \"6379\";
  toolforge envvars create REDIS_DB \"0\";
  toolforge envvars create REDIS_PASSWORD \"\";
  toolforge envvars create DEBUG \"False\";
  toolforge envvars create DJANGO_WORKERS \"2\";
  toolforge envvars create DJANGO_MAX_REQUESTS \"1000\";
  toolforge envvars create CELERY_WORKER_CONCURRENCY \"1\";
  toolforge envvars create CELERY_PARAGRAPH_BATCH_SIZE \"2\";
  toolforge envvars create CELERY_WORKER_POOL \"prefork\";
  toolforge envvars create CELERY_MAX_TASKS_PER_CHILD \"50\";
  echo \"🛑 Stopping service...\";
  toolforge webservice buildservice stop --mount all || echo \"ℹ️  Service was not running\";
  echo \"🔨 Starting build...\";
  toolforge build start https://github.com/rosslh/django-test-buildpack-app || { echo \"❌ Build failed\"; exit 1; };
  echo \"▶️  Starting service...\";
  toolforge webservice buildservice start --mount all || { echo \"❌ Service start failed\"; exit 1; };
  echo \"✅ Deployment successful!\"
'"

echo "🎉 Done!"
