FROM python:3.9-slim-buster

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*
    
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8089

ENTRYPOINT ["./entrypoint.sh"]
