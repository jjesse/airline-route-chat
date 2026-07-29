FROM python:3.11-slim

WORKDIR /app

# System deps for matplotlib + healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 appgroup \
    && useradd --system --uid 1000 --gid appgroup --create-home --home-dir /home/appuser appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appgroup . .

# Drop privileges
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
