# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create downloads folder
RUN mkdir -p /app/downloads

# Expose env variables
ENV DOWNLOAD_FOLDER=/app/downloads
ENV LOG_FILE=/app/kindle_watcher.log

# Run the main script
CMD ["python", "main.py"]
