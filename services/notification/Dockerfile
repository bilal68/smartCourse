FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    celery[redis]==5.3.4 \
    sendgrid==6.11.0 \
    twilio==8.11.0

# Copy application
COPY . .

# Run Celery worker (NO HTTP server!)
CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=info", "--pool=solo"]
