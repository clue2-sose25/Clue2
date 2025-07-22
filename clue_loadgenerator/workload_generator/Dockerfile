FROM python:3.9-slim-bullseye

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential dos2unix && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY workload_generator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY workload_generator/entrypoint.sh .
RUN dos2unix entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 8089

ENTRYPOINT ["./entrypoint.sh"]
