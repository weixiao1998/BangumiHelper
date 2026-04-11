FROM python:3.13-slim

WORKDIR /app

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ hatchling \
    && pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ .

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY migrate.sh ./
RUN chmod +x migrate.sh

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
