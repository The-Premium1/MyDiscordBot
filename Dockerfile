FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Verify FFmpeg installation
RUN which ffmpeg && ffmpeg -version | head -1

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Create directories
RUN mkdir -p dashboard/templates dashboard/static/css dashboard/static/js

# Run bot
CMD ["python", "main.py"]
