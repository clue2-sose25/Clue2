FROM docker:28.1-dind

RUN apk update     && apk add --no-cache     dos2unix     python3     py3-pip     && rm -rf /var/cache/apk/*

WORKDIR /app

COPY clue_loadgenerator/requirements.txt .
COPY clue_loadgenerator/entrypoint.sh .

RUN pip install --no-cache-dir --break-system-packages pyyaml docker

COPY clue_loadgenerator/builder/build.py ./build.py
COPY clue_loadgenerator/builder/entrypoint.sh ./entrypoint.builder.sh

COPY clue-config.yaml .
COPY sut_configs ./sut_configs

RUN chmod +x entrypoint.builder.sh

ENTRYPOINT ["./entrypoint.builder.sh"]