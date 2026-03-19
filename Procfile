web: cd dashboard && gunicorn -w 1 -b 0.0.0.0:5000 --timeout 120 --access-logfile - --error-logfile - app:app
worker: python main.py
