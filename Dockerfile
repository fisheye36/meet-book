FROM tiangolo/uvicorn-gunicorn:python3.8

ENV MODULE_NAME="backend.main"

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ./backend /app/backend

EXPOSE 80
