# Use an official lightweight Python image
FROM python:3.10-slim

# Install system dependencies (specifically ffmpeg for audio conversion)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first to utilize Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Render exposes a dynamic PORT, defaulting to 10000
EXPOSE 10000

# Start the application using Gunicorn (production-grade web server)
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "server:app"]