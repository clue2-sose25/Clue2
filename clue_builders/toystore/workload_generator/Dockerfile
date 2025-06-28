# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


FROM python:3.12-slim-bookworm AS base

FROM base AS builder
RUN apt-get -qq update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt .
RUN pip install --prefix="/reqs" -r requirements.txt

FROM base
WORKDIR /usr/src/app/
COPY --from=builder /reqs /usr/local
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
RUN playwright install --with-deps chromium
COPY ./locustfile.py .

ENV LOCUST_HEADLESS=yes
ENV LOCUST_WEB_PORT=8080

EXPOSE 8080

CMD ["locust" , "--csv", "toystore", "--csv-full-history", "--html", "./toystore_report.html","--headless","--only-summary"]
