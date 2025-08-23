web: gunicorn EditEngine.wsgi --bind 0.0.0.0 --access-logfile - --error-logfile -
migrate: python manage.py migrate
collectstatic: python manage.py collectstatic --noinput
createsuperuser: python manage.py createsuperuser --noinput