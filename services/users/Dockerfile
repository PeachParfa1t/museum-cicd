FROM public.ecr.aws/docker/library/python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /service

COPY services/users/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/users/users_service ./users_service
COPY services/users/wsgi.py .

EXPOSE 8000

CMD ["waitress-serve", "--host=0.0.0.0", "--port=8000", "wsgi:app"]
