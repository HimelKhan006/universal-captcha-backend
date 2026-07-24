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

# Expose port 10000
EXPOSE 10000

# Start Gunicorn, dynamically reading the port variable assigned by the host
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-10000} server:app"]