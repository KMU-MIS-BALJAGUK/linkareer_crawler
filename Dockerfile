# Dockerfile
FROM python:3.12-slim

# noninteractive for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies and Chromium (headless)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    gnupg2 \
    unzip \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxrandr2 \
    procps \
    chromium \
 && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium
# (point to chromium binary; webdriver-manager will download the matching chromedriver)
ENV CHROME_BIN=/usr/bin/chromium
ENV PATH="${PATH}:/root/.local/bin"

# Create app dir
WORKDIR /app

# Copy requirements and install Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy your crawler code into the image (assumes file name linkareer_crawler.py)
COPY crawler.py /app/crawler.py

# If you need other resources, copy them here (e.g., templates, config)
# COPY config.yaml /app/config.yaml

# Default command: run crawler in headless mode and produce JSON to stdout
# You can override CMD when running the container.
CMD ["python", "crawler.py", "--headless", "--max", "50"]
