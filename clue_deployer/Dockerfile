FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

COPY clue_deployer/ /app

RUN mv /app/src /app/clue_deployer

COPY sut_configs/ /app/sut_configs

COPY clue-config.yaml /app/clue-config.yaml

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

# write insecure registry config into docker daemon config
RUN mkdir -p /etc/docker && \
    echo '{ "insecure-registries":["registry:5000"] }' > /etc/docker/daemon.json

#start docker daemon
RUN mkdir -p /var/run/docker.sock && \
    chmod 777 /var/run/docker.sock && \
    dockerd &

# Install Python dependencies
RUN uv sync

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["/app/entrypoint.sh"]