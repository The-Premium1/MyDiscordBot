FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy entire project (so bot_data_connector.py and other imports work)
COPY . .

# Install dashboard requirements with gunicorn
RUN pip install --no-cache-dir -r dashboard/requirements.txt

# Run gunicorn in dashboard directory
WORKDIR /app/dashboard
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
