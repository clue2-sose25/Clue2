FROM python:3.9-slim-buster

RUN apt-get update && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY clue_loadgenerator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY clue_loadgenerator/entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8089

ENTRYPOINT ["./entrypoint.sh"]
