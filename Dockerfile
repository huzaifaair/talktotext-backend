# =========================
#   Base Image
# =========================
FROM python:3.11-slim

WORKDIR /app

# =========================
#   Install Dependencies
# =========================
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    libglib2.0-0 \
    libasound2-dev \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create a non-root user (fixes Celery warning)
RUN adduser --disabled-password appuser
USER appuser

# Default command for backend
CMD ["python", "wsgi.py"]
