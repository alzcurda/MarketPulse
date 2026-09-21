# Dockerfile para MarketPulse Web en Servidores / NAS (Synology, QNAP, Unraid, TrueNAS)
FROM python:3.12-slim

# Evitar prompts interactivos durante la instalación de paquetes
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    NO_BROWSER=1

WORKDIR /app

# Instalar dependencias del sistema requeridas para Playwright headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2t64 \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar requerimientos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium --with-deps || true

# Copiar el código de la aplicación
COPY marketpulse/ marketpulse/
COPY docs/ docs/
COPY README.md .
COPY pyproject.toml .

# Instalar el paquete en modo editable/estándar
RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["python", "-m", "marketpulse.web"]
