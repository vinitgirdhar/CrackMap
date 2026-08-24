# CrackMap backend — CPU-only YOLOv8 inference
FROM python:3.11-slim

# opencv (pulled in by ultralytics) needs these
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ultralytics/matplotlib write config at import time; keep it off the read-only fs
ENV YOLO_CONFIG_DIR=/tmp/Ultralytics \
    MPLCONFIGDIR=/tmp/matplotlib \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/

EXPOSE 8000
# PORT is injected by Render/Railway/Fly/HF Spaces; 8000 locally
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
