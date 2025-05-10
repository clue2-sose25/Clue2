FROM python:3.11-bookworm
WORKDIR /loadgenerator
COPY requirements.txt ./
RUN yes | pip3 install locust 

COPY *.py ./

ENV LOCUST_HOST=http://localhost/tools.descartes.teastore.webui/:8080
ENV LOCUST_HEADLESS=yes
ENV LOCUST_WEB_PORT=8080
ENV LOCUST_LOCUSTFILE="./consumerbehavior.py,./loadshapes.py"

CMD ["locust" , "--csv", "teastore", "--csv-full-history", "--html", "./teastore_report.html","--headless","--only-summary"]