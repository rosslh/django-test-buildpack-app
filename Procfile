web: gunicorn EditEngine.wsgi --bind 0.0.0.0 --workers 4 --access-logfile - --error-logfile -
migrate: python manage.py migrate
collectstatic: python manage.py collectstatic --noinput
createsuperuser: python manage.py createsuperuser --noinput
run-celery: celery -A EditEngine worker --loglevel=info --concurrency=1 --pool=prefork --max-tasks-per-child=50
run-celery-beat: celery -A EditEngine beat --loglevel=info