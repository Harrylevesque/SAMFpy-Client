FROM python:3.13-slim

# Install runtime helper (xdg-utils) and temporary build tools so pip can
# compile any packages that require native extensions (PyNaCl, kyber-py, etc.).
RUN apt-get update && apt-get install -y --no-install-recommends \
        xdg-utils \
        build-essential \
        gcc \
        g++ \
        libffi-dev \
        libsodium-dev \
        libssl-dev \
        pkg-config \
        cargo \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

# Create virtualenv and install Python deps while build deps are present.
RUN python -m venv /app/.venv \
    && /app/.venv/bin/pip install --upgrade pip setuptools wheel \
    && /app/.venv/bin/pip install -r /app/requirements.txt \
    && apt-get purge -y --auto-remove build-essential gcc g++ cargo python3-dev pkg-config libffi-dev libsodium-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/entrypoint.sh"]