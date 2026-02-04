# Dockerfile for Ironic AIO

# Use the official Python image from the Docker Hub
FROM python:3.14-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install build dependencies, install Python packages, then remove build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code
COPY . .

# Command to run the application
CMD ["python", "app.py"]
