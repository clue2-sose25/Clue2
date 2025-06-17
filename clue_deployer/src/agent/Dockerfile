FROM python:3.11
RUN pip install pipenv
ENV PROJECT_DIR /app
COPY . ${PROJECT_DIR}
WORKDIR ${PROJECT_DIR}
RUN pipenv install --system --deploy
EXPOSE 8000

CMD ["gunicorn","--timeout","0","--graceful-timeout","0","-w","1","-b","0.0.0.0:8000","agent:app"]