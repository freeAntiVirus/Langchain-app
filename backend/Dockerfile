FROM python:3.10-slim

RUN apt-get update && apt-get install -y curl tar xz-utils \
    tesseract-ocr poppler-utils libgl1 libglib2.0-0 libleptonica-dev pkg-config \
    libicu-dev libharfbuzz-dev libgraphite2-dev libssl-dev zlib1g-dev && \
    # install tectonic from official source
    curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh && \
    mv tectonic /usr/local/bin/tectonic && chmod +x /usr/local/bin/tectonic && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN tectonic --version  # sanity check

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]