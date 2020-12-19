FROM python:3.9.1-buster

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ./backend /app/backend
COPY ./frontend /app/frontend

WORKDIR /app
RUN uvicorn --version
CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "backend.main:app"]

EXPOSE 8000
