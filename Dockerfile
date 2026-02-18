# ============================================================
# Antigravity SGC — Dockerfile
# Base: selenium/standalone-chrome (Chrome ya incluido)
# + Python 3.11 + Streamlit
# ============================================================
FROM selenium/standalone-chrome:latest

USER root

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ── Python 3.11 + pip ─────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
   python3.11 python3.11-venv python3-pip \
   && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
   && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
   && rm -rf /var/lib/apt/lists/*

# ── Directorio de trabajo ─────────────────────────────────
WORKDIR /app

# ── Dependencias Python (via venv para evitar conflictos) ─
COPY requirements.txt .
RUN python3.11 -m venv /opt/venv \
   && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
   && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

# ── Código fuente ─────────────────────────────────────────
COPY . .

# ── Entrypoint ────────────────────────────────────────────
RUN chmod +x entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["bash", "entrypoint.sh"]
