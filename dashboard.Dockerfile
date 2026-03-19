FROM python:3.11-slim

WORKDIR /app/dashboard

COPY dashboard/app.py .
COPY dashboard/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# CRITICAL: Use gunicorn, NOT Flask directly
# Flask's PORT parsing crashes on Railway
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
