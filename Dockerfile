ARG DOCKER_USERNAME
ARG DOCKER_REPOSITORY

# Use the official slim Python image
FROM python:3.13.2-slim

# Install dependencies and clean up to reduce image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp using pip
RUN pip install yt-dlp && \
    rm -rf /root/.cache

# Create a working directory for the application
WORKDIR /usr/src/app

# Copy the requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Define the volume
VOLUME [ "/downloads" ]

# Expose the port defined by the environment variable
EXPOSE ${PORT:-3000}

# Define default environment variables
ENV GUNICORN_WORKERS=1
ENV GUNICORN_TIMEOUT=300

# Define the command to run the application using environment variables
# CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "$GUNICORN_WORKERS", "--timeout", "$GUNICORN_TIMEOUT", "app:app"]
# Define the entry point script
ENTRYPOINT [ "sh", "./entrypoint.sh" ]