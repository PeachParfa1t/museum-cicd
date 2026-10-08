FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY wsgi.py .
RUN mkdir -p /app/instance

EXPOSE 8000

CMD ["waitress-serve", "--host=0.0.0.0", "--port=8000", "wsgi:app"]

