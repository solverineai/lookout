FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" openai httpx python-multipart
COPY app app
COPY web web
RUN mkdir -p /data
ENV DB_PATH=/data/lookout.db
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
