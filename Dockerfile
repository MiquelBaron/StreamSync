# StreamSync — Django app (SQLite per defecte; vegeu docker-compose.yml)
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=StreamSync.settings \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# xhtml2pdf → svglib → pycairo necessita cairo + compilador (no hi ha wheel sempre)
# matplotlib: libgomp1, freetype, fonts
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        libcairo2-dev \
        libgomp1 \
        libfreetype6 \
        fontconfig \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

COPY manage.py ./
COPY StreamSync ./StreamSync
COPY ss ./ss

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
