FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files during build (will use local STATIC settings or storages if configured)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8080

CMD ["/bin/sh", "./entrypoint.sh"]
