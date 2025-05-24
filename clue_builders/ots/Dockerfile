# Dockerfile.dind-privileged
FROM docker:28.1-dind

RUN apk update \
    && apk add --no-cache \
    git \
    python3 \
    py3-pip 

WORKDIR /app


# Copy just requirements.txt first to benefit from cache
COPY clue_builders/ots/ .

# Create a venv, install deps (ignoring PEP668)
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# copy config files and loaders
COPY clue_deployers/src/config .
COPY ./clue_config.yaml .
COPY ./sut_configs/ots.yaml .

ENTRYPOINT ["sh" , "entrypoint.sh"]


