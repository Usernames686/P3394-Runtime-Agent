FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    AGENTCLAW_PROJECT_DIR=/app/local-demo

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY agentclaw ./agentclaw
COPY agents ./agents
COPY local-demo ./local-demo

RUN pip install --upgrade pip \
    && pip install -e .

RUN if [ ! -f /app/local-demo/models.json ] && [ -f /app/local-demo/models.example.json ]; then \
        cp /app/local-demo/models.example.json /app/local-demo/models.json; \
    fi

EXPOSE 8000

CMD ["python", "-X", "utf8", "-m", "agentclaw.cli", "serve", "-d", "/app/local-demo", "--host", "0.0.0.0", "--port", "8000"]
