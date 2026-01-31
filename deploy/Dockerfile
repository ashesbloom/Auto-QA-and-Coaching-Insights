# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements_aws.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_aws.txt

# Copy application code
COPY . .

# Create directories for local storage fallback
RUN mkdir -p voice_transcripts

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=unified_server.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/voice/status || exit 1

# Run the application
CMD ["python", "unified_server.py"]
