FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Install system dependencies
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
COPY clue_deployer/agent/ /app/agent
RUN mkdir -p /app/clue_deployer

# Install Python dependencies
RUN uv sync
ENV PATH="/app/.venv/bin:$PATH"

# Copy the rest of the necessary files
COPY clue_deployer/ /app
RUN mv /app/src/* /app/clue_deployer

# Fix the line endings
RUN dos2unix /app/entrypoint.sh \
     && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]