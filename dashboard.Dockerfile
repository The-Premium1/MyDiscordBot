FROM python:3.11-slim

WORKDIR /app/dashboard

COPY dashboard/app.py .
COPY dashboard/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "app.py"]
