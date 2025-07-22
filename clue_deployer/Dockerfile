FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Install system dependencies including build tools for Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    tar \
    iproute2 \
    iputils-ping \
    lsb-release \
    gnupg \
    docker.io \
    dos2unix \
    openssh-client \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl

# Install Helm
RUN curl -LO https://get.helm.sh/helm-v3.14.4-linux-amd64.tar.gz && \
    tar -zxvf helm-v3.14.4-linux-amd64.tar.gz && \
    mv linux-amd64/helm /usr/local/bin/helm && \
    rm -rf linux-amd64 helm-v3.14.4-linux-amd64.tar.gz

# Copy files to run uv (better caching)
COPY clue_deployer/pyproject.toml /app
COPY clue_deployer/src/agent/ /app/clue_deployer/src/agent
RUN mkdir -p /app/clue_deployer
RUN mkdir -p /app/data

# Install Python dependencies
RUN uv sync
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Copy the rest of the necessary files
COPY clue_deployer /app/clue_deployer

# Copy the example result from the Original CLUE paper
RUN mkdir -p /app/data/teastore/2025-05-11_12-00-00
COPY clue_deployer/result_example/teastore/2025-05-11_12-00-00 /app/data/teastore/2025-05-11_12-00-00

# Fix the line endings
RUN dos2unix /app/clue_deployer/entrypoint.sh \
    && chmod +x /app/clue_deployer/entrypoint.sh

ENTRYPOINT ["/app/clue_deployer/entrypoint.sh"]