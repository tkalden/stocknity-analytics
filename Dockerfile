FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY setup.py .
COPY src/ ./src/
COPY enums/ ./enums/
COPY services/ ./services/
COPY utilities/ ./utilities/
COPY finvizfinance/ ./finvizfinance/

EXPOSE 5001

CMD ["python", "main.py"]
