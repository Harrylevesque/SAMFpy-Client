# ── SAMFpy-Client ────────────────────────────────────────────────────────────
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone repo
RUN git clone https://github.com/Harrylevesque/SAMFpy-Client.git .

# Copy browser helper (placed alongside your source)
COPY browser.py /app/browser.py

# Create venv and install deps
RUN python -m venv /app/.venv \
    && /app/.venv/bin/pip install --upgrade pip \
    && /app/.venv/bin/pip install -r requirements.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/entrypoint.sh"]