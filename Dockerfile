# --- Stage 1: compile Tailwind CSS and vendor htmx/Alpine ----------------------
FROM node:22-slim AS frontend
WORKDIR /build/tailwind
COPY tailwind/package.json tailwind/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY tailwind/ ./
COPY templates/ /build/templates/
COPY core/ /build/core/
COPY members/ /build/members/
COPY attendance/ /build/attendance/
COPY checkin/ /build/checkin/
COPY biometrics/ /build/biometrics/
RUN mkdir -p /build/static && npm run build

# --- Stage 2: Django app ----------------------------------------------------------
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libjpeg62-turbo zlib1g libwebp7 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /build/static/css/app.css static/css/app.css
COPY --from=frontend /build/static/js/vendor/ static/js/vendor/
COPY --from=frontend /build/static/fonts/ static/fonts/
COPY --from=frontend /build/static/models/ static/models/

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R app:app /app \
    && chmod +x docker/entrypoint.sh
USER app

EXPOSE 8000
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-"]
