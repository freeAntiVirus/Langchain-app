FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl tar xz-utils \
    tesseract-ocr \
    poppler-utils \
    libgl1 libglib2.0-0 \
    libleptonica-dev pkg-config \
    libicu-dev libharfbuzz-dev libgraphite2-dev libssl-dev zlib1g-dev \
    dvisvgm ghostscript \
    fonts-dejavu-core fonts-lmodern \
    && rm -rf /var/lib/apt/lists/*

# Install Tectonic (LaTeX engine)
RUN curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh && \
    mv tectonic /usr/local/bin/tectonic && \
    chmod +x /usr/local/bin/tectonic

# --- sanity checks (VERY IMPORTANT for debugging on Render) ---
RUN tectonic --version
RUN dvisvgm --version
RUN gs --version
RUN pdftocairo -v || true

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose port
EXPOSE 8000

# Run backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]