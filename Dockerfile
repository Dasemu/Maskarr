FROM python:3.11-slim

LABEL maintainer="Maskarr"
LABEL description="Tracker Proxy for *arr Applications"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY maskarr.py .

# Create volume for config persistence
VOLUME ["/app/config"]

# Expose port
EXPOSE 8888

# Set environment variable for config location
ENV CONFIG_PATH=/app/config/maskarr_config.json

# Run as non-root user
RUN useradd -m -u 1000 maskarr && \
    chown -R maskarr:maskarr /app
USER maskarr

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8888/', timeout=5)" || exit 1

CMD ["python3", "-u", "maskarr.py"]
