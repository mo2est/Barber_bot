FROM python:3.12-slim

# tzdata — для zoneinfo; curl — для HEALTHCHECK ниже.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fs http://localhost:8080/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "-m", "bot.main"]
