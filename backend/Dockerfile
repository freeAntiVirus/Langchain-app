# ---------- Stage 1: copy tectonic binary from prebuilt image ----------
FROM rekka/tectonic AS tectonic-stage

# ---------- Stage 2: regular Python backend ----------
FROM python:3.10-slim

# Copy tectonic binary into this Python container
COPY --from=tectonic-stage /usr/bin/tectonic /usr/local/bin/tectonic

# Install other system dependencies
RUN apt-get update && \
    apt-get install -y \
        tesseract-ocr poppler-utils libgl1 libglib2.0-0 \
        libtesseract-dev libleptonica-dev pkg-config \
        libharfbuzz-icu0 libharfbuzz-dev libicu-dev libgraphite2-dev libssl-dev zlib1g-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]