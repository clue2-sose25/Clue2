# Dockerfile.dind-privileged
FROM docker:28.1-dind

RUN apk update \
    && apk add --no-cache \
    git \
    dos2unix \
    python3 \
    py3-pip 

WORKDIR /app


# Copy just requirements.txt first to benefit from cache
COPY clue_builders/ots/ .

# Create a venv, install deps (ignoring PEP668)
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY ./sut_configs/otel-demo.yaml /app/sut_configs/otel-demo.yaml
COPY ./clue-config.yaml /app/clue-configs/
# Convert line endings and make executable 
RUN dos2unix /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

ENTRYPOINT ["sh" , "entrypoint.sh"]


