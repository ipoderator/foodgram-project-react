GUNICORN ?= gunicorn
BIND ?= --bind
SERVER ?= 0.0.0.0:8000
WSGI_FILE ?= foodgram.wsgi


FROM:
    python:3.11.7

WORKDIR:
    /app

COPY:
    requirements.txt .

RUN:
    pip install -r requirements.txt --no-cache-dir

COPY:
    . .
CMD:
    $(GUNICORN): $(BIND): $(SERVER): $(WSGI_FILE)