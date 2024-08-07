FROM python:3.8-slim-bullseye

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN set -ex \
    && addgroup --system --gid 1001 appuser \
    && adduser --system --uid 1001 --gid 1001 --no-create-home appuser \
    && apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y build-essential \
    && apt-get install -y libpq-dev \
    && apt-get install -y git \
    && apt-get install -y libmagic1 \
    && apt-get install -y vim curl \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 5000
