# Dockerfile for Railway / Render / any container platform
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# sentence-transformers pulls full GPU/CUDA torch by default, which bloats
# the image and RAM usage on free-tier hosts that have no GPU anyway.
# Install the CPU-only wheel first so pip treats torch as already satisfied.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Platforms like Cloud Run, Render, and Railway inject their own $PORT;
# 7860 is just the local-run default.
EXPOSE 7860

# Start the server (HF Spaces) or any platform that sets $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]