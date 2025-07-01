# Dockerfile.dind-privileged
FROM docker:28.1-dind

RUN apk update \
    && apk add --no-cache \
    git \
    python3 \
    dos2unix \
    py3-pip 

WORKDIR /app

# Copy just requirements.txt first to benefit from cache
COPY clue_builders/toystore/requirements.txt ./requirements.txt

# Create a venv, install deps (ignoring PEP668)
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy the rest of the files 
COPY clue_builders/toystore/ .

# Convert line endings and make executable 
RUN dos2unix /app/entrypoint.sh \
     && chmod +x /app/entrypoint.sh

ENTRYPOINT ["sh" , "entrypoint.sh"]
