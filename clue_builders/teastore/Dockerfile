# Dockerfile.dind-privileged
FROM docker:28.1-dind

# Install system tools 
RUN apk update \
     && apk add --no-cache \
     openjdk17 \
     maven \
     git \
     dos2unix \
     python3 \
     py3-pip \
     && rm -rf /var/cache/apk/*

WORKDIR /app

# Copy just requirements.txt first to benefit from cache
COPY clue_builders/teastore/requirements.txt .

# Create a venv, install deps (ignoring PEP668)
RUN python3 -m venv /opt/venv \
     && /opt/venv/bin/pip install --upgrade pip \
     && /opt/venv/bin/pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy the rest of your code & configs
COPY clue_builders/teastore/ .  

# Ensure python/pip from your venv are first in PATH
ENV PATH="/opt/venv/bin:${PATH}"

# Convert line endings and make executable
RUN dos2unix /app/entrypoint.sh \
     && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
