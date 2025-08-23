#!/bin/bash
# deploy.sh

TOOL_NAME="editengine"
REPO_URL="https://github.com/rosslh/django-test-buildpack-app"

echo "🚀 Deploying $TOOL_NAME..."

ssh -i ~/.ssh/Toolforge rosslh@login.toolforge.org "become editengine bash" << 'ENDSSH'
  set -euo pipefail

  echo "📊 Checking database setup..."

  if [ ! -f ~/replica.my.cnf ]; then
    echo "❌ ERROR: ~/replica.my.cnf not found. Contact Toolforge admins."
    exit 1
  fi

  CREDENTIAL_USER=$(grep "^user" ~/replica.my.cnf | cut -d"=" -f2 | tr -d " ")
  CREDENTIAL_PASSWORD=$(grep "^password" ~/replica.my.cnf | cut -d"=" -f2 | tr -d " ")

  echo "Found credential user: $CREDENTIAL_USER"

  DB_NAME="${CREDENTIAL_USER}__editengine"

  echo "Checking if database $DB_NAME exists..."

  DB_EXISTS=$(mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud -e "SHOW DATABASES LIKE '$DB_NAME';" | grep -c $DB_NAME || true)

  if [ "$DB_EXISTS" -eq "0" ]; then
    echo "Creating database $DB_NAME..."
    mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud -e "CREATE DATABASE \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    echo "✅ Database created successfully"
  else
    echo "✅ Database already exists"
  fi

  echo "⚙️  Setting environment variables..."
  toolforge envvars create DJANGO_SETTINGS_MODULE "EditEngine.settings" || true
  toolforge envvars create DJANGO_CONFIGURATION "Production" || true
  toolforge envvars create TOOLFORGE_CREDENTIAL_USER "$CREDENTIAL_USER" || true
  toolforge envvars create TOOLFORGE_CREDENTIAL_PASSWORD "$CREDENTIAL_PASSWORD" || true
  toolforge envvars create REDIS_HOST "redis.svc.tools.eqiad1.wikimedia.cloud" || true
  toolforge envvars create REDIS_PORT "6379" || true
  toolforge envvars create REDIS_DB "0" || true
  toolforge envvars create REDIS_PASSWORD "" || true
  toolforge envvars create DEBUG "False" || true
  toolforge envvars create DJANGO_WORKERS "2" || true
  toolforge envvars create DJANGO_MAX_REQUESTS "1000" || true
  toolforge envvars create CELERY_WORKER_CONCURRENCY "1" || true
  toolforge envvars create CELERY_PARAGRAPH_BATCH_SIZE "2" || true
  toolforge envvars create CELERY_WORKER_POOL "prefork" || true
  toolforge envvars create CELERY_MAX_TASKS_PER_CHILD "50" || true
  toolforge envvars create CELERY_DEFAULT_QUEUE "editengine_$(date +%s)" || true

  echo "🛑 Stopping existing services..."
  toolforge webservice buildservice stop --mount all || echo "Web service was not running"

  echo "🚀 Starting Redis service (if not already running)..."
  if ! toolforge jobs list | grep -q "redis"; then
    toolforge jobs run redis \
      --image tool-containers/redis:latest \
      --command server \
      --continuous \
      --emails none \
      --port 6379
    echo "✅ Redis service started"
    sleep 10  # Wait for Redis to be ready
  else
    echo "✅ Redis service already running"
  fi

  echo "🛑 Stopping Celery workers..."
  if toolforge jobs list | grep -q "celery-worker"; then
    toolforge jobs delete celery-worker || true
    sleep 5
  fi

  echo "🛑 Stopping Celery beat scheduler..."
  if toolforge jobs list | grep -q "celery-beat"; then
    toolforge jobs delete celery-beat || true
    sleep 5
  fi

  echo "🔨 Starting build..."
  toolforge build start https://github.com/rosslh/django-test-buildpack-app || { echo "❌ Build failed"; exit 1; }

  echo "🏃 Running database migrations..."
  toolforge jobs run migrate \
    --image tool-editengine/tool-editengine:latest \
    --command "python manage.py migrate --noinput" \
    --mount all \
    --wait || {
      echo "❌ Migration failed"
      echo "📋 Migration logs:"
      toolforge jobs logs migrate
      exit 1
    }

  echo "▶️ Starting Celery workers..."
  toolforge jobs run celery-worker \
    --image tool-editengine/tool-editengine:latest \
    --command "run-celery" \
    --continuous \
    --mem 2Gi \
    --cpu 1 \
    --replicas 2

  echo "▶️ Starting Celery beat scheduler..."
  toolforge jobs run celery-beat \
    --image tool-editengine/tool-editengine:latest \
    --command "run-celery-beat" \
    --continuous \
    --mem 512Mi

  echo "▶️  Starting web service..."
  toolforge webservice buildservice start --mount all || { echo "❌ Web service start failed"; exit 1; }

  echo "✅ Deployment successful!"
  echo "🌐 Your app will soon be available at: https://editengine.toolforge.org"
ENDSSH

echo "🎉 Done!"
