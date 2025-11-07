# Use a lightweight base
FROM python:3.10-slim

# Install system dependencies for Tesseract
RUN apt-get update && \
    apt-get install -y tesseract-ocr libtesseract-dev libleptonica-dev pkg-config && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Optional: install language packs (uncomment if needed)
# RUN apt-get install -y tesseract-ocr-eng tesseract-ocr-osd

# Create working directory
WORKDIR /app

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your backend code
COPY . .

# Expose your FastAPI port
EXPOSE 8000

# Run FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
